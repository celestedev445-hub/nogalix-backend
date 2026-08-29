"""Reconstruit un PDF en pages éditables (fond sans texte + polices + spans).

Même principe que pdf2htmlEX / Word : le texte n'est plus une image, il est
reposé en HTML aux coordonnées d'origine, avec les polices extraites du PDF.
"""

from __future__ import annotations

import base64
import math
import re
import struct
from typing import Any

import pymupdf

PT_TO_PX = 96.0 / 72.0
MAX_PAGES = 20
BACKGROUND_ZOOM = 2.0
REDACT_PAD = 0.35

_FORMATS = {
    "ttf": "truetype",
    "otf": "opentype",
    "woff": "woff",
    "woff2": "woff2",
    "cff": "opentype",
}

_STANDARD_FAMILIES = {
    "helvetica": "Arial, Helvetica, sans-serif",
    "helv": "Arial, Helvetica, sans-serif",
    "times-roman": '"Times New Roman", Times, serif',
    "times": '"Times New Roman", Times, serif',
    "courier": '"Courier New", Courier, monospace',
    "symbol": "Symbol, serif",
    "zapfdingbats": '"Zapf Dingbats", sans-serif',
}


def _pt(value: float) -> float:
    return round(float(value) * PT_TO_PX, 3)


def _css_family_token(name: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_-]+", "-", name.split("+")[-1].strip())
    return token or "pdf-font"


def _name_words(font_name: str) -> list[str]:
    stripped = font_name.split("+")[-1]
    parts = re.split(r"[^A-Za-z0-9]+", stripped)
    words: list[str] = []
    for part in parts:
        if not part:
            continue
        split = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+", part)
        words.extend(split or [part])
    return words


_BOLD_TOKENS = {"bold", "black", "heavy", "extrabold", "ultrabold", "bld"}
_ITALIC_TOKENS = {"italic", "ital", "oblique", "obl", "it"}
_SOFT_WEIGHT = {"semi", "demi", "medium", "med", "book", "roman", "regular", "light", "thin"}


def _looks_bold(font_name: str) -> bool:
    """Vrai seulement si le nom de fichier est une graisse grasse, pas le flag PDF."""
    words = [word.lower() for word in _name_words(font_name)]
    for index, word in enumerate(words):
        if word not in _BOLD_TOKENS and word != "bd":
            continue
        previous = words[index - 1] if index else ""
        if previous in _SOFT_WEIGHT:
            continue
        return True
    return False


def _looks_italic(font_name: str) -> bool:
    words = {word.lower() for word in _name_words(font_name)}
    return bool(words & _ITALIC_TOKENS)


def _color_css(value: int, alpha: int = 255) -> str:
    red = (value >> 16) & 255
    green = (value >> 8) & 255
    blue = value & 255
    if alpha >= 255:
        return f"rgb({red},{green},{blue})"
    return f"rgba({red},{green},{blue},{round(alpha / 255, 3)})"


def _standard_family(font_name: str) -> str | None:
    key = _css_family_token(font_name).lower()
    for prefix, stack in _STANDARD_FAMILIES.items():
        if key == prefix or key.startswith(prefix):
            return stack
    return None


def _family_key(font_name: str) -> str:
    """Calibri-Bold / ABC+Calibri → Calibri, pour regrouper les graisses d'une même famille."""
    words = _name_words(font_name)
    skip = _BOLD_TOKENS | _ITALIC_TOKENS | {"bd", "mt", "ps", "psmt", "regular", "normal"}
    kept = [word for word in words if word.lower() not in skip]
    if not kept:
        return _css_family_token(font_name)
    return "-".join(kept)


