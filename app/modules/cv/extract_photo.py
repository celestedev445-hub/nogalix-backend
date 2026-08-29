"""Extrait la photo de profil d'un CV PDF ou Word."""

from __future__ import annotations

import base64
import io
import zipfile
from typing import Optional

import pymupdf

MIN_PIXELS = 70
MAX_PIXELS = 1600
MAX_DATA_URL = 900_000


def extract_cv_photo(content: bytes, file_name: str = "") -> Optional[str]:
    name = (file_name or "").lower()
    if name.endswith(".docx"):
        return _from_docx(content)
    return _from_pdf(content)


def _from_pdf(content: bytes) -> Optional[str]:
    try:
        document = pymupdf.open(stream=content, filetype="pdf")
    except Exception:
        return None

    try:
        if document.page_count < 1:
            return None
        page = document[0]
        page_rect = page.rect
        candidates: list[tuple[float, bytes, str]] = []

        seen: set[int] = set()
        for image in page.get_images(full=True):
            xref = int(image[0])
            if xref in seen:
                continue
            seen.add(xref)
            try:
                extracted = document.extract_image(xref)
            except Exception:
                continue
            raw = extracted.get("image")
            if not raw:
                continue
            width = int(extracted.get("width") or 0)
            height = int(extracted.get("height") or 0)
            ext = str(extracted.get("ext") or "jpeg")
            rects: list[pymupdf.Rect] = []
            try:
                rects = list(page.get_image_rects(xref) or [])
            except Exception:
                rects = []
            score = _score_photo(width, height, rects, page_rect)
            if score is None:
                continue
            candidates.append((score, raw, ext))

        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 1:
                continue
            raw = block.get("image")
            if not isinstance(raw, (bytes, bytearray)):
                continue
            bbox = pymupdf.Rect(block.get("bbox") or (0, 0, 0, 0))
            width = int(block.get("width") or bbox.width or 0)
            height = int(block.get("height") or bbox.height or 0)
            score = _score_photo(width, height, [bbox], page_rect)
            if score is None:
                continue
            candidates.append((score, bytes(raw), "jpeg"))

        if not candidates:
            return None
        _score, raw, ext = max(candidates, key=lambda item: item[0])
        return _to_data_url(raw, ext)
    except Exception:
        return None
    finally:
        document.close()


def _from_docx(content: bytes) -> Optional[str]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except Exception:
        return None

    candidates: list[tuple[float, bytes, str]] = []
    try:
        for name in archive.namelist():
            if not name.startswith("word/media/"):
                continue
            raw = archive.read(name)
            if len(raw) < 2_000:
                continue
            ext = name.rsplit(".", 1)[-1].lower()
            if ext not in {"jpg", "jpeg", "png", "webp"}:
                continue
            width, height = _probe_image_size(raw, ext)
            score = _score_photo(width, height, [], None)
            if score is None:
                continue
            candidates.append((score + len(raw) / 50_000, raw, ext))
    except Exception:
        return None
    finally:
        archive.close()

    if not candidates:
        return None
    _score, raw, ext = max(candidates, key=lambda item: item[0])
    return _to_data_url(raw, ext)


def _score_photo(
    width: int,
    height: int,
    rects: list[pymupdf.Rect],
    page_rect: Optional[pymupdf.Rect],
) -> Optional[float]:
    if width < MIN_PIXELS or height < MIN_PIXELS:
        return None
    if width > 4000 or height > 4000:
        return None
    ratio = width / max(height, 1)
    if ratio > 1.7 or ratio < 0.45:
        return None

    score = min(width, height) + (1 - abs(1 - ratio)) * 40

    if page_rect and rects:
        rect = rects[0]
        area = max(rect.width * rect.height, 1)
        page_area = max(page_rect.width * page_rect.height, 1)
        if area < 36 * 36:
            return None
        if area / page_area > 0.42:
            return None
        center_y = (rect.y0 + rect.y1) / 2
        center_x = (rect.x0 + rect.x1) / 2
        if center_y > page_rect.height * 0.58:
            return None
        score += (page_rect.height - center_y) * 0.35
        if center_x < page_rect.width * 0.38 or center_x > page_rect.width * 0.62:
            score += 90
        score += min(area / 80, 180)
    elif page_rect is None:
        score += min(width * height / 8000, 200)

    return score


def _probe_image_size(raw: bytes, ext: str) -> tuple[int, int]:
    try:
        pixmap = pymupdf.Pixmap(raw)
        return int(pixmap.width), int(pixmap.height)
    except Exception:
        if ext in {"jpg", "jpeg"} and raw[:2] == b"\xff\xd8":
            return _jpeg_size(raw)
        if ext == "png" and raw[:8] == b"\x89PNG\r\n\x1a\n":
            return int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
        return 0, 0


def _jpeg_size(raw: bytes) -> tuple[int, int]:
    index = 2
    while index < len(raw) - 8:
        if raw[index] != 0xFF:
            index += 1
            continue
        marker = raw[index + 1]
        if marker in {0xC0, 0xC1, 0xC2}:
            return int.from_bytes(raw[index + 5 : index + 7], "big"), int.from_bytes(
                raw[index + 7 : index + 9], "big"
            )
        if marker == 0xD8 or marker == 0xD9:
            index += 2
            continue
        length = int.from_bytes(raw[index + 2 : index + 4], "big")
        index += 2 + length
    return 0, 0


def _to_data_url(raw: bytes, ext: str) -> Optional[str]:
    try:
        pixmap = pymupdf.Pixmap(raw)
        if pixmap.n > 4 or pixmap.alpha:
            pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
        elif pixmap.n > 3:
            pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
        longest = max(pixmap.width, pixmap.height)
        if longest > MAX_PIXELS:
            zoom = MAX_PIXELS / longest
            pixmap = pymupdf.Pixmap(pixmap, int(pixmap.width * zoom), int(pixmap.height * zoom))
        data = pixmap.tobytes("jpeg", jpg_quality=84)
        mime = "image/jpeg"
        encoded = base64.b64encode(data).decode("ascii")
        url = f"data:{mime};base64,{encoded}"
        if len(url) > MAX_DATA_URL:
            data = pixmap.tobytes("jpeg", jpg_quality=70)
            encoded = base64.b64encode(data).decode("ascii")
            url = f"data:{mime};base64,{encoded}"
        return url if len(url) <= MAX_DATA_URL else None
    except Exception:
        mime = "image/png" if ext == "png" else "image/jpeg"
        encoded = base64.b64encode(raw).decode("ascii")
        url = f"data:{mime};base64,{encoded}"
        return url if len(url) <= MAX_DATA_URL else None
