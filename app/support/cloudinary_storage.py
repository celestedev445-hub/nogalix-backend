from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from fastapi import UploadFile

from app.core.config import settings


class CloudinaryStorage:
    """Port of CBC CloudinaryStorage — Cloudinary with local fallback."""

    def __init__(self) -> None:
        self._configured = False

    def is_enabled(self) -> bool:
        return bool(settings.cloudinary_url) or (
            bool(settings.cloudinary_cloud_name)
            and bool(settings.cloudinary_api_key)
            and bool(settings.cloudinary_api_secret)
        )

    def _ensure_client(self) -> None:
        if self._configured:
            return
        if settings.cloudinary_url:
            cloudinary.config(cloudinary_url=settings.cloudinary_url, secure=True)
        else:
            cloudinary.config(
                cloud_name=settings.cloudinary_cloud_name,
                api_key=settings.cloudinary_api_key,
                api_secret=settings.cloudinary_api_secret,
                secure=True,
            )
        self._configured = True

    def folder(self, folder: str) -> str:
        prefix = (settings.cloudinary_folder_prefix or "nogalix").strip("/")
        clean = folder.strip("/")
        return f"{prefix}/{clean}" if clean else prefix

    async def upload_detailed(
        self,
        file: UploadFile,
        folder: str,
        resource_type: str = "auto",
    ) -> dict[str, Any]:
        content = await file.read()
        if not content:
            raise ValueError("Fichier vide.")

        if self.is_enabled():
            self._ensure_client()
            result = cloudinary.uploader.upload(
                content,
                folder=self.folder(folder),
                resource_type=resource_type if resource_type in {"image", "video", "raw", "auto"} else "auto",
                overwrite=True,
                filename_override=file.filename,
            )
            return {
                "url": result.get("secure_url") or result.get("url") or "",
                "public_id": result.get("public_id"),
                "resource_type": result.get("resource_type") or resource_type,
                "bytes": result.get("bytes"),
                "format": result.get("format"),
                "width": result.get("width"),
                "height": result.get("height"),
            }

        return await self._local_upload(file.filename or "upload.bin", content, folder)

    async def upload(self, file: UploadFile, folder: str, resource_type: str = "image") -> str:
        result = await self.upload_detailed(file, folder, resource_type)
        return str(result.get("url") or "")

    async def _local_upload(self, filename: str, content: bytes, folder: str) -> dict[str, Any]:
        ext = Path(filename).suffix or ".bin"
        relative = Path("storage") / "uploads" / folder.strip("/") / f"{uuid4().hex}{ext}"
        absolute = Path(__file__).resolve().parents[2] / relative
        absolute.parent.mkdir(parents=True, exist_ok=True)
        absolute.write_bytes(content)
        url = f"{settings.app_url.rstrip('/')}/{relative.as_posix()}"
        return {
            "url": url,
            "public_id": None,
            "resource_type": "raw",
            "bytes": len(content),
            "format": ext.lstrip(".") or None,
            "width": None,
            "height": None,
        }

    def delete(self, stored: Optional[str], resource_type: str = "image") -> None:
        if not stored or not self.is_enabled():
            return
        if "res.cloudinary.com" not in stored and "cloudinary" not in stored:
            return
        public_id = self._public_id_from_url(stored)
        if not public_id:
            return
        self._ensure_client()
        for rtype in {resource_type, "image", "raw", "video"}:
            try:
                cloudinary.uploader.destroy(public_id, resource_type=rtype)
                break
            except Exception:
                continue

    def _public_id_from_url(self, url: str) -> Optional[str]:
        # .../upload/v123/folder/name.ext → folder/name
        try:
            marker = "/upload/"
            if marker not in url:
                return None
            path = url.split(marker, 1)[1]
            parts = path.split("/")
            if parts and parts[0].startswith("v") and parts[0][1:].isdigit():
                parts = parts[1:]
            joined = "/".join(parts)
            return joined.rsplit(".", 1)[0] if joined else None
        except Exception:
            return None


cloudinary_storage = CloudinaryStorage()
