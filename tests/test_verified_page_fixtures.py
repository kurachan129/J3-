from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from promotion_intelligence.parser.page3_layout import parse_page3
from promotion_intelligence.parser.page7_layout import parse_page7
from promotion_intelligence.parser.orchestrator import parse_match_report


PDF = Path("reports/regression/GR_20240302_J3_02_大宮vs岐阜.pdf")
FIXTURES = Path(__file__).parent / "fixtures"


def _assert_subset(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    for key, expected_value in expected.items():
        assert key in actual
        actual_value = actual[key]
        if isinstance(expected_value, dict):
            _assert_subset(actual_value, expected_value)
        elif isinstance(expected_value, float):
            assert actual_value == pytest.approx(expected_value, abs=0.001)
        else:
            assert actual_value == expected_value


@pytest.mark.parametrize(
    ("parser", "fixture_name"),
    (
        (parse_page3, "omiya_gifu_2024_r02_page3.expected.json"),
        (parse_page7, "omiya_gifu_2024_r02_page7.expected.json"),
        (parse_match_report, "omiya_gifu_2024_r02_page9.expected.json"),
    ),
)
def test_verified_page_fixture(
    parser: Callable[[Path], Any], fixture_name: str
) -> None:
    if not PDF.exists():
        pytest.skip(f"regression PDF is not present: {PDF}")
    expected = json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    _assert_subset(parser(PDF).to_dict(), expected)
