import logging
import sys
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

logging.getLogger("pypdf").setLevel(logging.ERROR)


def load_documents(path):
    """Yield (file_name, page_number, text) for every non-empty page of every PDF in path."""
    for pdf in sorted(Path(path).glob("*.pdf")):
        try:
            pages = PdfReader(pdf).pages
        except (PyPdfError, OSError) as e:
            print(f"Skipping {pdf.name}: {e}", file=sys.stderr)
            continue
        for number, page in enumerate(pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                yield pdf.name, number, text
