from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import base64

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.cv import service as cv_service
from app.modules.cv.analyse_schemas import (
    CvAnalyseRequest,
    CvImportParseRequest,
    CvImportParseResponse,
    CvMatchAnalyseRequest,
    CvRewriteAnalyseRequest,
    CvTranslateRequest,
    CvTranslateResponse,
    CvUploadAnalyseRequest,
)
from app.modules.cv.import_parse import ImportedCvAiError, parse_imported_cv
from app.modules.cv.translate import CvTranslateError, translate_cv
from app.modules.cv.import_storage import (
    ImportVariant,
    bump_version,
    editable_path,
    has_import_files,
    read_meta,
    save_original_file,
)
from app.modules.cv.onlyoffice import (
    build_editor_config,
    callback_response,
    download_edited_document,
    onlyoffice_enabled,
    verify_document_access_token,
)
from app.modules.cv.schemas import CvPayload
from app.modules.cv.text_extract import extract_resume_text
from app.modules.cv.extract_photo import extract_cv_photo
from app.modules.cv.pdf_to_docx import convert_pdf_to_docx
from app.modules.cv.pdf_to_editable import convert_pdf_to_editable
from app.modules.users.models import User

router = APIRouter(prefix="/cv", tags=["cv"])


@router.get("")
def index(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cv_service.list_cvs(db, user)


@router.get("/{cv_id}")
def show(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cv_service.get_cv(db, user, cv_id)


@router.post("")
def store(body: CvPayload, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cv_service.create_cv(db, user, body)


@router.put("/{cv_id}")
def update(
    cv_id: str,
    body: CvPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cv_service.update_cv(db, user, cv_id, body)


@router.delete("/{cv_id}")
def destroy(cv_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return cv_service.delete_cv(db, user, cv_id)


@router.post("/translate", response_model=CvTranslateResponse)
async def translate_cv_content(
    body: CvTranslateRequest,
    _user: User = Depends(get_current_user),
):
    try:
        return await translate_cv(
            cv=body.cv,
            language_name=body.languageName,
            language_code=body.languageCode,
        )
    except CvTranslateError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc)}) from exc


@router.post("/analyse/rewrite")
async def analyse_rewrite(
    body: CvRewriteAnalyseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await cv_service.rewrite_from_analyse(db, user, body)


@router.post("/analyse/match")
async def analyse_match(
    body: CvMatchAnalyseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await cv_service.match_analyse(db, user, body)


@router.post("/analyse/upload")
async def analyse_upload(
    body: CvUploadAnalyseRequest,
    user: User = Depends(get_current_user),
):
    try:
        content = base64.b64decode(body.contentBase64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"message": "Fichier invalide."}) from exc

    if not content:
        raise HTTPException(status_code=422, detail={"message": "Fichier vide."})
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail={"message": "Fichier trop lourd (5 Mo max)."})

    try:
        text = extract_resume_text(body.fileName or "cv.txt", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc

    if len(text) < 80:
        raise HTTPException(
            status_code=422,
            detail={"message": "Le document ne contient pas assez de texte pour une analyse fiable."},
        )

    return {"text": text, "fileName": body.fileName or "document", "jobOffer": body.jobOffer}


@router.post("/analyse/upload-multipart")
async def analyse_upload_multipart(
    file: UploadFile = File(...),
    job_offer: str = Form(""),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail={"message": "Fichier vide."})
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail={"message": "Fichier trop lourd (5 Mo max)."})

    try:
        text = extract_resume_text(file.filename or "cv.txt", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc

    if len(text) < 80:
        raise HTTPException(
            status_code=422,
            detail={"message": "Le document ne contient pas assez de texte pour une analyse fiable."},
        )

    return {"text": text, "fileName": file.filename or "document", "jobOffer": job_offer}


@router.post("/import/parse", response_model=CvImportParseResponse)
async def import_parse(
    body: CvImportParseRequest,
    user: User = Depends(get_current_user),
):
    text = (body.text or "").strip()
    if len(text) < 20:
        raise HTTPException(
            status_code=422,
            detail={"message": "Pas assez de texte pour pré-remplir le modèle."},
        )
    try:
        return await parse_imported_cv(text, body.fileName or "", require_ai=body.requireAi)
    except ImportedCvAiError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "Impossible d'extraire les sections de ce CV."},
        ) from exc


@router.post("/import/pdf-to-docx")
async def import_pdf_to_docx(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail={"message": "Fichier vide."})
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail={"message": "Fichier trop lourd (5 Mo max)."})

    file_name = file.filename or "cv.pdf"
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail={"message": "Seuls les fichiers PDF sont acceptés."})

    try:
        docx_bytes = convert_pdf_to_docx(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc

    base_name = file_name.rsplit(".", 1)[0] or "cv"
    return {
        "fileName": f"{base_name}.docx",
        "contentBase64": base64.b64encode(docx_bytes).decode("ascii"),
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }


@router.post("/import/pdf-to-editable")
async def import_pdf_to_editable(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail={"message": "Fichier vide."})
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail={"message": "Fichier trop lourd (5 Mo max)."})

    file_name = file.filename or "cv.pdf"
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail={"message": "Seuls les fichiers PDF sont acceptés."})

    try:
        return convert_pdf_to_editable(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc


@router.post("/import/extract-photo")
async def import_extract_photo(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail={"message": "Fichier vide."})
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail={"message": "Fichier trop lourd (5 Mo max)."})

    file_name = file.filename or "cv.pdf"
    lower = file_name.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".docx")):
        raise HTTPException(status_code=422, detail={"message": "PDF ou Word uniquement."})

    return {"photo": extract_cv_photo(content, file_name)}


