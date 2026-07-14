from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from promotion_intelligence.parser.layout_profiles import detect_layout
from promotion_intelligence.parser.page1_layout import parse_page1
from promotion_intelligence.parser.page3_layout import parse_page3
from promotion_intelligence.parser.page7_layout import parse_page7
from promotion_intelligence.parser.page8_layout import parse_page8
from promotion_intelligence.parser.page9_layout import parse_page9


@dataclass(frozen=True, slots=True)
class UnifiedMatchReport:
    layout: str
    source_filename: str
    identity: dict[str, Any]
    home: dict[str, Any]
    away: dict[str, Any]
    qc: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _merge_side(summary: Any, *page_metrics: Any) -> dict[str, Any]:
    output = summary.model_dump(mode="json") if hasattr(summary, "model_dump") else asdict(summary)
    for metrics in page_metrics:
        values = asdict(metrics)
        values.pop("source_page", None)
        values.pop("quality_flag", None)
        output.update(values)
    return output


def parse_match_report(pdf_path: Path) -> UnifiedMatchReport:
    """Parse a 2024 or 2025 DataStadium Match Report into one common JSON shape.

    Values are taken only from explicit report fields. Missing values remain ``None``.
    """
    profile = detect_layout(pdf_path)
    page1 = parse_page1(pdf_path)
    page3 = parse_page3(pdf_path)
    page7 = parse_page7(pdf_path)
    page8 = parse_page8(pdf_path)
    page9 = parse_page9(pdf_path)

    home = _merge_side(page1.home, page3.home, page7.home, page8.home, page9.home)
    away = _merge_side(page1.away, page3.away, page7.away, page8.away, page9.away)

    required_pages = tuple(profile.metric_pages.values())
    qc = {
        "status": "OK",
        "layout": profile.layout.value,
        "required_pages": required_pages,
        "missing_home_fields": sorted(key for key, value in home.items() if value is None),
        "missing_away_fields": sorted(key for key, value in away.items() if value is None),
    }
    if qc["missing_home_fields"] or qc["missing_away_fields"]:
        qc["status"] = "WARN"

    return UnifiedMatchReport(
        layout=profile.layout.value,
        source_filename=pdf_path.name,
        identity=page1.identity.model_dump(mode="json"),
        home=home,
        away=away,
        qc=qc,
    )
