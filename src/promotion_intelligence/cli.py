from __future__ import annotations

import json
from pathlib import Path

import typer

from promotion_intelligence.batch import run_batch
from promotion_intelligence.parser.orchestrator import parse_match_report

app = typer.Typer(no_args_is_help=True)


@app.command("parse")
def parse_report(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Parse one 2024/2025 Match Report into unified JSON."""
    result = parse_match_report(pdf).to_dict()
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if output is None:
        typer.echo(payload)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload + "\n", encoding="utf-8")
    typer.echo(str(output))


@app.command("batch")
def batch_reports(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, readable=True),
    output_dir: Path = typer.Argument(..., file_okay=False),
) -> None:
    """Parse Match Report PDFs and write match JSON plus QC reports."""
    results = run_batch(input_dir, output_dir)
    errors = sum(result.status == "ERROR" for result in results)
    typer.echo(f"reports={len(results)} errors={errors} output={output_dir}")
    if errors:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
