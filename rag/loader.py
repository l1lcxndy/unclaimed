from pathlib import Path

from pypdf import PdfReader


def load_documents(path):
    """Yield (file_name, page_number, text) for every non-empty page of every PDF in path."""
    for pdf in sorted(Path(path).glob("*.pdf")):
        for number, page in enumerate(PdfReader(pdf).pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                yield pdf.name, number, text
