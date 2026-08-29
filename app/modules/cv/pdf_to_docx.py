import tempfile
from pathlib import Path


def _convert_with_pdf2docx(content: bytes) -> bytes:
    """Convertit un PDF avec pdf2docx (moteur open source le plus proche d'iLovePDF).

    iLovePDF n'est pas open source. pdf2docx (Artifex, MIT) fait le même travail :
    PyMuPDF lit la page, des règles reconstruisent paragraphes / tableaux / images,
    python-docx écrit un .docx éditable.
    Les fichiers temporaires sont obligatoires : un BytesIO en sortie produit souvent
    un document vide, puis un fallback texte qui casse la mise en page.
    """
    from pdf2docx import Converter

    pdf_path = ""
    docx_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_tmp:
            pdf_tmp.write(content)
            pdf_path = pdf_tmp.name
        docx_path = str(Path(pdf_path).with_suffix(".docx"))

        converter = Converter(pdf_path)
        try:
            converter.convert(docx_path, ignore_page_error=True)
        finally:
            converter.close()

        result = Path(docx_path).read_bytes()
        if not result:
            raise ValueError("La conversion PDF vers Word a échoué.")
        return result
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Impossible de convertir ce PDF en Word.") from exc
    finally:
        for path in (pdf_path, docx_path):
            if path:
                Path(path).unlink(missing_ok=True)


def convert_pdf_to_docx(content: bytes) -> bytes:
    if not content:
        raise ValueError("Fichier PDF vide.")
    return _convert_with_pdf2docx(content)
