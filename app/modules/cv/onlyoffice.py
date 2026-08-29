from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.modules.cv.import_storage import ImportMeta, ImportVariant, read_meta, resolve_document_path

TOKEN_TTL_SECONDS = 60 * 60


def onlyoffice_enabled() -> bool:
    return bool(settings.onlyoffice_url.strip())


def _signing_secret() -> bytes:
    secret = settings.import_access_secret.strip() or settings.onlyoffice_jwt_secret.strip()
    if not secret:
        secret = "nogalix-dev-import-access"
    return secret.encode("utf-8")


def create_document_access_token(user_id: int, cv_id: str, variant: ImportVariant) -> str:
    expires_at = int(time.time()) + TOKEN_TTL_SECONDS
    payload = f"{user_id}:{cv_id}:{variant}:{expires_at}"
    signature = hmac.new(_signing_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_document_access_token(token: str) -> tuple[int, str, ImportVariant]:
    parts = token.split(":")
    if len(parts) != 5:
        raise ValueError("Token invalide.")
    user_id_raw, cv_id, variant_raw, expires_raw, signature = parts
    if variant_raw not in {"original", "editable"}:
        raise ValueError("Variante invalide.")
    payload = f"{user_id_raw}:{cv_id}:{variant_raw}:{expires_raw}"
    expected = hmac.new(_signing_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Signature invalide.")
    if int(expires_raw) < int(time.time()):
        raise ValueError("Token expiré.")
    return int(user_id_raw), cv_id, variant_raw  # type: ignore[return-value]


def document_key(user_id: int, cv_id: str, meta: ImportMeta) -> str:
    raw = f"{user_id}:{cv_id}:{meta.version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _internal_api_base() -> str:
    return settings.app_internal_url.rstrip("/")


def build_document_url(user_id: int, cv_id: str, variant: ImportVariant) -> str:
    token = create_document_access_token(user_id, cv_id, variant)
    query = urlencode({"variant": variant, "token": token})
    return f"{_internal_api_base()}/api/cv/import/document/{cv_id}?{query}"


def build_callback_url(user_id: int, cv_id: str) -> str:
    token = create_document_access_token(user_id, cv_id, "editable")
    query = urlencode({"cv_id": cv_id, "token": token})
    return f"{_internal_api_base()}/api/cv/import/onlyoffice/callback?{query}"


def build_editor_config(
    *,
    user_id: int,
    cv_id: str,
    user_name: str,
    meta: ImportMeta,
    title: str,
) -> dict[str, Any]:
    document_url = build_document_url(user_id, cv_id, "editable")
    config: dict[str, Any] = {
        "document": {
            "fileType": "docx",
            "key": document_key(user_id, cv_id, meta),
            "title": title or meta.original_name,
            "url": document_url,
            "permissions": {
                "edit": True,
                "download": True,
                "print": True,
                "review": False,
                "comment": False,
            },
        },
        "documentType": "word",
        "editorConfig": {
            "callbackUrl": build_callback_url(user_id, cv_id),
            "mode": "edit",
            "lang": "fr",
            "customization": {
                "autosave": True,
                "forcesave": True,
                "compactHeader": False,
                "toolbarNoTabs": False,
            },
            "user": {
                "id": str(user_id),
                "name": user_name or "Utilisateur",
            },
        },
        "height": "100%",
        "width": "100%",
    }
    if settings.onlyoffice_jwt_secret.strip():
        config["token"] = sign_onlyoffice_payload(config)
    return config


def sign_onlyoffice_payload(payload: dict[str, Any]) -> str:
    import jwt

    return jwt.encode(payload, settings.onlyoffice_jwt_secret, algorithm="HS256")


def parse_onlyoffice_callback_key(document_key: str) -> tuple[int, str] | None:
    # Keys are sha256 hashes — map via meta lookup is done by caller using cv_id in payload
    return None


async def download_edited_document(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.content
        if not content:
            raise ValueError("Document OnlyOffice vide.")
        return content


def callback_response(error: int = 0) -> dict[str, int]:
    return {"error": error}
