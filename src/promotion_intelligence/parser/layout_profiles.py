from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReportLayout(StrEnum):
    DATASTADIUM_2024 = "datastadium_2024"
    DATASTADIUM_2025 = "datastadium_2025"


@dataclass(frozen=True, slots=True)
class LayoutProfile:
    layout: ReportLayout
    expected_page_count: tuple[int, ...]
    metric_pages: dict[str, int]
    page1_labels: dict[str, tuple[str, ...]]
    notes: