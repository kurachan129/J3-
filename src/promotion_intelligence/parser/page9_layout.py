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
    cleaned = text.replace(",", "").replace("%", "").replace("m", "").strip()
    match = re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _central(words: list[Word], labels: tuple[str, ...], *, y_min: float = 0, y_max: float = 900) -> list[Word]:
    return sorted(
        [
            word
            for word in words
            if word.text in labels and 300 <= word.cx <= 625 and y_min <= word.cy <= y_max
        ],
        key=lambda word: (word.cy, word.cx),
    )


def _anchor(words: list[Word], labels: tuple[str, ...], *, occurrence: int = 0) -> Word:
    matches = _central(words, labels)
    if occurrence >= len(matches):
        raise ValueError(f"Page 9 section was not found: {labels}")
    return matches[occurrence]


def _pair_at(words: list[Word], anchor: Word, *, y_tolerance: float = 5.8) -> tuple[float | None, float | None]:
    row = [word for word in words if abs(word.cy - anchor.cy) <= y_tolerance]
    left = [word for word in row if 285 <= word.cx < anchor.cx - 7 and _number(word.text) is not None]
    right = [word for word in row if anchor.cx + 7 < word.cx <= 645 and _number(word.text) is not None]
    home = _number(max(left, key=lambda word: word.cx).text) if left else None
    away = _number(min(right, key=lambda word: word.cx).text) if right else None
    return home, away


def _metric(
    words: list[Word],
    labels: tuple[str, ...],
    *,
    y_min: float,
    y_max: float,
    occurrence: int = 0,
) -> tuple[float | None, float | None]:
    matches = _central(words, labels, y_min=y_min, y_max=y_max)
    if occurrence >= len(matches):
        return None, None
    return _pair_at(words, matches[occurrence])


def _as_int(value: float | None) -> int | None:
    return int(value) if value is not None else None


