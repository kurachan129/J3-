from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ExtractedValue:
    value: int | float | str | None
    source_page: int
    source_label: str
    raw_text: str | None
    confidence: float
    warning: str | None = None


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def first_match(patterns: Iterable[str], text: str, flags: int = re.IGNORECASE) -> re.Match[str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match
    return None


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").strip()
    return int(cleaned) if cleaned.isdigit() else None


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None
