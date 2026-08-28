from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
import base64

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.cv import service as cv_service
from app.modules.cv.analyse_schemas import CvAnalyseRequest, CvMatchAnalyseRequest, CvRewriteAnalyseRequest, CvUploadAnalyseRequest
from app.modules.cv.schemas import CvPayload
from app.modules.cv.text_extract import extract_resume_text
from app.modules.cv.pdf_to_docx import convert_pdf_to_docx
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


@router.post("/{cv_id}/analyse")
def analyse(
    cv_id: str,
    body: CvAnalyseRequest = CvAnalyseRequest(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job_offer = body.jobOffer or ""
    return cv_service.analyze_cv(db, user, cv_id, job_offer=job_offer)
