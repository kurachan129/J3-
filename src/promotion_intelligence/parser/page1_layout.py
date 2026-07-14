from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

import fitz

from promotion_intelligence.models import HomeAway, MatchIdentity, ParsedMatch, QualityFlag, TeamSummary

_HEADER_RE = re.compile(
    r"(?P<date>\d{4}/\d{2}/\d{2})\s+\d{2}:\d{2}KO\s+J3第(?P<round>\d+)節[\s　]+"
    r"(?P<home>.+?)[\s　]+(?P<hg>\d+)\s+vs\s+(?P<ag>\d+)[\s　]+(?P<away>.+?)＠"
)


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


def _words(page: fitz.Page) -> list[Word]:
    return [Word(*row[:5]) for row in page.get_text("words")]


def _header(text: str, source_filename: str) -> tuple[MatchIdentity, int, int]:
    match = _HEADER_RE.search(text)
    if not match:
        raise ValueError("page 1 match header was not found")
    identity = MatchIdentity(
        season=int(match.group("date")[:4]),
        round_no=int(match.group("round")),
        match_date=datetime.strptime(match.group("date"), "%Y/%m/%d").date(),
        home_team=match.group("home").strip(),
        away_team=match.group("away").strip(),
        source_filename=source_filename,
    )
    return identity, int(match.group("hg")), int(match.group("ag"))


def _label_word(words: list[Word], label: str) -> Word | None:
    candidates = [word for word in words if word.text == label]
    if not candidates:
        return None
    return min(candidates, key=lambda word: abs(word.cx - 460))


def _side_tokens(words: list[Word], label: Word, *, side: str, y_tolerance: float = 8.0) -> list[Word]:
    same_row = [word for word in words if abs(word.cy - label.cy) <= y_tolerance]
    if side == "left":
        same_row = [word for word in same_row if 330 <= word.cx < label.cx - 15]
    else:
        same_row = [word for word in same_row if label.cx + 15 < word.cx <= 575]
    return sorted(same_row, key=lambda word: word.x0)


def _number(text: str) -> float | None:
    cleaned = text.replace(",", "").replace("%", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _metric_pair(words: list[Word], label: str) -> tuple[float | None, float | None]:
    label_word = _label_word(words, label)
    if label_word is None:
        return None, None
    left = next((_number(w.text) for w in _side_tokens(words, label_word, side="left") if _number(w.text) is not None), None)
    right = next((_number(w.text) for w in _side_tokens(words, label_word, side="right") if _number(w.text) is not None), None)
    return left, right


def _shots_pair(words: list[Word]) -> tuple[tuple[int | None, int | None], tuple[int | None, int | None]]:
    label = _label_word(words, "シュート")
    if label is None:
        return (None, None), (None, None)

    def parse(tokens: list[Word]) -> tuple[int | None, int | None]:
        text = " ".join(word.text for word in tokens)
        match = re.search(r"(?P<shots>\d+)\s*\((?P<sot>\d+)\)", text)
        if not match:
            return None, None
        return int(match.group("shots")), int(match.group("sot"))

    return parse(_side_tokens(words, label, side="left")), parse(_side_tokens(words, label, side="right"))


def _count(value: float | None) -> int | None:
    return int(value) if value is not None else None


def parse_page1(pdf_path: Path) -> ParsedMatch:
    """Parse the Page 1 summary using PDF coordinates, not fragile text order."""
    with fitz.open(pdf_path) as document:
        if document.page_count < 1:
            raise ValueError("PDF has no pages")
        page = document.load_page(0)
        text = page.get_text("text")
        words = _words(page)

    identity, home_goals, away_goals = _header(text, pdf_path.name)
    possession = _metric_pair(words, "ボール保持率")
    opponent_half = _metric_pair(words, "保持割合")
    shots = _shots_pair(words)
    xg = _metric_pair(words, "ｘG")
    pa_entries = _metric_pair(words, "ＰＡ進入")
    final30_entries = _metric_pair(words, "30mライン進入")
    crosses = _metric_pair(words, "クロス")
    passes = _metric_pair(words, "パス")
    corners = _metric_pair(words, "CK")
    tackles = _metric_pair(words, "タックル")
    defensive_actions = _metric_pair(words, "守備プレー")

    def summary(*, home: bool) -> TeamSummary:
        index = 0 if home else 1
        return TeamSummary(
            team=identity.home_team if home else identity.away_team,
            opponent=identity.away_team if home else identity.home_team,
            home_away=HomeAway.HOME if home else HomeAway.AWAY,
            goals_for=home_goals if home else away_goals,
            goals_against=away_goals if home else home_goals,
            possession_pct=possession[index],
            opponent_half_possession_pct=opponent_half[index],
            shots=shots[index][0],
            shots_on_target=shots[index][1],
            xg=xg[index],
            pa_entries=_count(pa_entries[index]),
            final30_entries=_count(final30_entries[index]),
            crosses=_count(crosses[index]),
            passes=_count(passes[index]),
            corners=_count(corners[index]),
            tackles=_count(tackles[index]),
            defensive_actions=_count(defensive_actions[index]),
            source_page=1,
            quality_flag=QualityFlag.OK,
        )

    return ParsedMatch(identity=identity, home=summary(home=True), away=summary(home=False))
