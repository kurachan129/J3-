from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QualityFlag(StrEnum):
    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"


class HomeAway(StrEnum):
    HOME = "H"
    AWAY = "A"


class MatchIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season: int = Field(ge=2000, le=2100)
    round_no: int = Field(ge=1)
    match_date: date
    home_team: str = Field(min_length=1)
    away_team: str = Field(min_length=1)
    source_filename: str = Field(min_length=1)


class TeamSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team: str = Field(min_length=1)
    opponent: str = Field(min_length=1)
    home_away: HomeAway
    goals_for: int = Field(ge=0)
    goals_against: int = Field(ge=0)
    possession_pct: float | None = Field(default=None, ge=0, le=100)
    opponent_half_possession_pct: float | None = Field(default=None, ge=0, le=100)
    shots: int | None = Field(default=None, ge=0)
    shots_on_target: int | None = Field(default=None, ge=0)
    xg: float | None = Field(default=None, ge=0)
    pa_entries: int | None = Field(default=None, ge=0)
    final30_entries: int | None = Field(default=None, ge=0)
    crosses: int | None = Field(default=None, ge=0)
    cross_success_pct: float | None = Field(default=None, ge=0, le=100)
    passes: int | None = Field(default=None, ge=0)
    pass_success_pct: float | None = Field(default=None, ge=0, le=100)
    corners: int | None = Field(default=None, ge=0)
    tackles: int | None = Field(default=None, ge=0)
    defensive_actions: int | None = Field(default=None, ge=0)
    source_page: int = Field(default=1, ge=1)
    quality_flag: QualityFlag = QualityFlag.OK

    @property
    def points(self) -> int:
        if self.goals_for > self.goals_against:
            return 3
        if self.goals_for == self.goals_against:
            return 1
        return 0


class ParsedMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity: MatchIdentity
    home: TeamSummary
    away: TeamSummary

    @model_validator(mode="after")
    def validate_mirror(self) -> "ParsedMatch":
        if self.home.home_away is not HomeAway.HOME:
            raise ValueError("home summary must have home_away='H'")
        if self.away.home_away is not HomeAway.AWAY:
            raise ValueError("away summary must have home_away='A'")
        if self.home.team != self.identity.home_team:
            raise ValueError("home team mismatch")
        if self.away.team != self.identity.away_team:
            raise ValueError("away team mismatch")
        if self.home.opponent != self.away.team or self.away.opponent != self.home.team:
            raise ValueError("opponent names are not mirrored")
        if self.home.goals_for != self.away.goals_against:
            raise ValueError("home goals do not mirror away goals against")
        if self.away.goals_for != self.home.goals_against:
            raise ValueError("away goals do not mirror home goals against")
        return self