def parse_page9(pdf_path: Path) -> Page9Metrics:
    """Parse Page 9 using section-bounded coordinate extraction.

    The 2025 report appends ranking blocks below the current-match table. All
    repeated labels are therefore restricted to the central table and to their
    visual section. Missing values remain ``None`` and are never inferred.
    """
    with fitz.open(pdf_path) as document:
        if document.page_count < 9:
            raise ValueError("PDF does not contain Page 9")
        words = _words(document.load_page(8))

    tackle = _anchor(words, ("タックル",))
    defensive = _anchor(words, ("守備プレー",))
    gains = _anchor(words, ("ボールゲイン", "ボールゲイン　(ポゼッションリカバリー)"))
    aerial = _anchor(words, ("空中戦",))
    discipline = _anchor(words, ("ディシプリン",))

    values = {
        "tackles_total": _metric(words, ("総数",), y_min=tackle.cy, y_max=defensive.cy),
        "tackles_won": _metric(words, ("奪取数",), y_min=tackle.cy, y_max=defensive.cy, occurrence=0),
        "tackle_success_pct": _metric(words, ("奪取率",), y_min=tackle.cy, y_max=defensive.cy, occurrence=0),
        "tackle_line": _metric(words, ("タックルライン",), y_min=tackle.cy, y_max=defensive.cy),
        "attacking_third_tackles": _metric(words, ("ATでのタックル",), y_min=tackle.cy, y_max=defensive.cy),
        "attacking_third_tackles_won": _metric(words, ("奪取数",), y_min=tackle.cy, y_max=defensive.cy, occurrence=1),
        "attacking_third_tackle_success_pct": _metric(words, ("奪取率",), y_min=tackle.cy, y_max=defensive.cy, occurrence=1),
        "middle_third_tackles": _metric(words, ("MTでのタックル",), y_min=tackle.cy, y_max=defensive.cy),
        "middle_third_tackles_won": _metric(words, ("奪取数",), y_min=tackle.cy, y_max=defensive.cy, occurrence=2),
        "middle_third_tackle_success_pct": _metric(words, ("奪取率",), y_min=tackle.cy, y_max=defensive.cy, occurrence=2),
        "defensive_third_tackles": _metric(words, ("DTでのタックル",), y_min=tackle.cy, y_max=defensive.cy),
        "defensive_third_tackles_won": _metric(words, ("奪取数",), y_min=tackle.cy, y_max=defensive.cy, occurrence=3),
        "defensive_third_tackle_success_pct": _metric(words, ("奪取率",), y_min=tackle.cy, y_max=defensive.cy, occurrence=3),
        "defensive_actions": _metric(words, ("守備プレー",), y_min=defensive.cy - 2, y_max=gains.cy),
        "clearances": _metric(words, ("クリア",), y_min=defensive.cy, y_max=gains.cy),
        "own_pa_clearances": _metric(words, ("自陣PA内クリア",), y_min=defensive.cy, y_max=gains.cy),
        "blocks": _metric(
            words,
            ("ブロック（シュート）",),
            y_min=defensive.cy,
            y_max=gains.cy,
        ),
        "interceptions": _metric(words, ("インターセプト",), y_min=defensive.cy, y_max=gains.cy),
        "ball_gains_total": _metric(words, ("総数",), y_min=gains.cy, y_max=aerial.cy, occurrence=0),
        "ball_gains_at": _metric(words, ("AT", "AT回数"), y_min=gains.cy, y_max=aerial.cy, occurrence=0),
        "ball_gains_mt": _metric(words, ("MT", "MT回数"), y_min=gains.cy, y_max=aerial.cy, occurrence=0),
        "ball_gains_dt": _metric(words, ("DT", "DT回数"), y_min=gains.cy, y_max=aerial.cy, occurrence=0),
        "ball_gains_at_pct": _metric(words, ("AT割合",), y_min=gains.cy, y_max=aerial.cy),
        "ball_gains_mt_pct": _metric(words, ("MT割合",), y_min=gains.cy, y_max=aerial.cy),
        "ball_gains_dt_pct": _metric(words, ("DT割合",), y_min=gains.cy, y_max=aerial.cy),
        "gain_line": _metric(words, ("ゲインライン", "ゲインライン(m)"), y_min=gains.cy, y_max=aerial.cy),
        "regains_within_5s": _metric(words, ("ロスト後5秒以内リゲイン",), y_min=gains.cy, y_max=aerial.cy),
        "regain_within_5s_pct": _metric(words, ("5秒以内割合",), y_min=gains.cy, y_max=aerial.cy),
        "aerial_duels_opponent_half": _metric(words, ("相手陣での空中戦",), y_min=aerial.cy, y_max=discipline.cy),
        "aerial_duels_opponent_half_won": _metric(words, ("勝ち数",), y_min=aerial.cy, y_max=discipline.cy, occurrence=0),
        "aerial_duels_opponent_half_win_pct": _metric(words, ("勝率",), y_min=aerial.cy, y_max=discipline.cy, occurrence=0),
        "aerial_duels_own_half": _metric(words, ("自陣での空中戦",), y_min=aerial.cy, y_max=discipline.cy),
        "aerial_duels_own_half_won": _metric(words, ("勝ち数",), y_min=aerial.cy, y_max=discipline.cy, occurrence=1),
        "aerial_duels_own_half_win_pct": _metric(words, ("勝率",), y_min=aerial.cy, y_max=discipline.cy, occurrence=1),
        "fouls": _metric(words, ("ファウル",), y_min=discipline.cy, y_max=720),
        "defensive_third_fouls": _metric(words, ("DTでのファウル",), y_min=discipline.cy, y_max=720),
        "offsides": _metric(words, ("オフサイド",), y_min=discipline.cy, y_max=720),
    }

    int_fields = {
        "tackles_total", "tackles_won", "attacking_third_tackles",
        "attacking_third_tackles_won", "middle_third_tackles",
        "middle_third_tackles_won", "defensive_third_tackles",
        "defensive_third_tackles_won", "defensive_actions", "clearances",
        "own_pa_clearances", "blocks", "interceptions", "ball_gains_total",
        "ball_gains_at", "ball_gains_mt", "ball_gains_dt", "regains_within_5s",
        "aerial_duels_opponent_half", "aerial_duels_opponent_half_won",
        "aerial_duels_own_half", "aerial_duels_own_half_won", "fouls",
        "defensive_third_fouls", "offsides",
    }

    def build(index: int) -> Page9TeamMetrics:
        payload: dict[str, int | float | None] = {}
        for name, pair in values.items():
            value = pair[index]
            payload[name] = _as_int(value) if name in int_fields else value
        missing = sum(value is None for value in payload.values())
        quality = "OK" if missing == 0 else "WARN"
        return Page9TeamMetrics(**payload, quality_flag=quality)

    return Page9Metrics(home=build(0), away=build(1))
