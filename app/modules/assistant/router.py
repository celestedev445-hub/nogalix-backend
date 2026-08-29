import json
import re
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.ai import ai_json, ai_text
from app.core.deps import get_current_user, get_optional_user
from app.core.limiter import limiter
from app.modules.users.models import User
from app.support.cloudinary_storage import cloudinary_storage

router = APIRouter(prefix="/assistant", tags=["assistant"])

ALLOWED_AUDIO = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/mp4",
    "audio/m4a",
    "video/webm",
}
MAX_AUDIO_BYTES = 8 * 1024 * 1024


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)
    zone: Literal["vitrine", "app", "cv"] = "vitrine"
    cv: Optional[dict[str, Any]] = None


SYSTEM_PROMPT = """Tu es {name}, assistante IA de Nogalix, une application pour créer des CV.
Réponds toujours en français, de façon claire, concise et utile.
Tu aides à : choisir un modèle, rédiger expériences/compétences, améliorer un CV, exporter.
Ne invente pas de données personnelles. Si la question sort du CV, recentre poliment.
"""

CV_SYSTEM_PROMPT = """Tu es {name}, assistante vocale Nogalix pour remplir un CV.
Réponds TOUJOURS en français, courte et claire (2-4 phrases).
Tu guides l'utilisateur section par section : identité, accroche, expériences, formations, compétences, langues, projets, certifications, centres d'intérêt, références.
N'invente JAMAIS de données personnelles absentes du message utilisateur.
Quand l'utilisateur donne des infos, tu les structures dans un patch JSON.

Réponds UNIQUEMENT avec un objet JSON valide (pas de markdown) de la forme :
{{
  "reply": "texte pour l'utilisateur",
  "patch": {{
    "title": "optionnel",
    "summary": "optionnel",
    "identity": {{ "firstName": "", "lastName": "", "title": "", "email": "", "phone": "", "location": "" }},
    "experiences": [{{ "id": "", "title": "", "company": "", "location": "", "start": "", "end": "", "current": false, "bullets": [] }}],
    "education": [{{ "id": "", "diploma": "", "school": "", "year": "", "details": "" }}],
    "skills": [{{ "id": "", "name": "", "level": 70 }}],
    "languages": [{{ "id": "", "name": "", "level": "" }}],
    "projects": [{{ "id": "", "name": "", "description": "", "url": "" }}],
    "certifications": [{{ "id": "", "name": "", "issuer": "", "year": "" }}],
    "interests": [{{ "id": "", "name": "" }}],
    "references": [{{ "id": "", "name": "", "role": "", "company": "", "phone": "", "email": "" }}],
    "replaceLists": false
  }}
}}
N'inclus dans patch que les clés réellement mises à jour. Si aucune info CV, patch = {{}}.
Pose ensuite UNE question pour avancer.
"""


def _local_reply(message: str) -> str:
    lower = message.lower()
    name = settings.assistant_name
    if any(word in lower for word in ("modèle", "modele", "template")):
        return (
            f"Je suis {name}. Choisissez un modèle dans la galerie, puis personnalisez "
            "votre contenu. Le rendu reste instantané côté interface ; vos données sont "
            "sauvegardées sur votre compte."
        )
    if any(word in lower for word in ("expérience", "experience", "job", "poste")):
        return (
            "Pour chaque expérience, indiquez le titre, l'entreprise, les dates et "
            "2 à 4 puces mesurables (chiffres, résultats). Je peux reformuler vos puces "
            "si vous me les collez ici."
        )
    if any(word in lower for word in ("export", "pdf", "télécharg", "telecharg")):
        return (
            "Une fois votre CV prêt, utilisez l'export PDF depuis l'éditeur. "
            "Vérifiez l'aperçu avant de télécharger."
        )
    return (
        f"Je suis {name}, votre assistante CV. Dites-moi ce que vous voulez améliorer : "
        "accroche, expériences, compétences, modèle ou analyse."
    )


def _new_id(prefix: str) -> str:
    import secrets

    return f"{prefix}-{secrets.token_hex(4)}"


