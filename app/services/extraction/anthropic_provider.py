"""
Anthropic Claude extraction provider.

Requires ANTHROPIC_API_KEY in environment / .env.
Falls back to MockProvider if the key is absent.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Optional

from app.models.expense import ExtractionResult
from app.services.extraction.base import BaseExtractor

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert receipt parser. Given raw text extracted from a receipt, return a JSON object with exactly these keys:
- expense_date: ISO date string (YYYY-MM-DD) or null
- vendor_name: string or null
- total_amount: number or null (the final total the customer paid)
- currency: "CAD" or "USD" or null
- gst_amount: number or null (GST/HST only, not tips)
- expense_type: one of "Meal", "Hotel", "Airfare", "Car Rental", "Other", "Unknown"
- confidence: 0.0 to 1.0 (your overall confidence)
- flags: list of strings describing any uncertainty (e.g. ["date_ambiguous", "amount_unclear"])

Rules:
- Never invent values you cannot find in the text
- If a field is genuinely absent, return null
- If the date format is ambiguous, include "date_ambiguous" in flags
- If vendor name is unclear, include "vendor_unclear" in flags
- If GST is not found, return null for gst_amount
- Return ONLY the JSON object, no markdown fences"""


class AnthropicProvider(BaseExtractor):
    provider_name = "anthropic"

    def __init__(self) -> None:
        from config import settings
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        except ImportError:
            raise ImportError("anthropic package not installed: pip install anthropic")

    def extract(self, raw_text: str, file_name: str = "") -> ExtractionResult:
        import anthropic

        user_content = f"Receipt file: {file_name}\n\nRaw text:\n{raw_text[:6000]}"
        try:
            message = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw_json = message.content[0].text.strip()
            data = json.loads(raw_json)
        except Exception as exc:
            logger.error("Anthropic extraction failed: %s", exc)
            return ExtractionResult(raw_text=raw_text, flags=["extraction_failed"], confidence=0.0)

        expense_date = None
        if data.get("expense_date"):
            try:
                expense_date = date.fromisoformat(data["expense_date"])
            except ValueError:
                data.setdefault("flags", []).append("date_parse_error")

        return ExtractionResult(
            expense_date=expense_date,
            vendor_name=data.get("vendor_name"),
            total_amount=_safe_float(data.get("total_amount")),
            currency=data.get("currency"),
            gst_amount=_safe_float(data.get("gst_amount")),
            expense_type=data.get("expense_type", "Unknown"),
            raw_text=raw_text,
            confidence=float(data.get("confidence", 0.5)),
            flags=data.get("flags") or [],
        )


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
