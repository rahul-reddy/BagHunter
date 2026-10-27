"""Bounded, accession-bound statements from immutable SEC sources; no research activation."""

import hashlib
import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from packages.data.sec_facts import accession_metadata
from packages.data.statement_metrics import analyze
from packages.shared.models import Fact

POLICY = "sec-statements-v2-period-metrics"
MAX_ANALYSIS_PERIODS = 1000
# Exact standard concepts and units. Components are never silently combined into total debt.
CONCEPTS = {
    "Revenues": ("revenue", "USD", False),
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("revenue", "USD", False),
    "SalesRevenueNet": ("revenue", "USD", False),
    "GrossProfit": ("gross_profit", "USD", False),
    "CostOfRevenue": ("cost_of_revenue", "USD", False),
    "CostOfGoodsAndServicesSold": ("goods_services_cost", "USD", False),
    "ShareBasedCompensation": ("stock_compensation", "USD", False),
    "AssetsCurrent": ("current_assets", "USD", True),
    "LiabilitiesCurrent": ("current_liabilities", "USD", True),
    "OperatingIncomeLoss": ("operating_income", "USD", False),
    "NetIncomeLoss": ("net_income", "USD", False),
    "NetCashProvidedByUsedInOperatingActivities": ("operating_cashflow", "USD", False),
    "PaymentsToAcquirePropertyPlantAndEquipment": ("ppe_payments", "USD", False),
    "EarningsPerShareDiluted": ("diluted_eps", "USD/shares", False),
    "WeightedAverageNumberOfDilutedSharesOutstanding": ("diluted_weighted_shares", "shares", False),
    "Assets": ("assets", "USD", True),
    "Liabilities": ("liabilities", "USD", True),
    "StockholdersEquity": ("parent_equity", "USD", True),
    "CashAndCashEquivalentsAtCarryingValue": ("cash_equivalents", "USD", True),
    "LongTermDebtCurrent": ("current_long_term_debt", "USD", True),
    "LongTermDebtNoncurrent": ("noncurrent_long_term_debt", "USD", True),
    "CommonStockSharesOutstanding": ("common_shares", "shares", True),
}


