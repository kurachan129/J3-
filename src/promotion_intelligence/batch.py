from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from promotion_intelligence.parser.orchestrator import parse_match_report


@dataclass(frozen=True, slots=True)
class BatchResult:
    source_file: str
    status: str
    layout: str | None
    output_file: str | None
    missing_home_fields: int
    missing_away_fields: int
    null_home_fields: tuple[str, ...] = ()
    null_away_fields: tuple[str, ...] = ()
    error: str | None = None


def iter_pdfs(input_dir: Path) -> Iterable[Path]:
    yield from sorted(path for path in input_dir.rglob("*.pdf") if path.is_file())


def run_batch(input_dir: Path, output_dir: Path) -> list[BatchResult]:
    """Parse every Match Report PDF below ``input_dir``.

    Each successful report is written as one JSON file. A failed report is not
    discarded: the failure is recorded in the returned QC result. Existing JSON
    files are replaced deterministically.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[BatchResult] = []

    for pdf_path in iter_pdfs(input_dir):
        relative = pdf_path.relative_to(input_dir)
        json_path = (output_dir / relative).with_suffix(".json")
        json_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            report = parse_match_report(pdf_path)
            payload = report.to_dict()
            json_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            qc = payload["qc"]
            results.append(
                BatchResult(
                    source_file=str(relative),
                    status=str(qc["status"]),
                    layout=str(payload["layout"]),
                    output_file=str(json_path.relative_to(output_dir)),
                    missing_home_fields=len(qc.get("missing_home_fields", [])),
                    missing_away_fields=len(qc.get("missing_away_fields", [])),
                    null_home_fields=tuple(qc.get("missing_home_fields", [])),
                    null_away_fields=tuple(qc.get("missing_away_fields", [])),
                )
            )
        except Exception as exc:  # Batch processing must continue after one bad PDF.
            results.append(
                BatchResult(
                    source_file=str(relative),
                    status="ERROR",
                    layout=None,
                    output_file=None,
                    missing_home_fields=0,
                    missing_away_fields=0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    write_qc_reports(results, output_dir)
    return results


def write_qc_reports(results: list[BatchResult], output_dir: Path) -> None:
    rows = [asdict(result) for result in results]
    (output_dir / "qc_results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [field.name for field in BatchResult.__dataclass_fields__.values()]
    with (output_dir / "qc_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            {
                **row,
                "null_home_fields": "|".join(row["null_home_fields"]),
                "null_away_fields": "|".join(row["null_away_fields"]),
            }
            for row in rows
        )

    summary = _field_capture_summary(output_dir, results)
    (output_dir / "qc_field_capture.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "qc_field_capture.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("side", "field", "reports", "acquired", "nulls", "capture_rate_pct"),
        )
        writer.writeheader()
        writer.writerows(summary["fields"])


def _field_capture_summary(output_dir: Path, results: list[BatchResult]) -> dict[str, Any]:
    field_counts: dict[tuple[str, str], list[int]] = {}
    successful = 0
    for result in results:
        if result.output_file is None:
            continue
        payload = json.loads((output_dir / result.output_file).read_text(encoding="utf-8"))
        successful += 1
        for side in ("home", "away"):
            for field, value in payload[side].items():
                if field in {"team", "opponent", "home_away", "source_page", "quality_flag"}:
                    continue
                counts = field_counts.setdefault((side, field), [0, 0])
                counts[0] += 1
                if value is not None:
                    counts[1] += 1

    fields = []
    for (side, field), (reports, acquired) in sorted(field_counts.items()):
        fields.append(
            {
                "side": side,
                "field": field,
                "reports": reports,
                "acquired": acquired,
                "nulls": reports - acquired,
                "capture_rate_pct": round(acquired / reports * 100, 1) if reports else 0.0,
            }
        )
    return {
        "reports_total": len(results),
        "reports_successful": successful,
        "reports_failed": len(results) - successful,
        "fields": fields,
    }
