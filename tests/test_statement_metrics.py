"""Fictional exact-period financial calculations and unavailable-data boundaries."""

import copy
import json
from datetime import UTC, datetime

import pytest

from packages.data.sec_statements import normalize_statements, statement_analysis

ACC = "0000000001-25-000001"


def report(entries):
    submissions = {
        "cik": 1,
        "filings": {
            "recent": {
                "accessionNumber": [ACC],
                "acceptanceDateTime": ["2025-04-01T12:00:00Z"],
                "filingDate": ["2025-04-01"],
                "form": ["10-Q"],
                "primaryDocument": ["fictional.htm"],
            }
        },
    }
    company = {"cik": 1, "facts": {"us-gaap": {}}}
    for concept, value, start, end in entries:
        unit = "shares" if concept == "WeightedAverageNumberOfDilutedSharesOutstanding" else "USD"
        row = {"accn": ACC, "form": "10-Q", "filed": "2025-04-01", "end": end, "val": value}
        if start is not None:
            row["start"] = start
        company["facts"]["us-gaap"].setdefault(concept, {"units": {unit: []}})["units"][
            unit
        ].append(row)
    return normalize_statements(
        json.dumps(submissions).encode(),
        json.dumps(company).encode(),
        "fixture-entity",
        datetime(2025, 5, 1, tzinfo=UTC),
    )


def quarter(concept, value, year=2023, start="01-01", end="03-31"):
    return concept, value, f"{year}-{start}", f"{year}-{end}"


def test_explicit_concepts_ratios_and_citation_inputs_preserve_originals():
    source = report(
        [
            quarter("Revenues", 200),
            quarter("GrossProfit", 80),
            quarter("CostOfRevenue", 130),
            quarter("CostOfGoodsAndServicesSold", 110),
            quarter("ShareBasedCompensation", 12),
            quarter("WeightedAverageNumberOfDilutedSharesOutstanding", 50),
            quarter("NetCashProvidedByUsedInOperatingActivities", 40),
            quarter("PaymentsToAcquirePropertyPlantAndEquipment", 10),
            quarter("NetIncomeLoss", 15),
        ]
    )
    original = copy.deepcopy(source)
    row = statement_analysis(source)[0]
    expected = {
        "gross_margin": 0.4,
        "revenue_less_cost_margin": 0.35,
        "revenue_less_goods_services_cost_margin": 0.45,
        "stock_compensation_to_revenue": 0.06,
        "revenue_per_weighted_share": 4,
        "cfo_less_ppe": 30,
        "cfo_less_ppe_to_income": 2,
    }
    for name, value in expected.items():
        assert row["values"][name] == pytest.approx(value)
        assert row["derivations"][name]["status"] == "AVAILABLE"
        assert row["derivations"][name]["reason"] is None
    ids = {
        (f["metric"], f["basis"], f["period_start"], f["period_end"], f["accession"])
        for f in row["citations"]
    }
    assert all(tuple(i) in ids for d in row["derivations"].values() for i in d["input_ids"])
    assert source == original
    assert source["policy"] == "sec-statements-v2-period-metrics"
    assert row["analysis_policy"] == "statement-metrics-v2"


def test_cost_proxy_never_fills_reported_gross_profit_and_mixed_filings_stay_unavailable():
    source = report(
        [
            quarter("Revenues", 100),
            quarter("CostOfRevenue", 60),
            quarter("ShareBasedCompensation", -2),
        ]
    )
    row = statement_analysis(source)[0]
    assert row["values"]["gross_margin"] is None
    assert row["values"]["revenue_less_cost_margin"] == 0.4
    assert row["values"]["stock_compensation"] == -2
    assert row["values"]["stock_compensation_to_revenue"] == -0.02
    for f in source["facts"]:
        if f["metric"] != "revenue":
            f["accession"] = "0000000001-25-000002"
    row = statement_analysis(source)[0]
    for field in ("revenue_less_cost_margin", "stock_compensation_to_revenue"):
        assert row["values"][field] is None
        assert row["derivations"][field]["reason"] == "MIXED_FILINGS"


def test_margin_changes_are_fraction_differences_for_comparable_periods_only():
    source = report(
        [
            quarter("Revenues", 100, 2022),
            quarter("GrossProfit", 30, 2022),
            quarter("OperatingIncomeLoss", -10, 2022),
            quarter("Revenues", 200),
            quarter("GrossProfit", 80),
            quarter("OperatingIncomeLoss", 20),
        ]
    )
    row = statement_analysis(source)[0]
    assert row["values"]["gross_margin_yoy_change"] == pytest.approx(0.1)
    assert row["values"]["operating_margin_yoy_change"] == pytest.approx(0.2)
    # A second duration with the same end date makes the comparable period ambiguous.
    duplicate = copy.deepcopy(
        next(
            f
            for f in source["facts"]
            if f["metric"] == "revenue" and f["period_end"] == "2022-03-31"
        )
    )
    duplicate["period_start"] = "2022-01-02"
    source["facts"].append(duplicate)
    row = statement_analysis(source)[0]
    assert row["values"]["gross_margin_yoy_change"] is None
    assert row["values"]["revenue_yoy"] is None