def _local_cv_turn(message: str, cv: Optional[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """Heuristic fallback when Gemini is off — extract simple fields + guide next step."""
    patch: dict[str, Any] = {}
    text = message.strip()
    lower = text.lower()
    identity = (cv or {}).get("identity") or {}
    name = settings.assistant_name

    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
    phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
    if email_match:
        patch.setdefault("identity", {})["email"] = email_match.group(0)
    if phone_match:
        patch.setdefault("identity", {})["phone"] = re.sub(r"\s+", " ", phone_match.group(0)).strip()

    # "Je m'appelle X Y" (apostrophe optionnelle)
    name_match = re.search(
        r"(?:je m['’\s]?appelle|mon nom (?:est|c['’]est))\s+([A-Za-zÀ-ÿ'’-]+)(?:\s+([A-Za-zÀ-ÿ'’-]+))?",
        text,
        re.I,
    )
    if name_match:
        patch.setdefault("identity", {})["firstName"] = name_match.group(1).capitalize()
        if name_match.group(2):
            patch["identity"]["lastName"] = name_match.group(2).capitalize()

    # Title / métier — "je suis" = titre, jamais le nom
    title_match = re.search(
        r"(?:je suis|poste(?: de)?|titre(?: :)?|en tant que)\s+([^.!?\n,]{3,60})",
        text,
        re.I,
    )
    if title_match:
        patch.setdefault("identity", {})["title"] = title_match.group(1).strip(" .")

    # Location
    loc_match = re.search(
        r"(?:j['’]habite (?:à|a)|bas[eé]e? (?:à|a)|ville(?: :)?)\s+([A-Za-zÀ-ÿ'’\-\s]{2,40})",
        text,
        re.I,
    )
    if loc_match:
        patch.setdefault("identity", {})["location"] = loc_match.group(1).strip(" .")

    # Accroche / résumé
    if any(w in lower for w in ("accroche", "résumé", "resume", "à propos", "a propos", "profil")):
        cleaned = re.sub(
            r"^(?:mon )?(?:accroche|résumé|resume|profil)\s*(?:est|:)?\s*",
            "",
            text,
            flags=re.I,
        ).strip()
        if len(cleaned) > 20:
            patch["summary"] = cleaned

    # Expérience simple: "J'ai travaillé comme X chez Y"
    exp_match = re.search(
        r"(?:travaill[eé]|post[eé]|expérience).{0,40}?(?:comme|en tant que)\s+([^,.]+).{0,20}?(?:chez|à|a)\s+([^,.]+)",
        text,
        re.I,
    )
    if exp_match:
        patch["experiences"] = [
            {
                "id": _new_id("exp"),
                "title": exp_match.group(1).strip(),
                "company": exp_match.group(2).strip(),
                "location": "",
                "start": "",
                "end": "",
                "current": "actuellement" in lower or "aujourd" in lower,
                "bullets": [],
            }
        ]

    # Compétences listées
    skills_match = re.search(
        r"(?:comp[ée]tences?|skills?)\s*(?:sont|:)?\s*(.+)$",
        text,
        re.I,
    )
    if skills_match:
        raw_skills = re.split(r"[,;/]| et ", skills_match.group(1))
        skills = []
        for part in raw_skills:
            name_sk = part.strip(" .")
            if 1 < len(name_sk) < 40:
                skills.append({"id": _new_id("sk"), "name": name_sk, "level": 70})
        if skills:
            patch["skills"] = skills

    # Langues
    lang_match = re.search(r"(?:langues?|je parle)\s*(?:sont|:)?\s*(.+)$", text, re.I)
    if lang_match and "compétence" not in lower:
        raw_langs = re.split(r"[,;/]| et ", lang_match.group(1))
        langs = []
        for part in raw_langs:
            name_lg = part.strip(" .")
            if 1 < len(name_lg) < 40:
                langs.append({"id": _new_id("lg"), "name": name_lg, "level": "Courant"})
        if langs:
            patch["languages"] = langs

    has_patch = bool(patch)
    missing: list[str] = []
    ident = {**identity, **(patch.get("identity") or {})}
    if not ident.get("firstName") or not ident.get("lastName"):
        missing.append("votre prénom et nom")
    elif not ident.get("title"):
        missing.append("votre titre / métier")
    elif not ident.get("email"):
        missing.append("votre e-mail")
    elif not (cv or {}).get("summary") and not patch.get("summary"):
        missing.append("une courte accroche")
    elif not (cv or {}).get("experiences") and not patch.get("experiences"):
        missing.append("une expérience (poste, entreprise, dates)")
    elif not (cv or {}).get("education") and not patch.get("education"):
        missing.append("une formation")
    elif not (cv or {}).get("skills") and not patch.get("skills"):
        missing.append("quelques compétences")
    else:
        missing.append("une langue, un projet ou une certification")

    if has_patch:
        reply = (
            f"C'est noté, j'ai mis à jour votre CV. "
            f"Pouvez-vous me donner {missing[0]} ?"
        )
    else:
        reply = (
            f"Je suis {name}. Parlez-moi de vous : prénom, nom, métier, "
            f"ou décrivez une expérience. Vous pouvez aussi écrire dans le fil. "
            f"Prochaine info utile : {missing[0]}."
        )
    return reply, patch


async def _gemini_reply(message: str, history: list[ChatMessage]) -> Optional[str]:
    contents = []
    for item in history[-8:]:
        role = "user" if item.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": item.content}]})
    contents.append({"role": "user", "parts": [{"text": message}]})
    return await ai_text(
        contents=contents,
        system=SYSTEM_PROMPT.format(name=settings.assistant_name),
        purpose="chat",
    )


async def _gemini_cv_turn(
    message: str,
    history: list[ChatMessage],
    cv: Optional[dict[str, Any]],
) -> Optional[tuple[str, dict[str, Any]]]:
    snapshot = ""
    if cv:
        try:
            snapshot = json.dumps(
                {
                    "title": cv.get("title"),
                    "summary": cv.get("summary"),
                    "identity": cv.get("identity"),
                    "experiences": cv.get("experiences"),
                    "education": cv.get("education"),
                    "skills": cv.get("skills"),
                    "languages": cv.get("languages"),
                    "projects": cv.get("projects"),
                    "certifications": cv.get("certifications"),
                    "interests": cv.get("interests"),
                    "references": cv.get("references"),
                },
                ensure_ascii=False,
            )[:6000]
        except Exception:
            snapshot = ""

    contents = []
    for item in history[-8:]:
        role = "user" if item.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": item.content}]})
    user_blob = message
    if snapshot:
        user_blob = f"CV actuel (JSON):\n{snapshot}\n\nMessage utilisateur:\n{message}"
    contents.append({"role": "user", "parts": [{"text": user_blob}]})

    parsed = await ai_json(
        contents=contents,
        system=CV_SYSTEM_PROMPT.format(name=settings.assistant_name),
        purpose="cv_chat",
    )
    if not parsed:
        return None
    reply = str(parsed.get("reply") or "").strip()
    patch = parsed.get("patch") if isinstance(parsed.get("patch"), dict) else {}
    if not reply:
        reply = "C'est noté. Que souhaitez-vous ajouter ensuite ?"
    return reply, patch


@router.post("/chat")
@limiter.limit("30/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    if body.zone in {"app", "cv"} and user is None:
        raise HTTPException(status_code=401, detail={"message": "Non authentifié."})

    if body.zone in {"app", "cv"} and user is not None:
        from app.modules.plans.capability import ensure_ai_trial

        ensure_ai_trial(db, user)

    if body.zone == "cv":
        gemini = await _gemini_cv_turn(body.message, body.history, body.cv)
        if gemini:
            reply, patch = gemini
        else:
            reply, patch = _local_cv_turn(body.message, body.cv)
        return {
            "reply": reply,
            "message": reply,
            "patch": patch,
            "data": {"reply": reply, "patch": patch},
        }

    reply = await _gemini_reply(body.message, body.history)
    if not reply:
        reply = _local_reply(body.message)
    return {"reply": reply, "message": reply, "data": {"reply": reply}}


@router.post("/audio")
@limiter.limit("10/minute")
async def audio(
    request: Request,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content_type = (audio.content_type or "").lower()
    if content_type and content_type not in ALLOWED_AUDIO:
        raise HTTPException(
            status_code=422,
            detail={"message": "Format audio non supporté (mp3, wav, webm, ogg, m4a)."},
        )

    raw = await audio.read()
    if len(raw) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=422,
            detail={"message": "Le fichier audio ne doit pas dépasser 8 Mo."},
        )
    await audio.seek(0)

    uploaded = await cloudinary_storage.upload_detailed(
        audio, folder=f"audio/{user.id}", resource_type="video"
    )
    reply = (
        f"J'ai bien reçu votre message vocal. "
        f"La transcription automatique arrive bientôt. En attendant, "
        f"vous pouvez écrire votre demande dans le chat."
    )
    return {
        "reply": reply,
        "message": reply,
        "data": {"reply": reply, "audio_url": uploaded.get("url")},
    }