@router.get("/import/document/{cv_id}")
def serve_import_document(
    cv_id: str,
    token: str = Query(...),
    variant: ImportVariant = Query("editable"),
):
    try:
        user_id, token_cv_id, token_variant = verify_document_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail={"message": str(exc)}) from exc

    if token_cv_id != cv_id or token_variant != variant:
        raise HTTPException(status_code=403, detail={"message": "Accès refusé."})

    try:
        from app.modules.cv.import_storage import resolve_document_path

        path = resolve_document_path(user_id, cv_id, variant)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if path.suffix.lower() == ".docx"
        else "application/pdf"
        if path.suffix.lower() == ".pdf"
        else "application/octet-stream"
    )
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.post("/import/onlyoffice/callback")
async def onlyoffice_callback(
    request: Request,
    cv_id: str = Query(...),
    token: str = Query(...),
):
    try:
        user_id, token_cv_id, _variant = verify_document_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail={"message": str(exc)}) from exc

    if token_cv_id != cv_id:
        raise HTTPException(status_code=403, detail={"message": "Accès refusé."})

    body = await request.json()
    status = int(body.get("status") or 0)

    if status in {2, 6}:
        download_url = body.get("url")
        if not isinstance(download_url, str) or not download_url.strip():
            return callback_response(1)
        try:
            content = await download_edited_document(download_url)
            editable_path(user_id, cv_id).write_bytes(content)
            bump_version(user_id, cv_id)
        except Exception:
            return callback_response(1)

    return callback_response(0)


@router.post("/{cv_id}/import/upload")
async def upload_import_file(
    cv_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        cv_service.get_cv(db, user, cv_id)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail={"message": "Fichier vide."})
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail={"message": "Fichier trop lourd (5 Mo max)."})

    try:
        meta = save_original_file(
            user.id,
            cv_id,
            content,
            file.filename or "cv",
            file.content_type or "application/octet-stream",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc

    return {"ok": True, "meta": meta.to_dict()}


@router.get("/{cv_id}/import/editor-config")
def import_editor_config(
    cv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cv = cv_service.get_cv(db, user, cv_id)

    if not onlyoffice_enabled():
        return {"enabled": False, "ready": False}

    if not has_import_files(user.id, cv_id):
        return {
            "enabled": True,
            "ready": False,
            "documentServerUrl": settings.onlyoffice_url.rstrip("/") + "/",
        }

    meta = read_meta(user.id, cv_id)
    if not meta:
        return {
            "enabled": True,
            "ready": False,
            "documentServerUrl": settings.onlyoffice_url.rstrip("/") + "/",
        }

    display_name = user.name or user.email or "Utilisateur"
    config = build_editor_config(
        user_id=user.id,
        cv_id=cv_id,
        user_name=display_name,
        meta=meta,
        title=str(cv.get("title") or meta.original_name),
    )
    return {
        "enabled": True,
        "ready": True,
        "documentServerUrl": settings.onlyoffice_url.rstrip("/") + "/",
        "config": config,
    }


@router.post("/{cv_id}/analyse")
def analyse(
    cv_id: str,
    body: CvAnalyseRequest = CvAnalyseRequest(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job_offer = body.jobOffer or ""
    return cv_service.analyze_cv(db, user, cv_id, job_offer=job_offer)
