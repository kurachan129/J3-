from pathlib import Path

import pytest

from promotion_intelligence.parser.page8_layout import parse_page8


CASES = [
    (
        Path("reports/regression/GR_20240302_J3_02_大宮vs岐阜.pdf"),
        {
            "home": {"pa_entries_p8": 14, "near_zone_total": 13, "corners_p8": 2, "throw_ins": 19},
            "away": {"pa_entries_p8": 16, "near_zone_total": 9, "corners_p8": 8, "throw_ins": 27},
        },
    ),
    (
        Path("reports/regression/GR_20250705_J3_19_栃木Ｃvs琉球.pdf"),
        {
            "home": {"pa_entries_p8": 25, "near_zone_total": 19, "corners_p8": 11, "throw_ins": 25},
            "away": {"pa_entries_p8": 7, "near_zone_total": 4, "corners_p8": 1, "throw_ins": 20},
        },
    ),
]


@pytest.mark.parametrize(("pdf_path", "expected"), CASES)
def test_page8_current_match_values(pdf_path: Path, expected: dict[str, dict[str, int]]) -> None:
    if not pdf_path.exists():
        pytest.skip(f"regression PDF is not available: {pdf_path}")

    parsed = parse_page8(pdf_path)
    for side_name in ("home", "away"):
        side = getattr(parsed, side_name)
        for field_name, expected_value in expected[side_name].items():
            assert getattr(side, field_name) == expected_value
