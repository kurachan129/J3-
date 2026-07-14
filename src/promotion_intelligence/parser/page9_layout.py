from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

import fitz


@dataclass(frozen=True, slots=True)
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass(frozen=True, slots=True)
class Page9TeamMetrics:
    tackles_total: int | None
    tackles_won: int | None
    tackle_success_pct: float | None
    tackle_line: float | None
    attacking_third_tackles: int | None
    attacking_third_tackles_won: int | None
    attacking_third_tackle_success_pct: float | None
    middle_third_tackles: int | None
    middle_third_tackles_won: int | None
    middle_third_tackle_success_pct: float | None
    defensive_third_tackles: int | None
    defensive_third_tackles_won: int | None
    defensive_third_tackle_success_pct: float | None
    defensive_actions: int | None
    clearances: int | None
    own_pa_clearances: int | None
    blocks: int | None
    interceptions: int | None
    ball_gains_total: int | None
    ball_gains_at: int | None
    ball_gains_mt: int | None
    ball_gains_dt: int | None
    ball_gains_at_pct: float | None
    ball_gains_mt_pct: float | None
    ball_gains_dt_pct: float | None
    gain_line: float | None
    regains_within_5s: int | None
    regain_within_5s_pct: float | None
    aerial_duels_opponent_half: int | None
    aerial_duels_opponent_half_won: int | None
    aerial_duels_opponent_half_win_pct: float | None
    aerial_duels_own_half: int | None
    aerial_duels_own_half_won: int | None
    aerial_duels_own_half_win_pct: float | None
    fouls: int | None
    defensive_third_fouls: int | None
    offsides: int | None
    source_page: int = 9
    quality_flag: str = "OK"


@dataclass(frozen=True, slots=True)
class Page9Metrics:
    home: Page9TeamMetrics
    away: Page9TeamMetrics

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _words(page: fitz.Page) -> list[Word]:
    return [Word(*row[:5]) for row in page.get_text("words")]


def _number(text: str) -> float | None:
    cleaned = text.replace(",", "").replace("%", "").strip()
    match = re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _labels(words: list[Word], label: str) -> list[Word]:
    return sorted(
        [word for word in words if word.text == label and 300 <= word.cx <= 620],
        key=lambda word: word.cy,
    )


def _metric_pair(
    words: list[Word],
    label: str,
    *,
    occurrence: int = 0,
    y_tolerance: float = 5.5,
) -> tuple[float | None, float | None]:
    candidates = _labels(words, label)
    if occurrence >= len(candidates):
        return None, None
    anchor = candidates[occurrence]
    row = [word for word in words if abs(word.cy - anchor.cy) <= y_tolerance]
    left = [word for word in row if 300 <= word.cx < anchor.cx - 8 and _number(word.text) is not None]
    right = [word for word in row if anchor.cx + 8 < word.cx <= 620 and _number(word.text) is not None]
    home = _number(max(left, key=lambda word: word.cx).text) if left else None
    away = _number(min(right, key=lambda word: word.cx).text) if right else None
    return home, away


def _as_int(value: float | None) -> int | None:
    return int(value) if value is not None else None


def parse_page9(pdf_path: Path) -> Page9Metrics:
    """Parse Page 9 defensive metrics from the two values nearest each central label.

    Missing or unreadable metrics are kept as ``None``. The parser does not infer
    values from totals, percentages, charts, or neighboring rows.
    """
    with fitz.open(pdf_path) as document:
        if document.page_count < 9:
            raise ValueError("PDF does not contain Page 9")
        words = _words(document.load_page(8))

    metrics = {
        "tackles_total": _metric_pair(words, "総数", occurrence=0),
        "tackles_won": _metric_pair(words, "奪取数", occurrence=0),
        "tackle_success_pct": _metric_pair(words, "奪取率", occurrence=0),
        "tackle_line": _metric_pair(words, "タックルライン"),
        "attacking_third_tackles": _metric_pair(words, "ATでのタックル"),
        "attacking_third_tackles_won": _metric_pair(words, "奪取数", occurrence=1),
        "attacking_third_tackle_success_pct": _metric_pair(words, "奪取率", occurrence=1),
        "middle_third_tackles": _metric_pair(words, "MTでのタックル"),
        "middle_third_tackles_won": _metric_pair(words, "奪取数", occurrence=2),
        "middle_third_tackle_success_pct": _metric_pair(words, "奪取率", occurrence=2),
        "defensive_third_tackles": _metric_pair(words, "DTでのタックル"),
        "defensive_third_tackles_won": _metric_pair(words, "奪取数", occurrence=3),
        "defensive_third_tackle_success_pct": _metric_pair(words, "奪取率", occurrence=3),
        "defensive_actions": _metric_pair(words, "守備プレー"),
        "clearances": _metric_pair(words, "クリア"),
        "own_pa_clearances": _metric_pair(words, "自陣PA内クリア"),
        "blocks": _metric_pair(words, "ブロック"),
        "interceptions": _metric_pair(words, "インターセプト"),
        "ball_gains_total": _metric_pair(words, "総数", occurrence=1),
        "ball_gains_at": _metric_pair(words, "AT", occurrence=0),
        "ball_gains_mt": _metric_pair(words, "MT", occurrence=0),
        "ball_gains_dt": _metric_pair(words, "DT", occurrence=0),
        "ball_gains_at_pct": _metric_pair(words, "AT割合"),
        "ball_gains_mt_pct": _metric_pair(words, "MT割合"),
        "ball_gains_dt_pct": _metric_pair(words, "DT割合"),
        "gain_line": _metric_pair(words, "ゲインライン"),
        "regains_within_5s": _metric_pair(words, "ロスト後5秒以内リゲイン"),
        "regain_within_5s_pct": _metric_pair(words, "5秒以内割合"),
        "aerial_duels_opponent_half": _metric_pair(words, "相手陣での空中戦"),
        "aerial_duels_opponent_half_won": _metric_pair(words, "勝ち数", occurrence=0),
        "aerial_duels_opponent_half_win_pct": _metric_pair(words, "勝率", occurrence=0),
        "aerial_duels_own_half": _metric_pair(words, "自陣での空中戦"),
        "aerial_duels_own_half_won": _metric_pair(words, "勝ち数", occurrence=1),
        "aerial_duels_own_half_win_pct": _metric_pair(words, "勝率", occurrence=1),
        "fouls": _metric_pair(words, "ファウル"),
        "defensive_third_fouls": _metric_pair(words, "DTでのファウル"),
        "offsides": _metric_pair(words, "オフサイド"),
    }

    int_fields = {
        "tackles_total",
        "tackles_won",
        "attacking_third_tackles",
        "attacking_third_tackles_won",
        "middle_third_tackles",
        "middle_third_tackles_won",
        "defensive_third_tackles",
        "defensive_third_tackles_won",
        "defensive_actions",
        "clearances",
        "own_pa_clearances",
        "blocks",
        "interceptions",
        "ball_gains_total",
        "ball_gains_at",
        "ball_gains_mt",
        "ball_gains_dt",
        "regains_within_5s",
        "aerial_duels_opponent_half",
        "aerial_duels_opponent_half_won",
        "aerial_duels_own_half",
        "aerial_duels_own_half_won",
        "fouls",
        "defensive_third_fouls",
        "offsides",
    }

    def build(index: int) -> Page9TeamMetrics:
        values: dict[str, int | float | None] = {}
        for name, pair in metrics.items():
            value = pair[index]
            values[name] = _as_int(value) if name in int_fields else value
        return Page9TeamMetrics(**values)

    return Page9Metrics(home=build(0), away=build(1))
