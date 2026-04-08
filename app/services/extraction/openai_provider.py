"""
OpenAI extraction provider.

Requires OPENAI_API_KEY in environment / .env.
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
- flags: list of strings describing any uncertainty

Rules:
- Never invent values you cannot find in the text
- If a field is absent, return null
- Return ONLY the JSON object"""


class OpenAIProvider(BaseExtractor):
    provider_name = "openai"

    def __init__(self) -> None:
        from config import settings
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        except ImportError:
            raise ImportError("openai package not installed: pip install openai")

    def extract(self, raw_text: str, file_name: str = "") -> ExtractionResult:
        user_content = f"Receipt file: {file_name}\n\nRaw text:\n{raw_text[:6000]}"
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=512,
            )
            raw_json = response.choices[0].message.content.strip()
            data = json.loads(raw_json)
        except Exception as exc:
            logger.error("OpenAI extraction failed: %s", exc)
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
