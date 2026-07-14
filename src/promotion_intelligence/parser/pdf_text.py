from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True, slots=True)
class PdfPageText:
    page_number: int
    text: str


def extract_pages(pdf_path: Path, page_numbers: tuple[int, ...]) -> dict[int, PdfPageText]:
    """Extract selected 1-based pages from a Match Report PDF.

    Missing pages are returned with empty text so downstream parsers can emit
    explicit QC errors instead of silently guessing values.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"expected a PDF file: {pdf_path}")

    requested = tuple(dict.fromkeys(page_numbers))
    if any(page < 1 for page in requested):
        raise ValueError("page numbers must be 1-based positive integers")

    output: dict[int, PdfPageText] = {}
    with fitz.open(pdf_path) as document:
        for page_number in requested:
            if page_number > document.page_count:
                output[page_number] = PdfPageText(page_number=page_number, text="")
                continue
            page = document.load_page(page_number - 1)
            output[page_number] = PdfPageText(
                page_number=page_number,
                text=page.get_text("text", sort=True).strip(),
            )
    return output
