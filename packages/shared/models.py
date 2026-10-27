"""Validated raw records. Observation timestamps are UTC and never inferred from period ends."""

import math
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class Instrument(Record):
    security_id: str
    ticker: str
    name: str
    sector: str
    first_seen: date
    last_seen: date | None = None
    security_type: Literal["common", "benchmark"] = "common"
    cap_bucket: str = "fixture-small"
    liquidity_bucket: str = "fixture-liquid"
    price_bucket: str = "fixture-5-25"
    delisted: bool = False


class Symbol(Record):
    security_id: str
    ticker: str
    valid_from: date
    valid_to: date | None = None


class Bar(Record):
    security_id: str
    session: date
    available_at: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)
    source_id: str
    adjustment_policy: Literal["raw"] = "raw"

    @model_validator(mode="after")
    def valid_range(self) -> "Bar":
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("OHLC range is inconsistent")
        return self

    @field_validator("available_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("timezone required")
        return value


class Fact(Record):
    security_id: str
    period_end: date
    accepted_at: datetime
    published_at: datetime
    metric: str
    value: float
    unit: str
    accession: str
    amended: bool = False
    source_id: str
    source_url: str

    @model_validator(mode="after")
    def valid_times(self) -> "Fact":
        if self.accepted_at.utcoffset() is None or self.published_at.utcoffset() is None:
            raise ValueError("timezone required")
        accepted_utc = self.accepted_at.astimezone(UTC)
        published_utc = self.published_at.astimezone(UTC)
        if published_utc < accepted_utc or self.period_end > accepted_utc.date():
            raise ValueError("invalid filing timeline")
        if not math.isfinite(self.value):
            raise ValueError("nonfinite fact")
        return self


class Action(Record):
    security_id: str
    effective_date: date
    kind: Literal["split", "dividend", "delist"]
    value: float = Field(ge=0)
    source_id: str

    @model_validator(mode="after")
    def positive_split(self) -> "Action":
        if self.kind == "split" and self.value <= 0:
            raise ValueError("split ratio must be positive")
        return self


class Dataset(Record):
    mode: Literal["FIXTURE"]
    instruments: list[Instrument]
    symbols: list[Symbol]
    bars: list[Bar]
    facts: list[Fact]
    actions: list[Action]
