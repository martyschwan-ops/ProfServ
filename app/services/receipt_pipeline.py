"""
Receipt ingestion pipeline.

Stages:
  1. Detect file type
  2. Extract text (PDF native → OCR fallback)
  3. Run AI extraction
  4. Validate extracted fields
  5. Return ExtractionResult for user review
  (Steps 6-8: file rename/move + Excel write happen after user confirms in the route)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.models.expense import ExtractionResult
from app.services import ocr_service
from app.services.extraction.factory import get_extractor

logger = logging.getLogger(__name__)


def run_pipeline(file_path: Path) -> ExtractionResult:
    """
    Run the full extraction pipeline on an uploaded receipt file.
    Returns ExtractionResult; never raises (errors are surfaced in flags).
    """
    if not file_path.exists():
        return ExtractionResult(flags=["file_not_found"], raw_text="")

    if not ocr_service.is_supported_file(file_path):
        return ExtractionResult(
            flags=[f"unsupported_file_type:{file_path.suffix}"],
            raw_text="",
        )

    # Text extraction
    try:
        raw_text = ocr_service.extract_text(file_path)
    except Exception as exc:
        logger.error("Text extraction failed for %s: %s", file_path, exc)
        raw_text = ""

    if not raw_text.strip():
        logger.warning("No text extracted from %s", file_path)
        result = ExtractionResult(raw_text="", flags=["no_text_extracted"])
        return result

    # AI extraction
    try:
        extractor = get_extractor()
        result = extractor.extract(raw_text, file_name=file_path.name)
    except Exception as exc:
        logger.error("AI extraction failed: %s", exc)
        result = ExtractionResult(raw_text=raw_text, flags=["extraction_error"])

    # Basic validation
    _validate(result)
    return result


def _validate(result: ExtractionResult) -> None:
    """Annotate the result with validation flags (mutates in place)."""
    if result.total_amount is not None:
        if result.total_amount <= 0:
            result.flags.append("amount_not_positive")
        if result.gst_amount and result.gst_amount > result.total_amount:
            result.flags.append("gst_exceeds_total")
    if result.expense_date is None:
        if "date_not_found" not in result.flags:
            result.flags.append("date_not_found")
    if not result.vendor_name:
        if "vendor_not_found" not in result.flags:
            result.flags.append("vendor_not_found")
