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
class Page8TeamMetrics:
    pa_entries_p8: int | None
    pa_entries_through_pass: int | None
    pa_entries_cross: int | None
    pa_entries_short_pass: int | None
    pa_entries_long_pass: int | None
    pa_entries_dribble: int | None
    pa_entries_carry: int | None
    near_zone_total: int | None
    near_zone_right: int | None
    near_zone_left: int | None
    pa_entry_goals_within_3_plays: int | None
    pa_entry_shots_within_3_plays: int | None
    pa_flank_entries_total: int | None
    pa_flank_entries_right: int | None
    pa_flank_entries_left: int | None
    corners_p8: int | None
    corner_successes: int | None
    corner_last_passes: int | None
    free_kicks: int | None
    attacking_third_free_kicks: int | None
    free_kick_successes: int | None
    direct_free_kick_shots: int | None
    throw_ins: int | None
    throw_in_success_pct: float | None
    long_throws: int | None
    source_page: int = 8
    quality_flag: str = "OK"


@dataclass(frozen=True, slots=True)
class Page8Metrics:
    home: Page8TeamMetrics
    away: Page8TeamMetrics

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _words(page: fitz.Page) -> list[Word]:
    return [Word(*row[:5]) for row in page.get_text("words")]


def _number(text: str) -> float | None:
    cleaned = text.replace(",", "").replace("%", "").strip()
    match = re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _central_labels(words: list[Word], label: str) -> list[Word]:
    return sorted(
        [word for word in words if word.text == label and 430 <= word.cx <= 660],
        key=lambda word: word.cy,
    )


def _metric_pair(
    words: list[Word],
    label: str,
    *,
    occurrence: int = 0,
    y_tolerance: float = 5.5,
) -> tuple[float | None, float | None]:
    labels = _central_labels(words, label)
    if occurrence >= len(labels):
        return None, None

    anchor = labels[occurrence]
    row = [word for word in words if abs(word.cy - anchor.cy) <= y_tolerance]

    # Current-match values are the values immediately adjacent to the central label.
    # Season averages sit farther outside and are intentionally ignored.
    left = [
        word
        for word in row
        if anchor.cx - 110 <= word.cx < anchor.cx - 8 and _number(word.text) is not None
    ]
    right = [
        word
        for word in row
        if anchor.cx + 8 < word.cx <= anchor.cx + 110 and _number(word.text) is not None
    ]
    home = _number(max(left, key=lambda word: word.cx).text) if left else None
    away = _number(min(right, key=lambda word: word.cx).text) if right else None
    return home, away


def _as_int(value: float | None) -> int | None:
    return int(value) if value is not None else None


def parse_page8(pdf_path: Path) -> Page8Metrics:
    """Parse Page 8 attacking-play metrics from explicit current-match values.

    Values are read from the two numbers nearest each central metric label. Missing
    fields remain ``None``; no totals or percentages are inferred.
    """
    with fitz.open(pdf_path) as document:
        if document.page_count < 8:
            raise ValueError("PDF does not contain Page 8")
        words = _words(document.load_page(7))

    values = {
        "pa_entries_p8": _metric_pair(words, "総数", occurrence=0),
        "pa_entries_through_pass": _metric_pair(words, "スルーパスによる進入"),
        "pa_entries_cross": _metric_pair(words, "クロスによる進入"),
        "pa_entries_short_pass": _metric_pair(words, "30m未満パスによる進入"),
        "pa_entries_long_pass": _metric_pair(words, "30m以上パスによる進入"),
        "pa_entries_dribble": _metric_pair(words, "ドリブルによる進入"),
        "pa_entries_carry": _metric_pair(words, "キープによる進入"),
        "near_zone_total": _metric_pair(words, "総数", occurrence=1),
        "near_zone_right": _metric_pair(words, "右ニアゾーン進入"),
        "near_zone_left": _metric_pair(words, "左ニアゾーン進入"),
        "pa_entry_goals_within_3_plays": _metric_pair(words, "3プレー以内得点"),
        "pa_entry_shots_within_3_plays": _metric_pair(words, "3プレー以内シュート"),
        "pa_flank_entries_total": _metric_pair(words, "総数", occurrence=2),
        "pa_flank_entries_right": _metric_pair(words, "右脇進入"),
        "pa_flank_entries_left": _metric_pair(words, "左脇進入"),
        "corners_p8": _metric_pair(words, "総数", occurrence=3),
        "corner_successes": _metric_pair(words, "成功数", occurrence=0),
        "corner_last_passes": _metric_pair(words, "ラストパス"),
        "free_kicks": _metric_pair(words, "総数", occurrence=4),
        "attacking_third_free_kicks": _metric_pair(words, "ATでのFK総数"),
        "free_kick_successes": _metric_pair(words, "成功数", occurrence=1),
        "direct_free_kick_shots": _metric_pair(words, "FK直接シュート"),
        "throw_ins": _metric_pair(words, "総数", occurrence=5),
        "throw_in_success_pct": _metric_pair(words, "成功率"),
        "long_throws": _metric_pair(words, "ロングスロー"),
    }

    int_fields = {name for name in values if name != "throw_in_success_pct"}

    def build(index: int) -> Page8TeamMetrics:
        payload: dict[str, int | float | None] = {}
        for name, pair in values.items():
            value = pair[index]
            payload[name] = _as_int(value) if name in int_fields else value
        return Page8TeamMetrics(**payload)

    return Page8Metrics(home=build(0), away=build(1))
