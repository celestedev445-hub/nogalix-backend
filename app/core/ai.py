"""
Point unique pour toute l'IA Nogalix.

Réglez uniquement ce fichier pour :
- l'ordre des modèles et les bascules (404, 503, saturation)
- les tokens, timeouts et températures par usage
- le parsing JSON
- le comportement si l'IA est indisponible

Les modules métier appellent `ai_text` ou `ai_json`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Literal, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Modèles : le premier dispo gagne. GEMINI_MODEL (.env) est essayé en tête.
# Les 2.0 sont arrêtés. En 503 on passe à un 3.x encore servi, puis on réessaie.
# ---------------------------------------------------------------------------
AI_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
)

_retired_models: set[str] = set()

AI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TRANSIENT_STATUS = {429, 500, 502, 503, 504}

# Presets par usage. Ajoutez-en un ici, puis passez purpose="..." à ai_json / ai_text.
AI_PRESETS: dict[str, dict[str, Any]] = {
    "chat": {"max_tokens": 512, "timeout": 30.0, "temperature": 0.6, "json": False},
    "cv_chat": {"max_tokens": 1024, "timeout": 45.0, "temperature": 0.4, "json": True},
    "match": {"max_tokens": 1536, "timeout": 45.0, "temperature": 0.3, "json": True},
    "rewrite": {"max_tokens": 2048, "timeout": 60.0, "temperature": 0.35, "json": True},
    "import": {"max_tokens": 8192, "timeout": 90.0, "temperature": 0.1, "json": True},
    "translate": {"max_tokens": 8192, "timeout": 90.0, "temperature": 0.2, "json": True},
    "candidature": {"max_tokens": 8192, "timeout": 90.0, "temperature": 0.35, "json": True},
}


class AiError(Exception):
    """L'IA n'a pas pu répondre (clé, saturation, JSON invalide)."""


@dataclass
class AiResult:
    text: str
    data: Optional[dict[str, Any]]
    model: str


def ai_enabled() -> bool:
    return bool(settings.gemini_enabled and settings.gemini_api_key)


def ai_models() -> list[str]:
    models: list[str] = []
    configured = (settings.gemini_model or "").strip()
    if configured:
        models.append(configured)
    for model in AI_MODELS:
        if model not in models:
            models.append(model)
    return models


def _live_models() -> list[str]:
    ordered = ai_models()
    live = [model for model in ordered if model not in _retired_models]
    return live or list(ordered)


def _is_retired_payload(status: int, body: str) -> bool:
    if status == 404:
        return True
    lowered = (body or "").lower()
    return "no longer available" in lowered or '"status": "not_found"' in lowered


def _mark_retired(model: str, purpose: str) -> None:
    _retired_models.add(model)
    logger.warning("IA modèle retiré de la rotation %s (%s)", model, purpose)


def parse_ai_json(raw: str) -> Optional[dict[str, Any]]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _extract_text(payload: dict[str, Any]) -> str:
    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()


def _is_gemini_3(model: str) -> bool:
    return model.startswith("gemini-3")


def _adapt_config(model: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    adapted = dict(config)
    if not _is_gemini_3(model):
        return [adapted]
    for key in ("temperature", "topP", "topK", "top_p", "top_k"):
        adapted.pop(key, None)
    if "thinkingConfig" not in adapted:
        adapted["thinkingConfig"] = {"thinkingLevel": "MINIMAL"}
    configs = [adapted]
    stripped = {key: value for key, value in config.items() if key not in {
        "temperature", "topP", "topK", "top_p", "top_k", "thinkingConfig",
    }}
    if stripped != adapted:
        configs.append(stripped)
    return configs


def _preset(purpose: str) -> dict[str, Any]:
    return dict(AI_PRESETS.get(purpose) or {"max_tokens": 1024, "timeout": 60.0, "temperature": 0.3, "json": False})


def _floor_tokens(requested: int) -> int:
    configured = int(settings.gemini_max_output_tokens or 512)
    return max(configured, requested)


async def ai_complete(
    prompt: Optional[str] = None,
    *,
    contents: Optional[list[dict[str, Any]]] = None,
    system: Optional[str] = None,
    purpose: str = "generic",
    expect: Optional[Literal["text", "json"]] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    required: bool = False,
) -> Optional[AiResult]:
    """
    Seule fonction d'appel IA.

    - purpose : clé de AI_PRESETS (chat, import, translate, candidature, …)
    - expect  : "json" ou "text" (sinon le preset décide)
    - required : lève AiError au lieu de renvoyer None
    """
    if not ai_enabled():
        if required:
            raise AiError("L'IA est désactivée ou la clé API est absente.")
        return None

    preset = _preset(purpose)
    want_json = (expect == "json") if expect else bool(preset.get("json"))
    tokens = _floor_tokens(max_tokens if max_tokens is not None else int(preset["max_tokens"]))
    wait = float(timeout if timeout is not None else preset["timeout"])
    temp = float(temperature if temperature is not None else preset["temperature"])

    if contents is None:
        if not prompt:
            if required:
                raise AiError("Aucun prompt IA fourni.")
            return None
        contents = [{"role": "user", "parts": [{"text": prompt}]}]

    generation_config: dict[str, Any] = {
        "maxOutputTokens": tokens,
        "temperature": temp,
    }
    if want_json:
        generation_config["responseMimeType"] = "application/json"

    system_instruction = {"parts": [{"text": system}]} if system else None
    last_error = ""
    transient: list[str] = []

    async def try_models(client: httpx.AsyncClient, models: list[str]) -> Optional[AiResult]:
        nonlocal last_error
        for model in models:
            if model in _retired_models:
                continue
            for config in _adapt_config(model, generation_config):
                body: dict[str, Any] = {
                    "contents": contents,
                    "generationConfig": config,
                }
                if system_instruction:
                    body["systemInstruction"] = system_instruction
                try:
                    response = await client.post(
                        AI_ENDPOINT.format(model=model),
                        headers={"x-goog-api-key": settings.gemini_api_key},
                        json=body,
                    )
                except httpx.TimeoutException:
                    # Un modèle saturé peut rester muet au lieu de renvoyer un 503 :
                    # on ne perd pas tout l'appel pour ça, on tente le modèle suivant.
                    last_error = "timeout"
                    if model not in transient:
                        transient.append(model)
                    logger.warning(
                        "IA timeout sur %s (%s), essai du modèle suivant.", model, purpose
                    )
                    break
                if response.status_code == 200:
                    if model != settings.gemini_model:
                        logger.info("IA basculée sur %s (%s)", model, purpose)
                    text = _extract_text(response.json())
                    data = parse_ai_json(text) if want_json else None
                    if want_json and not data:
                        last_error = "JSON invalide ou vide"
                        logger.warning("IA %s : JSON invalide sur %s", purpose, model)
                        break
                    if not text:
                        last_error = "Réponse vide"
                        break
                    return AiResult(text=text, data=data, model=model)

                last_error = response.text[:400]
                if _is_retired_payload(response.status_code, last_error):
                    _mark_retired(model, purpose)
                    break
                if response.status_code == 400:
                    logger.warning("IA HTTP 400 sur %s (%s): %s", model, purpose, last_error)
                    continue
                if response.status_code in TRANSIENT_STATUS:
                    if model not in transient:
                        transient.append(model)
                    logger.warning(
                        "IA HTTP %s sur %s (%s), essai du modèle suivant: %s",
                        response.status_code,
                        model,
                        purpose,
                        last_error,
                    )
                    break
                logger.warning("IA HTTP %s sur %s (%s): %s", response.status_code, model, purpose, last_error)
                break
        return None

    try:
        async with httpx.AsyncClient(timeout=wait) as client:
            result = await try_models(client, _live_models())
            if result:
                return result
            if transient:
                logger.info(
                    "IA nouvel essai après saturation (%s) : %s",
                    purpose,
                    ", ".join(transient),
                )
                await asyncio.sleep(1.2)
                result = await try_models(client, transient)
                if result:
                    return result
    except AiError:
        raise
    except Exception:
        logger.exception("Appel IA interrompu (%s).", purpose)
        last_error = "appel interrompu"

    if last_error:
        logger.warning("IA indisponible (%s): %s", purpose, last_error)
    if required:
        raise AiError("L'IA n'a pas pu répondre. Réessayez dans un instant.")
    return None


async def ai_text(
    prompt: Optional[str] = None,
    *,
    contents: Optional[list[dict[str, Any]]] = None,
    system: Optional[str] = None,
    purpose: str = "chat",
    required: bool = False,
    **overrides: Any,
) -> Optional[str]:
    result = await ai_complete(
        prompt,
        contents=contents,
        system=system,
        purpose=purpose,
        expect="text",
        required=required,
        **overrides,
    )
    return result.text if result else None


async def ai_json(
    prompt: Optional[str] = None,
    *,
    contents: Optional[list[dict[str, Any]]] = None,
    system: Optional[str] = None,
    purpose: str = "generic",
    required: bool = False,
    **overrides: Any,
) -> Optional[dict[str, Any]]:
    result = await ai_complete(
        prompt,
        contents=contents,
        system=system,
        purpose=purpose,
        expect="json",
        required=required,
        **overrides,
    )
    return result.data if result else None
