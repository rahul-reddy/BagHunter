"""Cited, exact-period entity statement arithmetic; no security valuation or score activation."""

import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

from packages.shared.models import Fact

ANALYSIS_POLICY = "statement-metrics-v2"
Period = tuple[str, str | None, str]
StatementFact = dict[str, Any]
MetricGroup = dict[str, StatementFact]
Calculation = tuple[float | None, str | None, list[StatementFact]]


def _stamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Aware statement timestamp required")
    return parsed.astimezone(UTC)


def _identity(fact: dict[str, Any]) -> tuple[str, str, str | None, str, str]:
    return (
        fact["metric"],
        fact["basis"],
        fact["period_start"],
        fact["period_end"],
        fact["accession"],
    )


def analyze(
    report: dict[str, Any], contracts: dict[str, tuple[str, bool]], max_periods: int
) -> list[dict[str, Any]]:
    if len(report["facts"]) > 20_000 or report["processing_lag_hours"] != 24:
        raise ValueError("Statement analysis record/lag bound violated")
    clock = _stamp(report["asof"])
    latest: dict[tuple[str, str, str | None, str], dict[str, Any]] = {}
    for fact in report["facts"]:
        core = Fact(**{key: fact[key] for key in Fact.model_fields})
        contract = contracts.get(core.metric)
        if (
            contract is None
            or core.unit != contract[0]
            or core.security_id != report["security_id"]
        ):
            raise ValueError("Statement analysis unit/entity/metric mismatch")
        if type(fact["value"]) not in (int, float) or (core.unit == "shares" and core.value < 0):
            raise ValueError("Invalid statement analysis amount")
        if (
            max(_stamp(fact["accepted_at"]), _stamp(fact["published_at"])) + timedelta(hours=24)
            > clock
        ):
            raise ValueError("Statement analysis includes an unavailable fact")
        start = date.fromisoformat(fact["period_start"]) if fact["period_start"] else None
        end = date.fromisoformat(fact["period_end"])
        basis = fact["basis"]
        bounds = {
            "QUARTER": (75, 105),
            "ANNUAL": (330, 400),
            "YTD_6M": (150, 210),
            "YTD_9M": (240, 300),
        }
        if contract[1]:
            valid = basis == "INSTANT" and start is None
        else:
            valid = (
                start is not None
                and basis in bounds
                and bounds[basis][0] <= (end - start).days <= bounds[basis][1]
            )
        if not valid:
            raise ValueError("Statement analysis period mismatch")
        revision_key = (core.metric, basis, fact["period_start"], fact["period_end"])
        previous = latest.get(revision_key)
        order = (_stamp(fact["published_at"]), _stamp(fact["accepted_at"]), fact["accession"])
        prior_order = (
            None
            if previous is None
            else (
                _stamp(previous["published_at"]),
                _stamp(previous["accepted_at"]),
                previous["accession"],
            )
        )
        if previous is not None and order == prior_order and fact["value"] != previous["value"]:
            raise ValueError("Conflicting statement analysis revisions")
        if prior_order is None or order > prior_order:
            latest[revision_key] = fact
    periods: dict[tuple[str, str | None, str], dict[str, dict[str, Any]]] = {}
    for (_, period_basis, period_start, period_end), fact in latest.items():
        periods.setdefault((period_basis, period_start, period_end), {})[fact["metric"]] = fact
    if len(periods) > max_periods:
        raise ValueError("Statement analysis period count exceeds bound")

    def comparable(key: Period, metric: str) -> MetricGroup | None:
        basis, start, end = key
        found = []
        for (other_basis, other_start, other_end), values in periods.items():
            if basis != other_basis or metric not in values:
                continue
            if not 330 <= (date.fromisoformat(end) - date.fromisoformat(other_end)).days <= 400:
                continue
            if start is not None:
                if (
                    other_start is None
                    or abs(
                        (date.fromisoformat(end) - date.fromisoformat(start)).days
                        - (date.fromisoformat(other_end) - date.fromisoformat(other_start)).days
                    )
                    > 15
                ):
                    continue
            found.append(values)
        return found[0] if len(found) == 1 else None

    def chain(key: Period, count: int) -> list[Period] | None:
        keys = [key]
        while len(keys) < count:
            start = keys[-1][1]
            previous = [
                other
                for other, values in periods.items()
                if other[0] == "QUARTER"
                and "revenue" in values
                and start
                and date.fromisoformat(other[2]) + timedelta(days=1) == date.fromisoformat(start)
            ]
            if len(previous) != 1:
                return None
            keys.append(previous[0])
        return keys

    result = []
    for key, facts in sorted(
        periods.items(), key=lambda item: (item[0][0], item[0][2], item[0][1] or ""), reverse=True
    ):
        period_basis, period_start, period_end = key
        values: dict[str, float | None] = {metric: fact["value"] for metric, fact in facts.items()}
        citations = list(facts.values())
        derivations: dict[str, dict[str, Any]] = {}

        def record(
            name: str,
            value: float | None,
            reason: str | None,
            used: list[StatementFact],
            method: str,
            values: dict[str, float | None] = values,
            citations: list[StatementFact] = citations,
            derivations: dict[str, dict[str, Any]] = derivations,
        ) -> float | None:
            if value is not None and not math.isfinite(value):
                value, reason = None, "NUMERIC_RANGE"
            values[name] = value
            citations.extend(used)
            derivations[name] = {
                "method": method,
                "status": "AVAILABLE" if value is not None else "UNAVAILABLE",
                "reason": reason if value is None else None,
                "input_ids": [list(_identity(f)) for f in used],
            }
            return value

        def ratio(group: MetricGroup, numerator: str, denominator: str) -> Calculation:
            used = [group[m] for m in (numerator, denominator) if m in group]
            if len(used) != 2:
                return None, "REQUIRED_METRIC_MISSING", used
            if used[0]["accession"] != used[1]["accession"]:
                return None, "MIXED_FILINGS", used
            if used[1]["value"] <= 0:
                return None, "NONPOSITIVE_REFERENCE", used
            value = used[0]["value"] / used[1]["value"]
            return (value, None, used) if math.isfinite(value) else (None, "NUMERIC_RANGE", used)

        def yoy(group_key: Period, metric: str) -> Calculation:
            current = periods[group_key].get(metric)
            prior = comparable(group_key, metric)
            used = ([current] if current else []) + ([prior[metric]] if prior else [])
            if current is None or prior is None:
                return None, "MISSING_OR_AMBIGUOUS_PRIOR", used
            if prior[metric]["value"] <= 0:
                return None, "NONPOSITIVE_REFERENCE", used
            value = current["value"] / prior[metric]["value"] - 1
            return (value, None, used) if math.isfinite(value) else (None, "NUMERIC_RANGE", used)

        if period_basis != "INSTANT":
            for metric, output in (
                ("gross_profit", "gross_margin"),
                ("operating_income", "operating_margin"),
                ("net_income", "net_margin"),
                ("operating_cashflow", "cashflow_margin"),
                ("stock_compensation", "stock_compensation_to_revenue"),
            ):
                value, reason, used = ratio(facts, metric, "revenue")
                record(
                    output, value, reason, used, "EXACT_PERIOD_SAME_FILING_NUMERATOR_OVER_REVENUE"
                )
            for cost, output in (
                ("cost_of_revenue", "revenue_less_cost_margin"),
                ("goods_services_cost", "revenue_less_goods_services_cost_margin"),
            ):
                value, reason, used = ratio(facts, cost, "revenue")
                record(
                    output,
                    1 - value if value is not None else None,
                    reason,
                    used,
                    "REVENUE_LESS_REPORTED_COST_PROXY_NOT_REPORTED_GROSS_PROFIT",
                )
            value, reason, used = ratio(facts, "revenue", "diluted_weighted_shares")
            record(
                "revenue_per_weighted_share",
                value,
                reason,
                used,
                "USD_PER_REPORTED_DILUTED_PERIOD_AVERAGE_SHARE_NOT_SECURITY_VALUATION",
            )
            cfo, ppe = facts.get("operating_cashflow"), facts.get("ppe_payments")
            used = [f for f in (cfo, ppe) if f is not None]
            reason = (
                "REQUIRED_METRIC_MISSING"
                if cfo is None or ppe is None
                else "MIXED_FILINGS"
                if cfo["accession"] != ppe["accession"]
                else "NEGATIVE_PPE_PAYMENT"
                if ppe["value"] < 0
                else None
            )
            fcf = record(
                "cfo_less_ppe",
                cfo["value"] - ppe["value"] if reason is None and cfo and ppe else None,
                reason,
                used,
                "CFO_LESS_NONNEGATIVE_REPORTED_PPE_CASH_PAYMENTS",
            )
            income = facts.get("net_income")
            conversion_reason = (
                "FCF_PROXY_UNAVAILABLE"
                if fcf is None
                else "REQUIRED_METRIC_MISSING"
                if income is None
                else "MIXED_FILINGS"
                if cfo is None or income["accession"] != cfo["accession"]
                else "NONPOSITIVE_REFERENCE"
                if income["value"] <= 0
                else None
            )
            record(
                "cfo_less_ppe_to_income",
                fcf / income["value"]
                if conversion_reason is None and fcf is not None and income
                else None,
                conversion_reason,
                used + ([income] if income else []),
                "CFO_LESS_PPE_OVER_POSITIVE_NET_INCOME_PROXY",
            )
            for metric, output in (
                ("revenue", "revenue_yoy"),
                ("diluted_weighted_shares", "weighted_shares_yoy"),
            ):
                value, reason, used = yoy(key, metric)
                record(
                    output,
                    value,
                    reason,
                    used,
                    "ONE_COMPARABLE_SAME_BASIS_PERIOD_330_TO_400_DAYS_PRIOR",
                )
            for numerator, output in (
                ("gross_profit", "gross_margin_yoy_change"),
                ("operating_income", "operating_margin_yoy_change"),
            ):
                current, reason, used = ratio(facts, numerator, "revenue")
                prior = comparable(key, "revenue")
                before = None
                if prior is not None:
                    before, prior_reason, prior_used = ratio(prior, numerator, "revenue")
                    used += prior_used
                    if prior_reason:
                        reason = "PRIOR_MARGIN_UNAVAILABLE"
                else:
                    reason = "MISSING_OR_AMBIGUOUS_PRIOR"
                record(
                    output,
                    current - before if current is not None and before is not None else None,
                    reason,
                    used,
                    "CURRENT_LESS_PRIOR_MARGIN_FRACTION_CHANGE",
                )
            if period_basis == "QUARTER":
                for count, output in (
                    (2, "revenue_yoy_acceleration"),
                    (3, "revenue_yoy_change_2q"),
                ):
                    history = chain(key, count)
                    used = []
                    value = None
                    reason = "MISSING_OR_AMBIGUOUS_ADJACENT_QUARTER"
                    if history:
                        current, cr, cu = yoy(key, "revenue")
                        before, br, bu = yoy(history[-1], "revenue")
                        used = cu + bu
                        reason = cr or br
                        if current is not None and before is not None:
                            value = current - before
                    record(
                        output,
                        value,
                        reason,
                        used,
                        "CHANGE_IN_QUARTER_YOY_VS_PREVIOUS_QUARTER"
                        if count == 2
                        else "CHANGE_IN_QUARTER_YOY_VS_TWO_QUARTERS_EARLIER",
                    )
                for count, output in ((4, "revenue_4q"), (8, "revenue_4q_yoy")):
                    history = chain(key, count) if "revenue" in facts else None
                    used = []
                    value = None
                    reason = "MISSING_OR_AMBIGUOUS_ADJACENT_QUARTER"
                    if history:
                        used = [periods[k]["revenue"] for k in history]
                        spans = [
                            (
                                date.fromisoformat(history[i][2])
                                - date.fromisoformat(history[i + 3][1] or "")
                            ).days
                            for i in range(0, count, 4)
                        ]
                        if not all(330 <= span <= 400 for span in spans):
                            reason = "NON_ANNUAL_FOUR_QUARTER_SPAN"
                        else:
                            current = sum(f["value"] for f in used[:4])
                            prior = sum(f["value"] for f in used[4:]) if count == 8 else None
                            reason = (
                                "NUMERIC_RANGE"
                                if not math.isfinite(current)
                                or (prior is not None and not math.isfinite(prior))
                                else "NONPOSITIVE_REFERENCE"
                                if prior is not None and prior <= 0
                                else None
                            )
                            if reason is None:
                                value = current / prior - 1 if prior is not None else current
                    record(
                        output,
                        value,
                        reason,
                        used,
                        "FOUR_CONTIGUOUS_DIRECT_QUARTERS_NO_YTD_SUBTRACTION",
                    )
        else:
            assets, liabilities = facts.get("current_assets"), facts.get("current_liabilities")
            used = [f for f in (assets, liabilities) if f is not None]
            reason = (
                "REQUIRED_METRIC_MISSING"
                if assets is None or liabilities is None
                else "MIXED_FILINGS"
                if assets["accession"] != liabilities["accession"]
                else "NEGATIVE_CURRENT_BALANCE"
                if min(assets["value"], liabilities["value"]) < 0
                else None
            )
            wc = record(
                "working_capital",
                assets["value"] - liabilities["value"]
                if reason is None and assets and liabilities
                else None,
                reason,
                used,
                "CURRENT_ASSETS_LESS_CURRENT_LIABILITIES",
            )
            record(
                "current_ratio",
                assets["value"] / liabilities["value"]
                if reason is None and assets and liabilities and liabilities["value"] > 0
                else None,
                reason
                or ("NONPOSITIVE_REFERENCE" if liabilities and liabilities["value"] <= 0 else None),
                used,
                "CURRENT_ASSETS_OVER_POSITIVE_CURRENT_LIABILITIES",
            )
            prior = comparable(key, "current_assets")
            before = None
            prior_used = []
            if prior and "current_liabilities" in prior:
                a, b = prior["current_assets"], prior["current_liabilities"]
                prior_used = [a, b]
                if a["accession"] == b["accession"] and min(a["value"], b["value"]) >= 0:
                    before = a["value"] - b["value"]
            record(
                "working_capital_yoy_change",
                wc - before if wc is not None and before is not None else None,
                "MISSING_OR_INCOMPATIBLE_PRIOR_BALANCES" if before is None else reason,
                used + prior_used,
                "CURRENT_LESS_PRIOR_WORKING_CAPITAL_USD_CHANGE",
            )
        result.append(
            {
                "basis": period_basis,
                "period_start": period_start,
                "period_end": period_end,
                "values": values,
                "analysis_policy": ANALYSIS_POLICY,
                "derivations": derivations,
                "citations": list({_identity(f): f for f in citations}.values()),
            }
        )
    return result