def normalize_statements(
    submissions_raw: bytes, facts_raw: bytes, security_id: str, asof: datetime
) -> dict[str, Any]:
    if asof.utcoffset() is None or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", security_id
    ):
        raise ValueError("Aware statement clock and explicit entity key required")
    if max(len(submissions_raw), len(facts_raw)) > 20 * 1024 * 1024:
        raise ValueError("Statement source size exceeds bound")
    submissions, company = json.loads(submissions_raw), json.loads(facts_raw)
    cik = str(submissions["cik"])
    if not cik.isdigit() or not 0 < int(cik) < 10**10 or int(company["cik"]) != int(cik):
        raise ValueError("Statement CIK binding mismatch")
    metadata = accession_metadata(submissions)
    excluded = dict.fromkeys(
        (
            "missing_accession",
            "unsupported_unit",
            "unsupported_form_period",
            "future_or_processing_lag",
        ),
        0,
    )
    rows: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    seen = 0
    for concept, (metric, unit, instant) in CONCEPTS.items():
        for reported_unit, records in (
            company.get("facts", {}).get("us-gaap", {}).get(concept, {"units": {}})["units"].items()
        ):
            if not isinstance(records, list) or len(records) > 100_000:
                raise ValueError("Invalid statement records")
            seen += len(records)
            if seen > 100_000:
                raise ValueError("Statement input record count exceeds bound")
            for record in records:
                if reported_unit != unit:
                    excluded["unsupported_unit"] += 1
                    continue
                accession = record["accn"]
                meta = metadata.get(accession)
                if meta is None:
                    excluded["missing_accession"] += 1
                    continue
                if (
                    meta["form"] not in ("10-K", "10-K/A", "10-Q", "10-Q/A")
                    or record["form"] != meta["form"]
                ):
                    excluded["unsupported_form_period"] += 1
                    continue
                end = date.fromisoformat(record["end"])
                start = date.fromisoformat(record["start"]) if "start" in record else None
                basis = "INSTANT" if instant and start is None else ""
                if not instant and start is not None:
                    days = (end - start).days
                    if 75 <= days <= 105:
                        basis = "QUARTER"
                    elif 150 <= days <= 210:
                        basis = "YTD_6M"
                    elif 240 <= days <= 300:
                        basis = "YTD_9M"
                    elif 330 <= days <= 400 and meta["form"].startswith("10-K"):
                        basis = "ANNUAL"
                if not basis:
                    excluded["unsupported_form_period"] += 1
                    continue
                filed = date.fromisoformat(record["filed"])
                accepted = meta["accepted"]
                if (
                    (meta["filed"] is not None and filed != meta["filed"])
                    or (meta["filed"] is None and abs((filed - accepted.date()).days) > 1)
                    or filed < accepted.date() - timedelta(days=1)
                ):
                    raise ValueError("Statement filing date conflicts with accession metadata")
                publication = max(
                    accepted, datetime.combine(filed + timedelta(days=1), datetime.min.time(), UTC)
                )
                if publication + timedelta(hours=24) > asof:
                    excluded["future_or_processing_lag"] += 1
                    continue
                if type(record["val"]) not in (int, float):
                    raise ValueError("Statement amount must be numeric")
                if unit == "shares" and record["val"] < 0:
                    raise ValueError("Statement share counts must be nonnegative")
                fact = Fact(
                    security_id=security_id,
                    period_end=end,
                    accepted_at=accepted,
                    published_at=publication,
                    metric=metric,
                    value=record["val"],
                    unit=unit,
                    accession=accession,
                    amended=meta["form"].endswith("/A"),
                    source_id=f"sec-{int(cik)}-{accession}",
                    source_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{accession.replace('-', '')}/{meta['primary']}",
                )
                row = fact.model_dump(mode="json") | {
                    "period_start": str(start) if start else None,
                    "basis": basis,
                    "concept": concept,
                }
                key = (metric, basis, str(start), str(end), accession)
                if key in rows and rows[key]["value"] != row["value"]:
                    raise ValueError("Conflicting SEC statement aliases or duplicate amounts")
                # Same-value aliases retain a deterministic concept citation.
                if key not in rows:
                    rows[key] = row
                if len(rows) > 20_000:
                    raise ValueError("Statement normalized fact count exceeds bound")
    return {
        "policy": POLICY,
        "asof": asof.astimezone(UTC).isoformat(),
        "processing_lag_hours": 24,
        "security_id": security_id,
        "cik": str(int(cik)),
        "submissions_sha256": hashlib.sha256(submissions_raw).hexdigest(),
        "companyfacts_sha256": hashlib.sha256(facts_raw).hexdigest(),
        "facts": [row for _, row in sorted(rows.items())],
        "excluded_counts": excluded,
        "limitations": [
            "Current aggregate extraction is not proof of original extraction vintages",
            "Quarterly duration is 75–105 days; six/nine-month cumulative amounts stay separate",
            "No YTD subtraction, inferred fourth quarter, custom concepts or currency conversion",
            "Weighted diluted shares are period averages, not class shares or ownership dilution",
            "PPE cash payments are a narrow capex proxy; CFO minus PPE is not standardized FCF",
            "Computed ratios require exact periods, compatible units and the same accession",
            "Reported-cost margins are separate proxies, not replacements for missing GrossProfit",
            "Revenue/share uses aggregate period-average shares; class applicability is unknown",
            "Four-quarter sums require four directly reported contiguous quarters; no inferred Q4",
            "Working capital/current ratio describe reported balances, not solvency forecasts",
            "Debt components and parent equity are reported separately, never total debt estimates",
            "CIK entity evidence does not assign a permanent security or approve research inputs",
        ],
    }


def statement_analysis(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Latest knowable metrics, with exact-period alignment and conservative arithmetic."""
    contracts = {metric: (unit, instant) for metric, unit, instant in CONCEPTS.values()}
    return analyze(report, contracts, MAX_ANALYSIS_PERIODS)
