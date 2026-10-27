"""Frozen, non-fitted 63-session momentum selector versus equal-weight peers and benchmark.

This is a mechanical walk-forward screening demonstration, not a strategy validation.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from packages.research.discovery import DiscoveryPolicy, ranking_snapshot
from packages.research.features import eligible, snapshot
from packages.shared.models import Dataset
from packages.shared.numeric import require_finite


def evaluate(
    dataset: Dataset, seed: int, discovery_policy: DiscoveryPolicy | None = None
) -> dict[str, Any]:
    sessions = sorted({b.session for b in dataset.bars})
    lookup = {(b.security_id, b.session): b for b in dataset.bars}
    identity_dates = {i.security_id: str(i.first_seen) for i in dataset.instruments}
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
        policy = discovery_policy or DiscoveryPolicy()
        discovered = ranking_snapshot(dataset, asof, policy)
        discovery_candidates = [
            f
            for f in discovered
            if f["eligible"]
            and f["close"] >= policy.min_price
            and f["dollar_volume_20d"] >= policy.min_dollar_volume
        ]
        if not candidates:
            continue
        chosen = candidates[0]["security_id"]
        realized: dict[str, float] = {}
        for security_id in sorted(
            {c["security_id"] for c in candidates + discovery_candidates} | {"fx-market"}
        ):
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
        if any(c["security_id"] not in realized for c in discovery_candidates):
            raise ValueError("Incomplete discovery evaluation coverage")
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
                "label_available_at": max(
                    datetime.combine(exit_day, datetime.min.time(), UTC) + timedelta(hours=23),
                    max(
                        b.available_at
                        for b in dataset.bars
                        if b.session <= exit_day and b.security_id in realized
                    ),
                ).isoformat(),
                "candidates": [
                    {
                        "security_id": c["security_id"],
                        "identity_first_seen": identity_dates[c["security_id"]],
                        "signal_score": c["return_63d"],
                        "signal_at": asof.isoformat(),
                        "latest_publication": c["latest_included_publication"],
                        "net_return": realized[c["security_id"]],
                    }
                    for c in candidates
                ],
                "eligible_count": len(candidates),
                "discovery_candidates": [
                    {
                        "security_id": c["security_id"],
                        "identity_first_seen": identity_dates[c["security_id"]],
                        "signal_score": c["score"],
                        "signal_at": asof.isoformat(),
                        "latest_publication": c["latest_included_publication"],
                        "net_return": realized[c["security_id"]],
                    }
                    for c in discovery_candidates
                ],
            }
        )
    require_finite(rows, "frozen evaluation ledger")
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
        require_finite(equity, "toy compounded wealth")
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
