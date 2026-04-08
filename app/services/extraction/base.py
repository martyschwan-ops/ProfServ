"""
Abstract base class for extraction providers.
All providers must implement extract(raw_text) → ExtractionResult.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.expense import ExtractionResult


class BaseExtractor(ABC):
    """Interface for AI/rule-based receipt extraction providers."""

    @abstractmethod
    def extract(self, raw_text: str, file_name: str = "") -> ExtractionResult:
        """Parse raw receipt text and return structured fields."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...
