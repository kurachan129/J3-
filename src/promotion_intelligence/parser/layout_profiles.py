from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re

import fitz


class ReportLayout(StrEnum):
    DATASTADIUM_2024 = "datastadium_2024"
    DATASTADIUM_2025 = "datastadium_2025"


@dataclass(frozen=True, slots=True)
class LayoutProfile:
    layout: ReportLayout
    expected_page_count: tuple[int, ...]
    metric_pages: dict[str, int]
    page1_labels: dict[str, tuple[str, ...]]
    notes: tuple[str, ...] = ()


COMMON_METRIC_PAGES = {
    "summary": 1,
    "shooting": 3,
    "crosses": 7,
    "attacking": 8,
    "defensive": 9,
}


PROFILES: dict[ReportLayout, LayoutProfile] = {
    ReportLayout.DATASTADIUM_2024: LayoutProfile(
        layout=ReportLayout.DATASTADIUM_2024,
        expected_page_count=(17,),
        metric_pages=COMMON_METRIC_PAGES,
        page1_labels={
            "opponent_half_possession": ("保持割合", "相手陣保持割合"),
            "distance": ("総移動距離",),
        },
        notes=("Base 2024 Match Report layout",),
    ),
    ReportLayout.DATASTADIUM_2025: LayoutProfile(
        layout=ReportLayout.DATASTADIUM_2025,
        expected_page_count=(18,),
        metric_pages=COMMON_METRIC_PAGES,
        page1_labels={
            "opponent_half_possession": ("相手陣保持割合", "保持割合"),
            "distance": ("総移動距離", "総移動距離（km）"),
        },
        notes=(
            "Ranking blocks may be appended to Pages 7, 8 and 9",
            "Coordinate-based parsing must prefer the central current-match table",
        ),
    ),
}


_YEAR_RE = re.compile(r"(?P<year>20\d{2})[/-]")


def detect_layout(pdf_path: Path) -> LayoutProfile:
    """Detect the Match Report profile from header season and page count."""
    with fitz.open(pdf_path) as document:
        page_count = document.page_count
        if page_count < 1:
            raise ValueError("PDF has no pages")
        page1_text = document.load_page(0).get_text("text")

    match = _YEAR_RE.search(page1_text)
    if match:
        year = int(match.group("year"))
        if year == 2024:
            profile = PROFILES[ReportLayout.DATASTADIUM_2024]
        elif year == 2025:
            profile = PROFILES[ReportLayout.DATASTADIUM_2025]
        else:
            raise ValueError(f"unsupported Match Report season: {year}")

        if page_count not in profile.expected_page_count:
            raise ValueError(
                f"layout/page-count mismatch: season={year}, pages={page_count}, "
                f"expected={profile.expected_page_count}"
            )
        return profile

    candidates = [
        profile for profile in PROFILES.values() if page_count in profile.expected_page_count
    ]
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError(f"unable to detect Match Report layout: pages={page_count}")
