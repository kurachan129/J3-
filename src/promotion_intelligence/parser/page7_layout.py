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
class Page7TeamMetrics:
    crosses: int | None
    cross_successes: int | None
    cross_success_pct: float | None
    right_crosses: int | None
    right_cross_successes: int | None
    right_cross_success_pct: float | None
    right_cross_share_pct: float | None
    left_crosses: int | None
    left_cross_successes: int | None
    left_cross_success_pct: float | None
    left_cross_share_pct: float | None
    pa_inside_crosses: int | None
    pa_inside_cross_successes: int | None
    pa_inside_cross_success_pct: float | None
    pa_inside_cross_share_pct: float | None
    pa_outside_crosses: int | None
    pa_outside_cross_successes: int | None
    pa_outside_cross_success_pct: float | None
    pa_outside_cross_share_pct: float | None
    last_pass_crosses: int | None
    cross_to_shot_within_3_plays: int | None
    through_passes: int | None
    through_pass_successes: int | None
    through_pass_success_pct: float | None
    last_pass_through_passes: int | None
    through_pass_to_shot_within_3_plays: int | None
    dribbles: int | None
    dribble_successes: int | None
    dribble_success_pct: float | None
    source_page: int = 7
    quality_flag: str = "OK"


@dataclass(frozen=True, slots=True)
class Page7Metrics:
    home: Page7TeamMetrics
    away: Page7TeamMetrics

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        for side in ("home", "away"):
            values = payload[side]
            values["crosses_to_shot_within_3_plays"] = values[
                "cross_to_shot_within_3_plays"
            ]
            values["through_passes_to_shot_within_3_plays"] = values[
                "through_pass_to_shot_within_3_plays"
            ]
        return payload


def _words(page: fitz.Page) -> list[Word]:
    return [Word(*row[:5]) for row in page.get_text("words")]


def _number(text: str) -> float | None:
    cleaned = text.replace(",", "").replace("%", "").strip()
    match = re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _central_labels(words: list[Word], label: str) -> list[Word]:
    return sorted(
        [word for word in words if word.text == label and 450 <= word.cx <= 535],
        key=lambda word: word.cy,
    )


def _section_anchor(words: list[Word], title: str) -> Word:
    labels = _central_labels(words, title)
    if not labels:
        raise ValueError(f"Page 7 section was not found: {title}")
    return labels[0]


def _pair_at_label(words: list[Word], label_word: Word, y_tolerance: float = 5.5) -> tuple[float | None, float | None]:
    row = [word for word in words if abs(word.cy - label_word.cy) <= y_tolerance]
    left = [word for word in row if 350 <= word.cx < label_word.cx - 8 and _number(word.text) is not None]
    right = [word for word in row if label_word.cx + 8 < word.cx <= 630 and _number(word.text) is not None]
    home = _number(max(left, key=lambda word: word.cx).text) if left else None
    away = _number(min(right, key=lambda word: word.cx).text) if right else None
    return home, away


def _metric_pair(
    words: list[Word],
    label: str,
    *,
    y_min: float,
    y_max: float,
    occurrence: int = 0,
) -> tuple[float | None, float | None]:
    labels = [word for word in _central_labels(words, label) if y_min <= word.cy <= y_max]
    if occurrence >= len(labels):
        return None, None
    return _pair_at_label(words, labels[occurrence])


def _as_int(value: float | None) -> int | None:
    return int(value) if value is not None else None


