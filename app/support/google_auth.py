from typing import Any, Optional

import httpx

from app.core.config import settings


class GoogleAuthError(Exception):
    def __init__(self, message: str, code: str = "google_auth_failed"):
        super().__init__(message)
        self.message = message
        self.code = code


async def resolve_google_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Accepts id_token / credential / access_token / code (CBC-compatible).
    Returns { google_id, email, name, avatar }.
    """
    id_token = payload.get("id_token") or payload.get("credential")
    access_token = payload.get("access_token")
    code = payload.get("code")

    if id_token:
        return await _from_id_token(str(id_token))
    if access_token:
        return await _from_access_token(str(access_token))
    if code:
        tokens = await _exchange_code(str(code))
        if tokens.get("id_token"):
            return await _from_id_token(str(tokens["id_token"]))
        if tokens.get("access_token"):
            return await _from_access_token(str(tokens["access_token"]))

    raise GoogleAuthError("Jeton Google manquant.", "google_auth_required")


async def _from_id_token(token: str) -> dict[str, Any]:
    if settings.app_env not in {"local", "development", "dev", "test"} and not settings.google_client_id:
        raise GoogleAuthError("Google OAuth non configuré.", "google_not_configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
        )
    if response.status_code != 200:
        raise GoogleAuthError("Jeton Google invalide.")
    data = response.json()
    audience = data.get("aud")
    if settings.google_client_id and audience != settings.google_client_id:
        raise GoogleAuthError("Audience Google invalide.")
    if str(data.get("email_verified", "")).lower() not in {"true", "1"}:
        raise GoogleAuthError("Email Google non vérifié.")
    email = data.get("email")
    if not email:
        raise GoogleAuthError("Email Google introuvable.")
    return {
        "google_id": str(data.get("sub") or ""),
        "email": str(email).lower(),
        "name": str(data.get("name") or email.split("@")[0]),
        "avatar": data.get("picture"),
    }


async def _from_access_token(token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code != 200:
        raise GoogleAuthError("Token Google invalide.")
    data = response.json()
    if data.get("email_verified") is False:
        raise GoogleAuthError("Email Google non vérifié.")
    email = data.get("email")
    if not email:
        raise GoogleAuthError("Email Google introuvable.")
    return {
        "google_id": str(data.get("sub") or ""),
        "email": str(email).lower(),
        "name": str(data.get("name") or email.split("@")[0]),
        "avatar": data.get("picture"),
    }


async def _exchange_code(code: str) -> dict[str, Any]:
    if not settings.google_client_id or not settings.google_client_secret:
        raise GoogleAuthError("Google OAuth non configuré.")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code != 200:
        raise GoogleAuthError("Échange du code Google impossible.")
    return response.json()
