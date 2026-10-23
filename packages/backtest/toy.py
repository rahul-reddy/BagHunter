"""Frozen, non-fitted 63-session momentum selector versus equal-weight peers and benchmark.

This is a mechanical walk-forward screening demonstration, not a strategy validation.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from packages.research.features import eligible, snapshot
from packages.shared.models import Dataset


def evaluate(dataset: Dataset, seed: int) -> dict[str, Any]:
    sessions = sorted({b.session for b in dataset.bars})
    lookup = {(b.security_id, b.session): b for b in dataset.bars}
    rows: list[dict[str, Any]] = []
    for index in range(260, min(780, len(sessions) - 23), 42):
        decision, entry, exit_day = sessions[index], sessions[index + 1], sessions[index + 22]
        asof = datetime.combine(decision, datetime.min.time(), UTC) + timedelta(hours=23)
        candidates = []
        for instrument in dataset.instruments:
            if eligible(instrument, asof):
                features = snapshot(instrument, dataset.bars, dataset.facts, asof)
                if features["dollar_volume_20d"] >= 1000000:
                    candidates.append(features)
        candidates.sort(key=lambda f: (-f["return_63d"], f["security_id"]))
        if not candidates:
            continue
        chosen = candidates[0]["security_id"]
        realized: dict[str, float] = {}
        for security_id in [c["security_id"] for c in candidates] + ["fx-market"]:
            first = lookup.get((security_id, entry))
            last = lookup.get((security_id, exit_day))
            delists = [
                a
                for a in dataset.actions
                if a.security_id == security_id
                and a.kind == "delist"
                and entry <= a.effective_date <= exit_day
            ]
            if first is None or (last is None and not delists):
                # Unknown exits are flagged and do not become optimistic filled trades.
                continue
            exit_value = delists[0].value if delists else last.close if last else 0
            realized[security_id] = exit_value / first.open - 1 - 0.004
        net = realized.get(chosen)
        peer_returns = [
            realized[c["security_id"]] for c in candidates if c["security_id"] in realized
        ]
        if net is None or len(peer_returns) != len(candidates) or "fx-market" not in realized:
            raise ValueError("Incomplete evaluation coverage; cannot summarize comparable wealth")
        rows.append(
            {
                "decision": str(decision),
                "entry": str(entry),
                "exit": str(exit_day),
                "security_id": chosen,
                "net_return": net,
                "equal_weight_net": sum(peer_returns) / len(peer_returns)
                if len(peer_returns) == len(candidates)
                else None,
                "benchmark_net": realized.get("fx-market"),
                "coverage": "FILLED" if net is not None else "UNRESOLVED_EXIT",
            }
        )
    equity = {"selector": 1.0, "equal_weight": 1.0, "benchmark": 1.0}
    curve = []
    for row in rows:
        for key, field in (
            ("selector", "net_return"),
            ("equal_weight", "equal_weight_net"),
            ("benchmark", "benchmark_net"),
        ):
            if row[field] is not None:
                equity[key] *= 1 + row[field]
        curve.append({"date": row["exit"], **equity})
    return {
        "mode": "FIXTURE",
        "status": "DEMONSTRATION_NOT_EMPIRICAL_VALIDATION",
        "seed": seed,
        "model": "frozen-63d-momentum-v0",
        "fit": "none; no tuned parameters",
        "split": "Sequential decisions; 21-session holding windows, 21-session cash gaps. "
        "No training or untouched holdout claim.",
        "execution": "Next weekday open, exit 21 sessions later at close; long only; "
        "20 bps each way; flat cash between windows; reinvest full equity",
        "cost_round_trip_bps": 40,
        "rows": rows,
        "equity_curve": curve,
        "period_start": rows[0]["decision"],
        "period_end": rows[-1]["exit"],
        "limitations": [
            "FIXTURE data only; no alpha or probability inference",
            "Weekdays, not an exchange calendar",
            "No capacity/sector constraints",
            "No risk-free accrual in cash gaps",
            "No split/dividend events in toy sample",
            "No statistical confidence intervals; too few artificial observations",
        ],
        "ending_wealth": equity,
    }