@pytest.mark.parametrize("liabilities,ratio", [(50, 2), (0, None), (200, 0.5), (-1, None)])
def test_working_capital_signed_usd_change_and_positive_denominator(liabilities, ratio):
    source = report(
        [
            ("AssetsCurrent", 100, None, "2023-03-31"),
            ("LiabilitiesCurrent", liabilities, None, "2023-03-31"),
            ("AssetsCurrent", 20, None, "2022-03-31"),
            ("LiabilitiesCurrent", 30, None, "2022-03-31"),
        ]
    )
    row = statement_analysis(source)[0]
    assert row["values"]["current_ratio"] == ratio
    assert row["values"]["working_capital"] == (100 - liabilities if liabilities >= 0 else None)
    assert row["values"]["working_capital_yoy_change"] == (
        110 - liabilities if liabilities >= 0 else None
    )


def quarters():
    return [
        quarter("Revenues", value, year, start, end)
        for year, values in [(2022, [100, 100, 100, 100]), (2023, [110, 120, 130, 140])]
        for value, (start, end) in zip(
            values,
            [("01-01", "03-31"), ("04-01", "06-30"), ("07-01", "09-30"), ("10-01", "12-31")],
            strict=True,
        )
    ]


def test_direct_quarter_chains_trailing_growth_and_yoy_changes():
    source = report(quarters())
    row = statement_analysis(source)[0]
    for field, value in {
        "revenue_4q": 500,
        "revenue_4q_yoy": 0.25,
        "revenue_yoy_acceleration": 0.1,
        "revenue_yoy_change_2q": 0.2,
    }.items():
        assert row["values"][field] == pytest.approx(value)
    assert len(row["derivations"]["revenue_4q_yoy"]["input_ids"]) == 8
    source["facts"] = [f for f in source["facts"] if f["period_end"] != "2023-09-30"]
    row = statement_analysis(source)[0]
    assert row["values"]["revenue_4q"] is None
    assert row["values"]["revenue_yoy_acceleration"] is None


def test_ytd_never_substitutes_for_missing_quarter_and_period_gaps_stay_missing():
    entries = quarters()
    entries.remove(quarter("Revenues", 130, 2023, "07-01", "09-30"))
    entries.append(quarter("Revenues", 360, 2023, "01-01", "09-30"))
    rows = statement_analysis(report(entries))
    row = next(r for r in rows if r["basis"] == "QUARTER" and r["period_end"] == "2023-12-31")
    assert row["values"]["revenue_4q"] is None
    assert any(r["basis"] == "YTD_9M" for r in rows)


def test_overflowed_four_quarter_reference_never_becomes_false_negative_growth():
    entries = [
        (c, 1e308 if start.startswith("2022") else v, start, end) for c, v, start, end in quarters()
    ]
    row = statement_analysis(report(entries))[0]
    assert row["values"]["revenue_4q_yoy"] is None
    assert row["derivations"]["revenue_4q_yoy"]["reason"] == "NUMERIC_RANGE"


@pytest.mark.parametrize(
    "field,value",
    [
        ("unit", "shares"),
        ("security_id", "other"),
        ("basis", "ANNUAL"),
        ("value", True),
        ("accepted_at", "2025-05-01T00:00:00Z"),
    ],
)
def test_analysis_revalidates_typed_entity_period_and_availability(field, value):
    source = report([quarter("Revenues", 100)])
    source["facts"][0][field] = value
    with pytest.raises(ValueError):
        statement_analysis(source)


def test_incompatible_periods_and_nonpositive_references_do_not_mix():
    source = report(
        [
            quarter("Revenues", 200),
            quarter("WeightedAverageNumberOfDilutedSharesOutstanding", 0),
            quarter("NetCashProvidedByUsedInOperatingActivities", 40),
            quarter("PaymentsToAcquirePropertyPlantAndEquipment", 10),
            quarter("NetIncomeLoss", -5),
            quarter("GrossProfit", 80, start="01-02"),
        ]
    )
    row = next(r for r in statement_analysis(source) if r["period_start"] == "2023-01-01")
    assert row["values"]["gross_margin"] is None
    assert row["values"]["revenue_per_weighted_share"] is None
    assert row["values"]["cfo_less_ppe"] == 30
    assert row["values"]["cfo_less_ppe_to_income"] is None


def test_missing_liability_is_unavailable_without_crashing():
    row = statement_analysis(report([("AssetsCurrent", 100, None, "2023-03-31")]))[0]
    assert row["values"]["current_ratio"] is None
    assert row["derivations"]["working_capital"]["reason"] == "REQUIRED_METRIC_MISSING"
