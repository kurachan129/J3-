from __future__ import annotations

import json
from pathlib import Path

from promotion_intelligence.batch import BatchResult, write_qc_reports


def test_write_qc_reports_includes_null_lists_and_capture_rates(tmp_path: Path) -> None:
    (tmp_path / "match.json").write_text(
        json.dumps(
            {
                "home": {"shots": 4, "xg": None},
                "away": {"shots": None, "xg": 0.5},
            }
        ),
        encoding="utf-8",
    )
    results = [
        BatchResult(
            source_file="match.pdf",
            status="WARN",
            layout="datastadium_2024",
            output_file="match.json",
            missing_home_fields=1,
            missing_away_fields=1,
            null_home_fields=("xg",),
            null_away_fields=("shots",),
        )
    ]

    write_qc_reports(results, tmp_path)

    qc = json.loads((tmp_path / "qc_results.json").read_text(encoding="utf-8"))
    assert qc[0]["null_home_fields"] == ["xg"]
    summary = json.loads((tmp_path / "qc_field_capture.json").read_text(encoding="utf-8"))
    fields = {(row["side"], row["field"]): row for row in summary["fields"]}
    assert fields[("home", "shots")]["capture_rate_pct"] == 100.0
    assert fields[("home", "xg")]["capture_rate_pct"] == 0.0
    assert fields[("away", "shots")]["nulls"] == 1
