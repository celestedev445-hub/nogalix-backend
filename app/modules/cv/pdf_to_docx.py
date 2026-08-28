import io

from docx import Document
from docx.shared import Pt
from pypdf import PdfReader


def _convert_with_pdf2docx(content: bytes) -> bytes:
    from pdf2docx import Converter

    pdf_stream = io.BytesIO(content)
    docx_stream = io.BytesIO()
    converter = Converter(stream=pdf_stream)
    converter.convert(docx_stream)
    converter.close()
    result = docx_stream.getvalue()
    if not result:
        raise ValueError("La conversion PDF vers Word a échoué.")
    return result


def _convert_with_plain_text(content: bytes) -> bytes:
    reader = PdfReader(io.BytesIO(content))
    if not reader.pages:
        raise ValueError("Le PDF ne contient aucune page.")

    doc = Document()
    has_text = False

    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            has_text = True

        for line in lines:
            paragraph = doc.add_paragraph(line)
            paragraph.paragraph_format.space_after = Pt(4)

        if index < len(reader.pages) - 1 and lines:
            doc.add_page_break()

    if not has_text:
        raise ValueError(
            "Ce PDF ne contient pas de texte sélectionnable. Importez un fichier Word (.docx)."
        )

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def convert_pdf_to_docx(content: bytes) -> bytes:
    if not content:
        raise ValueError("Fichier PDF vide.")

    try:
        return _convert_with_pdf2docx(content)
    except Exception:
        return _convert_with_plain_text(content)
