import io
import re
import zipfile
from xml.etree import ElementTree

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _collapse_spaces(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text or "").strip()


def _normalize_lines(text: str) -> str:
    lines = []
    for raw in (text or "").splitlines():
        line = _collapse_spaces(raw)
        if line:
            lines.append(line)
    return "\n".join(lines)


def extract_txt(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return _normalize_lines(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    return _normalize_lines(content.decode("utf-8", errors="ignore"))


def extract_docx(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{W_NS}p"):
        parts: list[str] = []
        for node in paragraph.iter(f"{W_NS}t"):
            if node.text:
                parts.append(node.text)
            if node.tail:
                parts.append(node.tail)
        line = _collapse_spaces("".join(parts))
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("Lecture PDF indisponible sur le serveur.") from exc

    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        page_lines = [_collapse_spaces(line) for line in text.splitlines() if _collapse_spaces(line)]
        if page_lines:
            pages.append("\n".join(page_lines))
    return "\n\n".join(pages)


def extract_resume_text(filename: str, content: bytes) -> str:
    lower = (filename or "").lower()
    if lower.endswith(".txt"):
        return extract_txt(content)
    if lower.endswith(".docx"):
        return extract_docx(content)
    if lower.endswith(".pdf"):
        text = extract_pdf(content)
        if len(text) < 40:
            raise ValueError("Le PDF ne contient pas assez de texte sélectionnable.")
        return text
    if lower.endswith(".doc"):
        raise ValueError("Le format .doc ancien n'est pas pris en charge. Utilisez DOCX ou PDF.")
    raise ValueError("Format de fichier non pris en charge.")
