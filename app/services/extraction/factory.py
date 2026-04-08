"""
Provider factory – returns the configured extractor, falling back to mock.
"""
from __future__ import annotations

import logging

from app.services.extraction.base import BaseExtractor

logger = logging.getLogger(__name__)


def get_extractor() -> BaseExtractor:
    from config import settings

    provider = settings.extraction_provider.lower()

    if provider == "anthropic":
        try:
            from app.services.extraction.anthropic_provider import AnthropicProvider
            return AnthropicProvider()
        except Exception as exc:
            logger.warning("AnthropicProvider unavailable (%s), falling back to mock", exc)

    elif provider == "openai":
        try:
            from app.services.extraction.openai_provider import OpenAIProvider
            return OpenAIProvider()
        except Exception as exc:
            logger.warning("OpenAIProvider unavailable (%s), falling back to mock", exc)

    from app.services.extraction.mock_provider import MockProvider
    return MockProvider()
