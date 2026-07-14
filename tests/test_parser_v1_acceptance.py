from __future__ import annotations

import os
from pathlib import Path

import pytest

from promotion_intelligence.parser.orchestrator import parse_match_report


REPORT_DIR = Path(os.getenv("PI_REGRESSION_REPORT_DIR", "reports/regression"))
EXPECTED_FILES = (
    "GR_20240224_J3_01_大宮vs八戸.pdf",
    "GR_20240302_J3_02_大宮vs岐阜.pdf",
    "GR_20240421_J3_03_福島vs大宮.pdf",
    "GR_20240316_J3_04_大宮vs奈良.pdf",
    "GR_20240320_J3_05_相模原vs大宮.pdf",
    "GR_20240323_J3_06_大宮vs宮崎.pdf",
    "GR_20240331_J3_07_北九州vs大宮.pdf",
    "GR_20240406_J3_08_大宮vsFC大阪.pdf",
    "GR_20240410_J3_09_YS横浜vs大宮.pdf",
    "GR_20240414_J3_10_大宮vs沼津.pdf",
    "GR_20250705_J3_19_栃木Ｃvs琉球.pdf",
)


def _reports() -> list[Path]:
    paths = [REPORT_DIR / name for name in EXPECTED_FILES]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        pytest.skip(f"regression PDFs not installed: {missing}")
    return paths


def test_parser_v1_acceptance_on_11_reports() -> None:
    reports = [_safe_parse(path) for path in _reports()]
    assert len(reports) == 11

    for report in reports:
        assert report.layout in {"datastadium_2024", "datastadium_2025"}
        assert report.identity["home_team"]
        assert report.identity["away_team"]
        assert report.home["goals_for"] == report.away["goals_against"]
        assert report.away["goals_for"] == report.home["goals_against"]

        for side in (report.home, report.away):
            _assert_non_negative(side)
            _assert_percent_ranges(side)
            _assert_count_relationships(side)


def _safe_parse(path: Path):
    try:
        return parse_match_report(path)
    except Exception as exc:  # pragma: no cover - assertion message only
        pytest.fail(f"failed to parse {path.name}: {exc}")


def _assert_non_negative(side: dict[str, object]) -> None:
    for key, value in side.items():
        if value is None or isinstance(value, (str, bool)):
            continue
        if key.endswith("_pct") or key.endswith("_line") or key == "xg":
            continue
        if isinstance(value, (int, float)):
            assert value >= 0, f"{key} must be non-negative"


def _assert_percent_ranges(side: dict[str, object]) -> None:
    for key, value in side.items():
        if value is None or not key.endswith("_pct"):
            continue
        assert 0 <= value <= 100, f"{key} outside 0..100: {value}"


def _assert_count_relationships(side: dict[str, object]) -> None:
    relationships = (
        ("shots_on_target", "shots"),
        ("cross_successes", "crosses"),
        ("through_pass_successes", "through_passes"),
        ("dribble_successes", "dribbles"),
        ("tackles_won", "tackles_total"),
        ("attacking_third_tackles_won", "attacking_third_tackles"),
        ("middle_third_tackles_won", "middle_third_tackles"),
        ("defensive_third_tackles_won", "defensive_third_tackles"),
        ("aerial_duels_opponent_half_won", "aerial_duels_opponent_half"),
        ("aerial_duels_own_half_won", "aerial_duels_own_half"),
    )
    for numerator, denominator in relationships:
        num = side.get(numerator)
        den = side.get(denominator)
        if num is not None and den is not None:
            assert num <= den, f"{numerator}={num} exceeds {denominator}={den}"
