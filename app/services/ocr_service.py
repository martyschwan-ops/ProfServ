"""
OCR / text-extraction service.

Pipeline per file type:
  PDF  → pdfplumber text extraction → pytesseract OCR fallback if text is sparse
  Image → pytesseract OCR
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MIN_TEXT_CHARS = 80  # below this we consider a PDF "scanned" and fall back to OCR


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from a PDF using pdfplumber; fall back to OCR if sparse."""
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            pages_text = []
            for page in pdf.pages:
                t = page.extract_text() or ""
                pages_text.append(t)
            full_text = "\n".join(pages_text).strip()

        if len(full_text) >= _MIN_TEXT_CHARS:
            return full_text

        logger.info("PDF text sparse (%d chars), attempting OCR", len(full_text))
        return _ocr_pdf(path) or full_text

    except Exception as exc:
        logger.warning("pdfplumber failed for %s: %s. Trying OCR.", path, exc)
        return _ocr_pdf(path) or ""


def extract_text_from_image(path: Path) -> str:
    """OCR an image file."""
    try:
        from PIL import Image
        import pytesseract

        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as exc:
        logger.error("OCR failed for image %s: %s", path, exc)
        return ""


def _ocr_pdf(path: Path) -> Optional[str]:
    """Convert each PDF page to an image and OCR it."""
    try:
        from pdf2image import convert_from_path
        import pytesseract

        images = convert_from_path(str(path))
        texts = [pytesseract.image_to_string(img) for img in images]
        return "\n".join(texts).strip()
    except ImportError:
        logger.warning("pdf2image not installed; cannot OCR scanned PDF")
        return None
    except Exception as exc:
        logger.error("PDF OCR failed for %s: %s", path, exc)
        return None


_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp"}


def extract_text(path: Path) -> str:
    """Dispatch to the appropriate extractor based on file suffix."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix in _IMAGE_SUFFIXES:
        return extract_text_from_image(path)
    raise ValueError(f"Unsupported file type: {suffix!r}")


def is_supported_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix == ".pdf" or suffix in _IMAGE_SUFFIXES