def _sfnt_weight(content: bytes) -> int | None:
    if len(content) < 12 or content[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        return None
    table_count = struct.unpack(">H", content[4:6])[0]
    cursor = 12
    for _ in range(table_count):
        if cursor + 16 > len(content):
            break
        tag = content[cursor : cursor + 4]
        offset, length = struct.unpack(">II", content[cursor + 8 : cursor + 16])
        cursor += 16
        if tag == b"OS/2" and length >= 6 and offset + 6 <= len(content):
            return int(struct.unpack(">H", content[offset + 4 : offset + 6])[0])
    return None


def _font_file_weight(content: bytes, basefont: str, raw_name: str) -> int:
    parsed = _sfnt_weight(content)
    if parsed:
        return parsed
    if _looks_bold(basefont) or _looks_bold(raw_name):
        return 700
    try:
        if pymupdf.Font(fontbuffer=content).is_bold:
            return 700
    except Exception:
        pass
    return 400


def _font_file_is_bold(content: bytes, basefont: str, raw_name: str) -> bool:
    return _font_file_weight(content, basefont, raw_name) >= 600


def _remember_alias(alias: dict[str, str], key: str, family: str) -> None:
    if not key:
        return
    current = alias.get(key)
    if current and current != family:
        return
    alias[key] = family


def _extract_fonts(
    doc: pymupdf.Document,
) -> tuple[list[dict[str, str]], dict[str, str], dict[int, dict[str, Any]]]:
    fonts: list[dict[str, str]] = []
    alias: dict[str, str] = {}
    xref_meta: dict[int, dict[str, Any]] = {}
    seen_xref: set[int] = set()

    for page in doc:
        for item in page.get_fonts(full=True):
            xref = int(item[0])
            basefont = str(item[3] if len(item) > 3 else "")
            if xref in seen_xref:
                continue
            seen_xref.add(xref)

            try:
                info = doc.extract_font(xref, named=True)
            except Exception:
                continue

            content = info.get("content") or b""
            ext = str(info.get("ext") or "").lower().lstrip(".")
            if not content or ext in ("", "n/a", "none"):
                continue

            raw_name = str(info.get("name") or basefont or f"font-{xref}")
            token = _css_family_token(raw_name) if raw_name else _css_family_token(basefont)
            family = f"pdf{xref}-{token}"
            file_bold = _font_file_is_bold(content, basefont, raw_name)

            fonts.append(
                {
                    "family": family,
                    "format": _FORMATS.get(ext, "truetype"),
                    "data": base64.b64encode(content).decode("ascii"),
                }
            )
            xref_meta[xref] = {
                "family": family,
                "is_bold": file_bold,
                "weight": _font_file_weight(content, basefont, raw_name),
                "basefont": basefont,
            }

            styled = file_bold or _looks_italic(raw_name) or _looks_italic(basefont)
            exact_keys = [basefont, basefont.split("+")[-1]]
            if _looks_bold(raw_name) or _looks_italic(raw_name):
                exact_keys.extend([raw_name, raw_name.split("+")[-1], token])
            specific_token = _css_family_token(basefont)
            if _looks_bold(specific_token) or _looks_italic(specific_token):
                exact_keys.append(specific_token)
            for key in exact_keys:
                _remember_alias(alias, key, family)
            if not styled:
                _remember_alias(alias, token, family)
                _remember_alias(alias, specific_token, family)
                _remember_alias(alias, raw_name, family)
                _remember_alias(alias, raw_name.split("+")[-1], family)

    return fonts, alias, xref_meta


def _span_style(pdf_font: str, alias: dict[str, str]) -> tuple[str, str, str]:
    token = _css_family_token(pdf_font)
    embedded = alias.get(pdf_font) or alias.get(pdf_font.split("+")[-1]) or alias.get(token)
    if embedded:
        return f'"{embedded}"', "400", "normal"

    family = _standard_family(pdf_font) or f'"{token}", Arial, Helvetica, sans-serif'
    weight = "700" if _looks_bold(pdf_font) else "400"
    style = "italic" if _looks_italic(pdf_font) else "normal"
    return family, weight, style


_FLAG_BOLD = 16
try:
    _CHAR_BOLD = int(pymupdf.mupdf.FZ_STEXT_BOLD)
    _CHAR_STROKED = int(pymupdf.mupdf.FZ_STEXT_STROKED)
except Exception:
    _CHAR_BOLD = 8
    _CHAR_STROKED = 32


def _want_bold(pdf_font: str, flags: int, char_flags: int) -> bool:
    return (
        _looks_bold(pdf_font)
        or bool(flags & _FLAG_BOLD)
        or bool(char_flags & _CHAR_BOLD)
        or bool(char_flags & _CHAR_STROKED)
    )


def _find_faces(
    pdf_font: str,
    groups: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]] | None:
    keys = [_family_key(pdf_font), _css_family_token(pdf_font), pdf_font.split("+")[-1]]
    for key in keys:
        if key in groups:
            return groups[key]
    font_key = _family_key(pdf_font)
    if len(font_key) < 4:
        return None
    for group_key, faces in groups.items():
        if group_key.startswith(font_key + "-") or font_key.startswith(group_key + "-"):
            return faces
    return None


