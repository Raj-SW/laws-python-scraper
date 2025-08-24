from io import BytesIO
from typing import Optional, Tuple
from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage


def extract_text_from_pdf(pdf_bytes: bytes, max_chars: Optional[int] = None) -> str:
    """Extract text from PDF bytes. Optionally truncate to save storage."""
    with BytesIO(pdf_bytes) as bio:
        text = extract_text(bio) or ""
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars]
    return text


def count_pdf_pages(pdf_bytes: bytes) -> int:
    with BytesIO(pdf_bytes) as bio:
        return sum(1 for _ in PDFPage.get_pages(bio))

