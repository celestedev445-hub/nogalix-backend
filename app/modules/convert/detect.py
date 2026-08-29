from __future__ import annotations

import io
import zipfile
from typing import Literal

ConvertKind = Literal["pdf", "docx"]

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOC_OLE = b"\xd0\xcf\x11\xe0"


class ConvertKindError(ValueError):
    pass


def detect_kind(content: bytes, file_name: str = "", content_type: str = "") -> ConvertKind:
    if not content:
        raise ConvertKindError("Fichier vide.")

    if content.startswith(b"%PDF"):
        return "pdf"

    if content.startswith(DOC_OLE):
        raise ConvertKindError(
            "Les fichiers Word .doc ne sont pas supportés. Enregistrez-les en .docx."
        )

    if content.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = archive.namelist()
        except zipfile.BadZipFile as exc:
            raise ConvertKindError("Fichier ZIP illisible. Importez un PDF ou un Word (.docx).") from exc
        if "word/document.xml" in names or any(name.startswith("word/") for name in names):
            return "docx"
        raise ConvertKindError("Ce fichier n'est pas un document Word (.docx).")

    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if mime == PDF_MIME:
        return "pdf"
    if mime in {DOCX_MIME, "application/msword"}:
        if mime == "application/msword":
            raise ConvertKindError(
                "Les fichiers Word .doc ne sont pas supportés. Enregistrez-les en .docx."
            )
        return "docx"

    lower = (file_name or "").lower()
    if lower.endswith(".pdf"):
        raise ConvertKindError("Ce fichier n'est pas un PDF valide.")
    if lower.endswith(".docx"):
        raise ConvertKindError("Ce fichier n'est pas un Word (.docx) valide.")
    if lower.endswith(".doc"):
        raise ConvertKindError(
            "Les fichiers Word .doc ne sont pas supportés. Enregistrez-les en .docx."
        )

    raise ConvertKindError("Type de fichier non reconnu. Importez un PDF ou un Word (.docx).")


def opposite_kind(kind: ConvertKind) -> ConvertKind:
    return "docx" if kind == "pdf" else "pdf"


def mime_for(kind: ConvertKind) -> str:
    return PDF_MIME if kind == "pdf" else DOCX_MIME
