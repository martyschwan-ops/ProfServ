"""
Mock extraction provider – returns plausible but fabricated data.
Useful for local development without any API keys.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from app.models.expense import ExtractionResult
from app.services.extraction.base import BaseExtractor


_DATE_RE = re.compile(
    r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\w+ \d{1,2},? \d{4})\b"
)
_AMOUNT_RE = re.compile(r"(?:total|amount|balance|due|charged)[^\d]*(\d[\d,]*\.?\d*)", re.IGNORECASE)
_GST_RE = re.compile(r"(?:gst|hst|tax)[^\d]*(\d[\d,]*\.?\d*)", re.IGNORECASE)
_CURRENCY_RE = re.compile(r"\b(USD|CAD|US\$|CA\$|\$)\b", re.IGNORECASE)


def _parse_amount(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _parse_date(s: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%B %d %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


class MockProvider(BaseExtractor):
    """
    Regex-based fallback that attempts to parse common receipt patterns.
    No AI; intended for offline/testing use.
    """

    provider_name = "mock"

    def extract(self, raw_text: str, file_name: str = "") -> ExtractionResult:
        flags = []
        confidence = 0.4

        # Date
        expense_date = None
        date_match = _DATE_RE.search(raw_text)
        if date_match:
            expense_date = _parse_date(date_match.group(1))
        if expense_date is None:
            flags.append("date_not_found")

        # Amount
        total_amount = None
        amt_match = _AMOUNT_RE.search(raw_text)
        if amt_match:
            total_amount = _parse_amount(amt_match.group(1))
        if total_amount is None:
            # Grab last dollar-prefixed number
            nums = re.findall(r"\$\s*(\d[\d,]*\.?\d*)", raw_text)
            if nums:
                total_amount = _parse_amount(nums[-1])
        if total_amount is None:
            flags.append("amount_not_found")

        # GST
        gst_amount = None
        gst_match = _GST_RE.search(raw_text)
        if gst_match:
            gst_amount = _parse_amount(gst_match.group(1))

        # Currency
        currency = "CAD"
        cur_match = _CURRENCY_RE.search(raw_text)
        if cur_match:
            raw_cur = cur_match.group(1).upper()
            if "USD" in raw_cur or raw_cur == "US$":
                currency = "USD"

        # Vendor: first non-empty, non-numeric line
        vendor_name = None
        for line in raw_text.splitlines():
            line = line.strip()
            if line and not re.match(r"^[\d\s\W]+$", line) and len(line) > 3:
                vendor_name = line[:60]
                break
        if not vendor_name:
            flags.append("vendor_not_found")

        # Expense type: simple keyword heuristic
        lower = raw_text.lower()
        expense_type = "Unknown"
        if any(k in lower for k in ("hotel", "inn", "resort", "accommodation", "lodging")):
            expense_type = "Hotel"
        elif any(k in lower for k in ("airline", "airfare", "flight", "air canada", "westjet", "united", "delta")):
            expense_type = "Airfare"
        elif any(k in lower for k in ("restaurant", "café", "cafe", "bistro", "food", "dine", "dinner", "lunch", "breakfast", "pizza", "sushi")):
            expense_type = "Meal"
        elif any(k in lower for k in ("rental", "hertz", "avis", "enterprise", "budget car")):
            expense_type = "Car Rental"

        if expense_type != "Unknown":
            confidence = 0.6

        return ExtractionResult(
            expense_date=expense_date,
            vendor_name=vendor_name,
            total_amount=total_amount,
            currency=currency,
            gst_amount=gst_amount,
            expense_type=expense_type,
            raw_text=raw_text,
            confidence=confidence,
            flags=flags,
        )
