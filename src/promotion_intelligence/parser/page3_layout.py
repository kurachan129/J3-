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
class Page3TeamMetrics:
    goals: int | None
    shots: int | None
    shots_on_target: int | None
    shot_accuracy_pct: float | None
    shots_off_target: int | None
    other_shots: int | None
    xg: float | None
    xg_0_1_plus: int | None
    xg_0_2_plus: int | None
    one_touch_shots: int | None
    one_touch_pct: float | None
    pa_goals: int | None
    pa_shots: int | None
    pa_shots_on_target: int | None
    pa_shot_accuracy_pct: float | None
    pa_shot_rate_pct: float | None
    outside_pa_goals: int | None
    outside_pa_shots: int | None
    outside_pa_shots_on_target: int | None
    outside_pa_accuracy_pct: float | None
    set_piece_goals: int | None
    set_piece_shots: int | None
    direct_fk_goals: int | None
    direct_fk_shots: int | None
    pk_goals: int | None
    pk_shots: int | None
    source_page: int = 3
    quality_flag: str = "OK"


@dataclass(frozen=True, slots=True)
class Page3Metrics:
    home: Page3TeamMetrics
    away: Page3TeamMetrics

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _words(page: fitz.Page) -> list[Word]:
    return [Word(*row[:5]) for row in page.get_text("words")]


def _number(text: str) -> float | None:
    cleaned = text.replace(",", "").replace("%", "").strip()
    match = re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _label_candidates(words: list[Word], label: str) -> list[Word]:
    return sorted(
        [word for word in words if word.text == label and 300 <= word.cx <= 560],
        key=lambda word: word.cy,
    )


def _metric_pair(
    words: list[Word],
    label: str,
    *,
    occurrence: int = 0,
    y_tolerance: float = 5.5,
) -> tuple[float | None, float | None]:
    labels = _label_candidates(words, label)
    if occurrence >= len(labels):
        return None, None
    target = labels[occurrence]
    row = [word for word in words if abs(word.cy - target.cy) <= y_tolerance]

    left = [word for word in row if 300 <= word.cx < target.cx - 8 and _number(word.text) is not None]
    right = [word for word in row if target.cx + 8 < word.cx <= 610 and _number(word.text) is not None]

    # The current-match value is the number closest to the central label.
    home = _number(max(left, key=lambda word: word.cx).text) if left else None
    away = _number(min(right, key=lambda word: word.cx).text) if right else None
    return home, away


def _as_int(value: float | None) -> int | None:
    return int(value) if value is not None else None


