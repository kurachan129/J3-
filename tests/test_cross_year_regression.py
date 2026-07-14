from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from promotion_intelligence.parser.orchestrator import parse_match_report


FIXTURE_DIR = Path(__file__).parent / "fixtures"


CASES = [
    (
        "GR_20240302_J3_02_大宮vs岐阜.pdf",
        "omiya_gifu_2024_r02_page1.expected.json",
    ),
    (
        "GR_20250705_J3_19_栃木Ｃvs琉球.pdf",
        "tochigi_ryukyu_2025_r19.expected.json",
    ),
]


def _assert_subset(actual: dict[str, Any], expected: dict[str, Any], path: str = "root") -> None:
    for key, expected_value in expected.items():
        assert key in actual, f"missing key: {path}.{key}"
        actual_value = actual[key]
        if isinstance(expected_value, dict):
            assert isinstance(actual_value, dict), f"expected object: {path}.{key}"
            _assert_subset(actual_value, expected_value, f"{path}.{key}")
        elif isinstance(expected_value, float):
            assert actual_value == pytest.approx(expected_value, abs=0.001), (
                f"value mismatch: {path}.{key}: {actual_value} != {expected_value}"
            )
        else:
            assert actual_value == expected_value, (
                f"value mismatch: {path}.{key}: {actual_value} != {expected_value}"
            )


@pytest.mark.parametrize(("pdf_name", "fixture_name"), CASES)
def test_verified_match_report_subset(pdf_name: str, fixture_name: str) -> None:
    reports_dir = Path("reports/regression")
    pdf_path = reports_dir / pdf_name
    if not pdf_path.exists():
        pytest.skip(f"regression PDF is not present: {pdf_path}")

    expected = json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))
    actual = parse_match_report(pdf_path).to_dict()
    _assert_subset(actual, expected)


def test_cross_year_fixtures_share_common_contract() -> None:
    fixture_names = [
        "omiya_gifu_2024_r02_page1.expected.json",
        "tochigi_ryukyu_2025_r19.expected.json",
    ]
    fixtures = [
        json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))
        for fixture_name in fixture_names
    ]

    common_top_level = {"identity", "home", "away"}
    for fixture in fixtures:
        assert common_top_level.issubset(fixture)
        assert {"season", "round_no", "home_team", "away_team"}.issubset(
            fixture["identity"]
        )

    assert set(fixtures[0]["home"]) <= set(fixtures[1]["home"]) | {
        "source_page",
        "quality_flag",
    }
