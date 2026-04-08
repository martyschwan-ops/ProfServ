"""
Historical FX service.

Primary provider: Frankfurter API (https://www.frankfurter.app) – free, no key.
Rates are cached locally in a JSON file to avoid repeated network calls.
Manual override is supported when the API is unavailable.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

_FRANKFURTER_BASE = "https://api.frankfurter.dev/v1"
_CACHE: Dict[str, float] = {}  # in-memory cache: "YYYY-MM-DD:FROM:TO" -> rate
_CACHE_FILE: Path = Path(settings.fx_cache_file)


def _cache_key(d: date, from_currency: str, to_currency: str) -> str:
    return f"{d.isoformat()}:{from_currency}:{to_currency}"


def _load_disk_cache() -> None:
    if _CACHE_FILE.exists():
        try:
            data = json.loads(_CACHE_FILE.read_text())
            _CACHE.update(data)
        except Exception as exc:
            logger.warning("Could not read FX cache file: %s", exc)


def _save_disk_cache() -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(_CACHE, indent=2))
    except Exception as exc:
        logger.warning("Could not write FX cache file: %s", exc)


def _fetch_rate_frankfurter(d: date, from_currency: str, to_currency: str) -> Optional[float]:
    """Fetch a historical rate from Frankfurter. Returns None on failure."""
    url = f"{_FRANKFURTER_BASE}/{d.isoformat()}?from={from_currency}&to={to_currency}"
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        rate = data.get("rates", {}).get(to_currency)
        if rate is not None:
            return float(rate)
    except Exception as exc:
        logger.warning("Frankfurter FX lookup failed for %s %s→%s: %s", d, from_currency, to_currency, exc)
    return None


def get_rate(d: date, from_currency: str = "USD", to_currency: str = "CAD") -> Optional[float]:
    """
    Return the historical exchange rate for *d*.
    Checks in-memory cache → disk cache → API.
    Returns None if unavailable (caller should prompt for manual override).
    """
    if from_currency == to_currency:
        return 1.0

    # Load disk cache on first call
    if not _CACHE:
        _load_disk_cache()

    key = _cache_key(d, from_currency, to_currency)
    if key in _CACHE:
        return _CACHE[key]

    rate = _fetch_rate_frankfurter(d, from_currency, to_currency)
    if rate is not None:
        _CACHE[key] = rate
        _save_disk_cache()

    return rate


def store_manual_rate(d: date, from_currency: str, to_currency: str, rate: float) -> None:
    """Persist a manually entered exchange rate to both caches."""
    key = _cache_key(d, from_currency, to_currency)
    _CACHE[key] = rate
    _save_disk_cache()


def convert_to_cad(amount: float, d: date, from_currency: str) -> tuple[Optional[float], Optional[float]]:
    """
    Convert *amount* in *from_currency* to CAD for date *d*.
    Returns (amount_cad, rate_used).  Both are None if rate unavailable.
    """
    if from_currency == "CAD":
        return amount, 1.0
    rate = get_rate(d, from_currency=from_currency, to_currency="CAD")
    if rate is None:
        return None, None
    return round(amount * rate, 2), rate