def parse_page7(pdf_path: Path) -> Page7Metrics:
    """Parse Page 7 crossing, through-pass and dribble metrics by PDF coordinates.

    Each repeated row label is constrained to its visual section. This prevents
    values such as cross success and dribble success from being mixed up.
    Missing values remain ``None`` and are never inferred.
    """
    with fitz.open(pdf_path) as document:
        if document.page_count < 7:
            raise ValueError("PDF does not contain Page 7")
        words = _words(document.load_page(6))

    cross = _section_anchor(words, "クロス")
    area = _section_anchor(words, "エリア別クロス")
    cross_shot = _section_anchor(words, "シュートにつながったクロス")
    through = _section_anchor(words, "スルーパス")
    through_shot = _section_anchor(words, "シュートにつながったスルーパス")
    dribble = _section_anchor(words, "ドリブル")

    values = {
        "crosses": _metric_pair(words, "総数", y_min=cross.cy, y_max=area.cy),
        "cross_successes": _metric_pair(words, "成功数", y_min=cross.cy, y_max=area.cy),
        "cross_success_pct": _metric_pair(words, "成功率", y_min=cross.cy, y_max=area.cy),
        "right_crosses": _metric_pair(words, "右サイドからのクロス", y_min=area.cy, y_max=cross_shot.cy),
        "right_cross_successes": _metric_pair(words, "成功数", y_min=area.cy, y_max=cross_shot.cy, occurrence=0),
        "right_cross_success_pct": _metric_pair(words, "成功率", y_min=area.cy, y_max=cross_shot.cy, occurrence=0),
        "right_cross_share_pct": _metric_pair(words, "割合", y_min=area.cy, y_max=cross_shot.cy, occurrence=0),
        "left_crosses": _metric_pair(words, "左サイドからのクロス", y_min=area.cy, y_max=cross_shot.cy),
        "left_cross_successes": _metric_pair(words, "成功数", y_min=area.cy, y_max=cross_shot.cy, occurrence=1),
        "left_cross_success_pct": _metric_pair(words, "成功率", y_min=area.cy, y_max=cross_shot.cy, occurrence=1),
        "left_cross_share_pct": _metric_pair(words, "割合", y_min=area.cy, y_max=cross_shot.cy, occurrence=1),
        "pa_inside_crosses": _metric_pair(words, "PA内からのクロス", y_min=area.cy, y_max=cross_shot.cy),
        "pa_inside_cross_successes": _metric_pair(words, "成功数", y_min=area.cy, y_max=cross_shot.cy, occurrence=2),
        "pa_inside_cross_success_pct": _metric_pair(words, "成功率", y_min=area.cy, y_max=cross_shot.cy, occurrence=2),
        "pa_inside_cross_share_pct": _metric_pair(words, "割合", y_min=area.cy, y_max=cross_shot.cy, occurrence=2),
        "pa_outside_crosses": _metric_pair(words, "PA外からのクロス", y_min=area.cy, y_max=cross_shot.cy),
        "pa_outside_cross_successes": _metric_pair(words, "成功数", y_min=area.cy, y_max=cross_shot.cy, occurrence=3),
        "pa_outside_cross_success_pct": _metric_pair(words, "成功率", y_min=area.cy, y_max=cross_shot.cy, occurrence=3),
        "pa_outside_cross_share_pct": _metric_pair(words, "割合", y_min=area.cy, y_max=cross_shot.cy, occurrence=3),
        "last_pass_crosses": _metric_pair(words, "ラストパスクロス", y_min=cross_shot.cy, y_max=through.cy),
        "cross_to_shot_within_3_plays": _metric_pair(words, "3プレー以内シュート", y_min=cross_shot.cy, y_max=through.cy),
        "through_passes": _metric_pair(words, "総数", y_min=through.cy, y_max=through_shot.cy),
        "through_pass_successes": _metric_pair(words, "成功数", y_min=through.cy, y_max=through_shot.cy),
        "through_pass_success_pct": _metric_pair(words, "成功率", y_min=through.cy, y_max=through_shot.cy),
        "last_pass_through_passes": _metric_pair(words, "ラストパススルーパス", y_min=through_shot.cy, y_max=dribble.cy),
        "through_pass_to_shot_within_3_plays": _metric_pair(words, "3プレー以内シュート", y_min=through_shot.cy, y_max=dribble.cy),
        "dribbles": _metric_pair(words, "総数", y_min=dribble.cy, y_max=700),
        "dribble_successes": _metric_pair(words, "成功数", y_min=dribble.cy, y_max=700),
        "dribble_success_pct": _metric_pair(words, "成功率", y_min=dribble.cy, y_max=700),
    }

    int_fields = {
        "crosses",
        "cross_successes",
        "right_crosses",
        "right_cross_successes",
        "left_crosses",
        "left_cross_successes",
        "pa_inside_crosses",
        "pa_inside_cross_successes",
        "pa_outside_crosses",
        "pa_outside_cross_successes",
        "last_pass_crosses",
        "cross_to_shot_within_3_plays",
        "through_passes",
        "through_pass_successes",
        "last_pass_through_passes",
        "through_pass_to_shot_within_3_plays",
        "dribbles",
        "dribble_successes",
    }

    def build(index: int) -> Page7TeamMetrics:
        payload: dict[str, int | float | None] = {}
        for name, pair in values.items():
            value = pair[index]
            payload[name] = _as_int(value) if name in int_fields else value
        return Page7TeamMetrics(**payload)

    return Page7Metrics(home=build(0), away=build(1))
