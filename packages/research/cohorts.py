"""Multi-anchor hindsight cohort grids, physically separate from predictor construction."""

from datetime import UTC, datetime
from typing import Any

from packages.research.features import eligible
from packages.research.outcomes import outcome
from packages.shared.models import Dataset


def cohort_grid(dataset: Dataset) -> dict[str, Any]:
    sessions = sorted({b.session for b in dataset.bars})
    anchors = []
    for year in sorted({day.year for day in sessions})[1:]:
        anchors.append(next(day for day in sessions if day.year == year))
    labels = []
    grid = []
    for anchor in anchors:
        clock = datetime(anchor.year, anchor.month, anchor.day, 23, tzinfo=UTC)
        population = [i for i in dataset.instruments if eligible(i, clock)]
        for years in (1, 2, 3, 5):
            records: list[dict[str, Any]] = []
            for instrument in population:
                bars = [b for b in dataset.bars if b.security_id == instrument.security_id]
                if not any(b.session == anchor for b in bars):
                    record = {
                        "security_id": instrument.security_id,
                        "anchor": str(anchor),
                        "horizon_years": years,
                        "max_multiple": None,
                        "terminal_total_return": None,
                        "max_drawdown": None,
                        "coverage_flag": "MISSING_ANCHOR",
                        "delisted": None,
                    }
                else:
                    record = outcome(
                        instrument.security_id, dataset.bars, dataset.actions, anchor, years
                    )
                records.append(record | {"sector": instrument.sector})
            labels.extend(records)
            for sector in ["ALL", *sorted({i.sector for i in population})]:
                selected = [r for r in records if sector == "ALL" or r["sector"] == sector]
                complete = [r for r in selected if r["max_multiple"] is not None]
                for threshold in (5, 10, 20, 100):
                    hits = sum(r["max_multiple"] >= threshold for r in complete)
                    grid.append(
                        {
                            "anchor": str(anchor),
                            "horizon_years": years,
                            "sector": sector,
                            "threshold": threshold,
                            "eligible": len(selected),
                            "complete": len(complete),
                            "missing": len(selected) - len(complete),
                            "cases": hits,
                            "failed_terminal": sum(
                                r["terminal_total_return"] < 0 for r in complete
                            ),
                            "delisted": sum(bool(r["delisted"]) for r in selected),
                            "observed_fraction": hits / len(complete) if complete else None,
                        }
                    )
    return {
        "mode": "FIXTURE",
        "scope": "ARTIFICIAL_UNIVERSE_DESCRIPTIVE_ONLY_NOT_POPULATION_BASE_RATES",
        "anchors": [str(a) for a in anchors],
        "labels": labels,
        "grid": grid,
        "limitations": [
            "Overlapping horizons are correlated; no independent sample-count inference",
            "Missing outcomes remain in eligible denominators; no survival-only denominator",
            "Case/control sampling is retrospective; not predictive population probabilities",
        ],
    }