def _pick_face(faces: list[dict[str, Any]], want_bold: bool) -> dict[str, Any]:
    if want_bold:
        return max(faces, key=lambda face: int(face["weight"]))
    lighter = [face for face in faces if int(face["weight"]) < 600]
    pool = lighter or faces
    return min(pool, key=lambda face: abs(int(face["weight"]) - 400))


def _page_font_lookup(
    page: pymupdf.Page,
    xref_meta: dict[int, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    exact: dict[str, dict[str, Any]] = {}
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in page.get_fonts(full=True):
        xref = int(item[0])
        meta = xref_meta.get(xref)
        if not meta:
            continue
        face = {
            "family": meta["family"],
            "weight": int(meta.get("weight") or (700 if meta["is_bold"] else 400)),
        }
        basefont = str(item[3] if len(item) > 3 else meta.get("basefont") or "")
        exact[basefont] = face
        stripped = basefont.split("+")[-1]
        token = _css_family_token(basefont)
        if _looks_bold(basefont) or _looks_italic(basefont) or face["weight"] >= 600:
            exact[stripped] = face
            exact[token] = face
        elif face["weight"] < 600:
            exact[stripped] = face
            exact[token] = face

        keys = {_family_key(basefont), token, stripped}
        for key in keys:
            if not key:
                continue
            bucket = groups.setdefault(key, [])
            if not any(existing["family"] == face["family"] for existing in bucket):
                bucket.append(face)
    return exact, groups


def _css_weight_for_face(face: dict[str, Any], want_bold: bool) -> str:
    if want_bold and int(face["weight"]) < 600:
        return "700"
    return "400"


def _span_style_for_later_page(
    pdf_font: str,
    flags: int,
    char_flags: int,
    exact: dict[str, dict[str, Any]],
    groups: dict[str, list[dict[str, Any]]],
    alias: dict[str, str],
) -> tuple[str, str, str]:
    want = _want_bold(pdf_font, flags, char_flags)
    faces = _find_faces(pdf_font, groups)
    exact_face = exact.get(pdf_font) if "+" in pdf_font else None

    if faces and len(faces) > 1:
        face = _pick_face(faces, want)
        return f'"{face["family"]}"', _css_weight_for_face(face, want), "normal"

    if exact_face:
        return f'"{exact_face["family"]}"', _css_weight_for_face(exact_face, want), "normal"

    stripped = pdf_font.split("+")[-1]
    fallback_face = exact.get(pdf_font) or exact.get(stripped)
    if fallback_face:
        return f'"{fallback_face["family"]}"', _css_weight_for_face(fallback_face, want), "normal"

    if faces:
        face = _pick_face(faces, want)
        return f'"{face["family"]}"', _css_weight_for_face(face, want), "normal"

    family, weight, style = _span_style(pdf_font, alias)
    if want and weight == "400":
        return family, "700", style
    return family, weight, style


def _merge_line_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not spans:
        return []
    merged: list[dict[str, Any]] = [dict(spans[0])]
    for current in spans[1:]:
        last = merged[-1]
        gap = current["bbox"][0] - last["bbox"][2]
        same = (
            last["font"] == current["font"]
            and last["weight"] == current["weight"]
            and abs(last["size"] - current["size"]) < 0.05
            and last["color"] == current["color"]
            and last["flags"] == current["flags"]
            and abs(last["origin"][1] - current["origin"][1]) < 0.6
        )
        if same and -0.8 <= gap <= max(last["size"] * 0.55, 2.0):
            last["text"] += current["text"]
            last["bbox"] = (
                last["bbox"][0],
                min(last["bbox"][1], current["bbox"][1]),
                current["bbox"][2],
                max(last["bbox"][3], current["bbox"][3]),
            )
        else:
            merged.append(dict(current))
    return merged


def _page_spans(
    page: pymupdf.Page,
    alias: dict[str, str],
    xref_meta: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    span_index = 0
    later_exact: dict[str, dict[str, Any]] = {}
    later_groups: dict[str, list[dict[str, Any]]] = {}
    if page.number > 0:
        later_exact, later_groups = _page_font_lookup(page, xref_meta)
        style_flag = int(getattr(pymupdf, "TEXT_COLLECT_STYLES", 0) or 0)
        payload = page.get_text("dict", flags=int(pymupdf.TEXTFLAGS_DICT) | style_flag)
    else:
        payload = page.get_text("dict")

    for block in payload.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            direction = line.get("dir") or (1.0, 0.0)
            rotate = round(math.degrees(math.atan2(float(direction[1]), float(direction[0]))), 2)
            raw_spans: list[dict[str, Any]] = []
            for span in line.get("spans", []):
                text = span.get("text") or ""
                if not text.strip("\x00"):
                    continue
                bbox = tuple(float(value) for value in span["bbox"])
                origin = span.get("origin") or (bbox[0], bbox[3])
                size = float(span.get("size") or 11)
                flags = int(span.get("flags") or 0)
                char_flags = int(span.get("char_flags") or 0)
                font_name = str(span.get("font") or "Helvetica")
                if page.number > 0:
                    family, weight, style = _span_style_for_later_page(
                        font_name, flags, char_flags, later_exact, later_groups, alias
                    )
                else:
                    family, weight, style = _span_style(font_name, alias)
                ascender = float(span.get("ascender") or 0.8)
                if ascender <= 0:
                    ascender = 0.8
                raw_spans.append(
                    {
                        "text": text.replace("\x00", ""),
                        "bbox": bbox,
                        "origin": (float(origin[0]), float(origin[1])),
                        "size": size,
                        "flags": flags,
                        "font": font_name,
                        "family": family,
                        "weight": weight,
                        "style": style,
                        "color": _color_css(int(span.get("color") or 0), int(span.get("alpha") or 255)),
                        "ascender": ascender,
                        "rotate": rotate,
                    }
                )

            for span in _merge_line_spans(raw_spans):
                x0, y0, x1, y1 = span["bbox"]
                origin_x, origin_y = span["origin"]
                result.append(
                    {
                        "id": f"{page.number + 1}:{span_index}",
                        "text": span["text"],
                        "left": _pt(origin_x),
                        "top": _pt(origin_y),
                        "width": _pt(max(x1 - x0, 0.5)),
                        "height": _pt(max(y1 - y0, span["size"] * 0.8)),
                        "fontSize": _pt(span["size"]),
                        "fontFamily": span["family"],
                        "fontWeight": span["weight"],
                        "fontStyle": span["style"],
                        "color": span["color"],
                        "ascent": round(span["ascender"], 4),
                        "rotate": span["rotate"],
                    }
                )
                span_index += 1
    return result


def _redact_text(page: pymupdf.Page) -> None:
    payload = page.get_text("dict")
    has_redact = False
    for block in payload.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text") or ""
                if not text.strip("\x00"):
                    continue
                rect = pymupdf.Rect(span["bbox"])
                rect.x0 -= REDACT_PAD
                rect.y0 -= REDACT_PAD
                rect.x1 += REDACT_PAD
                rect.y1 += REDACT_PAD
                page.add_redact_annot(rect, fill=None, cross_out=False)
                has_redact = True
    if has_redact:
        page.apply_redactions(images=0, graphics=0, text=0)


def _page_background(page: pymupdf.Page) -> str:
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(BACKGROUND_ZOOM, BACKGROUND_ZOOM), alpha=False)
    png = pixmap.tobytes("png")
    if len(png) > 1_200_000:
        data = pixmap.tobytes("jpeg", jpg_quality=90)
        mime = "image/jpeg"
    else:
        data = png
        mime = "image/png"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def convert_pdf_to_editable(content: bytes) -> dict[str, Any]:
    if not content:
        raise ValueError("Fichier PDF vide.")

    try:
        source = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("Impossible d'ouvrir ce PDF.") from exc

    pages: list[dict[str, Any]] = []
    fonts: list[dict[str, str]] = []
    try:
        if source.page_count < 1:
            raise ValueError("Le PDF ne contient aucune page.")

        fonts, alias, xref_meta = _extract_fonts(source)
        page_count = min(source.page_count, MAX_PAGES)
        parsed_pages: list[tuple[float, float, list[dict[str, Any]]]] = []

        for index in range(page_count):
            page = source[index]
            rect = page.rect
            parsed_pages.append(
                (_pt(rect.width), _pt(rect.height), _page_spans(page, alias, xref_meta))
            )

        for index in range(page_count):
            page = source[index]
            _redact_text(page)
            width, height, spans = parsed_pages[index]
            pages.append(
                {
                    "width": width,
                    "height": height,
                    "background": _page_background(page),
                    "spans": spans,
                }
            )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Impossible de reconstruire ce PDF.") from exc
    finally:
        source.close()

    if not pages:
        raise ValueError("Impossible de reconstruire ce PDF.")

    return {"fonts": fonts, "pages": pages}