def parse_page3(pdf_path: Path) -> Page3Metrics:
    """Parse Page 3 shot metrics using PDF coordinates.

    The parser deliberately reads the two values nearest each central metric label.
    This avoids confusing season averages with the current-match values.
    Missing or unreadable values remain ``None``.
    """
    with fitz.open(pdf_path) as document:
        if document.page_count < 3:
            raise ValueError("PDF does not contain Page 3")
        words = _words(document.load_page(2))

    top = {
        "goals": _metric_pair(words, "ゴール", occurrence=0),
        "shots": _metric_pair(words, "シュート", occurrence=0),
        "shots_on_target": _metric_pair(words, "枠内シュート", occurrence=0),
        "shot_accuracy_pct": _metric_pair(words, "枠内率", occurrence=0),
        "shots_off_target": _metric_pair(words, "枠外シュート"),
        "other_shots": _metric_pair(words, "その他のシュート"),
        "xg": _metric_pair(words, "xG"),
        "xg_0_1_plus": _metric_pair(words, "xGが0.1以上のシュート"),
        "xg_0_2_plus": _metric_pair(words, "xGが0.2以上のシュート"),
        "one_touch_shots": _metric_pair(words, "ワンタッチシュート"),
        "one_touch_pct": _metric_pair(words, "ワンタッチ比率"),
        "pa_goals": _metric_pair(words, "ゴール", occurrence=1),
        "pa_shots": _metric_pair(words, "シュート", occurrence=1),
        "pa_shots_on_target": _metric_pair(words, "枠内シュート", occurrence=1),
        "pa_shot_accuracy_pct": _metric_pair(words, "枠内率", occurrence=1),
        "pa_shot_rate_pct": _metric_pair(words, "PA内シュート率"),
        "outside_pa_goals": _metric_pair(words, "ゴール", occurrence=2),
        "outside_pa_shots": _metric_pair(words, "シュート", occurrence=2),
        "outside_pa_shots_on_target": _metric_pair(words, "枠内シュート", occurrence=2),
        "outside_pa_accuracy_pct": _metric_pair(words, "枠内率", occurrence=2),
        "pk_goals": _metric_pair(words, "PKゴール"),
        "pk_shots": _metric_pair(words, "PKシュート"),
        "direct_fk_goals": _metric_pair(words, "直接FKゴール"),
        "direct_fk_shots": _metric_pair(words, "直接FKシュート"),
    }

    # In the lower left/right shot-pattern tables, the current-match values are
    # listed as shot count followed by goal count. These labels are not centered,
    # so they are parsed separately by locating the row and taking the adjacent pair.
    def pattern_pair(label: str) -> tuple[tuple[int | None, int | None], tuple[int | None, int | None]]:
        matches = [word for word in words if word.text == label]
        home_row = [word for word in matches if word.cx < 420]
        away_row = [word for word in matches if word.cx > 580]

        def values(anchor: Word | None, side: str) -> tuple[int | None, int | None]:
            if anchor is None:
                return None, None
            row = [word for word in words if abs(word.cy - anchor.cy) <= 5.5 and _number(word.text) is not None]
            if side == "home":
                nums = sorted([w for w in row if anchor.cx + 5 < w.cx < 310], key=lambda w: w.cx)
            else:
                nums = sorted([w for w in row if 790 < w.cx and w.cx < 950], key=lambda w: w.cx)
            parsed = [_as_int(_number(word.text)) for word in nums]
            return (parsed[0] if len(parsed) > 0 else None, parsed[1] if len(parsed) > 1 else None)

        return values(home_row[0] if home_row else None, "home"), values(
            away_row[0] if away_row else None, "away"
        )

    set_piece = pattern_pair("セットプレーから")

    def build(index: int) -> Page3TeamMetrics:
        def value(name: str) -> float | None:
            return top[name][index]

        return Page3TeamMetrics(
            goals=_as_int(value("goals")),
            shots=_as_int(value("shots")),
            shots_on_target=_as_int(value("shots_on_target")),
            shot_accuracy_pct=value("shot_accuracy_pct"),
            shots_off_target=_as_int(value("shots_off_target")),
            other_shots=_as_int(value("other_shots")),
            xg=value("xg"),
            xg_0_1_plus=_as_int(value("xg_0_1_plus")),
            xg_0_2_plus=_as_int(value("xg_0_2_plus")),
            one_touch_shots=_as_int(value("one_touch_shots")),
            one_touch_pct=value("one_touch_pct"),
            pa_goals=_as_int(value("pa_goals")),
            pa_shots=_as_int(value("pa_shots")),
            pa_shots_on_target=_as_int(value("pa_shots_on_target")),
            pa_shot_accuracy_pct=value("pa_shot_accuracy_pct"),
            pa_shot_rate_pct=value("pa_shot_rate_pct"),
            outside_pa_goals=_as_int(value("outside_pa_goals")),
            outside_pa_shots=_as_int(value("outside_pa_shots")),
            outside_pa_shots_on_target=_as_int(value("outside_pa_shots_on_target")),
            outside_pa_accuracy_pct=value("outside_pa_accuracy_pct"),
            set_piece_shots=set_piece[index][0],
            set_piece_goals=set_piece[index][1],
            direct_fk_goals=_as_int(value("direct_fk_goals")),
            direct_fk_shots=_as_int(value("direct_fk_shots")),
            pk_goals=_as_int(value("pk_goals")),
            pk_shots=_as_int(value("pk_shots")),
        )

    return Page3Metrics(home=build(0), away=build(1))
