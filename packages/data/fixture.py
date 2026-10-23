"""Entirely synthetic deterministic observations, never a substitute for market evidence."""

import math
from datetime import UTC, date, datetime, timedelta

from packages.shared.models import Action, Bar, Dataset, Fact, Instrument, Symbol


def fixture() -> Dataset:
    instruments = [
        Instrument(
            security_id="fx-compound",
            ticker="DEMO-A",
            name="Fixture Compounder",
            sector="Fixture industrials",
            first_seen=date(2019, 1, 1),
        ),
        Instrument(
            security_id="fx-failure",
            ticker="DEMO-B",
            name="Fixture Failed Lookalike",
            sector="Fixture industrials",
            first_seen=date(2019, 1, 1),
            last_seen=date(2022, 4, 5),
            delisted=True,
        ),
        Instrument(
            security_id="fx-steady",
            ticker="DEMO-C",
            name="Fixture Steady Peer",
            sector="Fixture services",
            first_seen=date(2019, 1, 1),
        ),
        Instrument(
            security_id="fx-market",
            ticker="DEMO-M",
            name="Fixture Market Baseline",
            sector="Fixture market",
            first_seen=date(2019, 1, 1),
            security_type="benchmark",
        ),
    ]
    days = [date(2019, 1, 1) + timedelta(days=i) for i in range(1550)]
    days = [d for d in days if d.weekday() < 5]  # Weekdays, NOT an exchange calendar.
    bars: list[Bar] = []
    facts: list[Fact] = []
    for k, instrument in enumerate(instruments):
        for i, day in enumerate(days):
            if instrument.last_seen and day > instrument.last_seen:
                continue
            if k == 0:
                close = 10 * math.exp(max(0, min(i - 270, 250)) * 0.0075)
                close *= 1 + 0.015 * math.sin(i / 8)
            elif k == 1:
                close = 10 * math.exp(-max(0, i - 310) * 0.005)
                close *= 1 + 0.015 * math.sin(i / 8)
            else:
                close = (10 + k) * math.exp(0.00025 * i) * (1 + 0.015 * math.sin(i / 9))
            bars.append(
                Bar(
                    security_id=instrument.security_id,
                    session=day,
                    available_at=datetime.combine(day, datetime.min.time(), UTC)
                    + timedelta(hours=22),
                    open=round(close * 0.998, 4),
                    high=round(close * 1.012, 4),
                    low=round(close * 0.988, 4),
                    close=round(close, 4),
                    volume=200000 + i % 20 * 2000,
                    source_id="fixture-v1",
                )
            )
        if instrument.security_type == "common":
            for year in (2019, 2020, 2021, 2022):
                published = datetime(year, 5, 1, 12, tzinfo=UTC)
                facts.append(
                    Fact(
                        security_id=instrument.security_id,
                        period_end=date(year - 1, 12, 31),
                        accepted_at=published,
                        published_at=published,
                        metric="annual_revenue",
                        value=100000000 * (1 + (0.3 if k == 0 else -0.08) * (year - 2019)),
                        unit="USD",
                        accession=f"FIXTURE-{k}-{year}",
                        source_id="fixture-v1",
                        source_url="fixture://fixture-v1",
                    )
                )
    return Dataset(
        mode="FIXTURE",
        instruments=instruments,
        bars=bars,
        facts=facts,
        symbols=[
            Symbol(security_id=i.security_id, ticker=i.ticker, valid_from=i.first_seen)
            for i in instruments
        ],
        actions=[
            Action(
                security_id="fx-failure",
                effective_date=date(2022, 4, 6),
                kind="delist",
                value=0,
                source_id="fixture-v1",
            )
        ],
    )
