"""Complete saved validation and adverse-outcome exports, without recomputing history."""

import json
import re
from typing import Any
from urllib.parse import urlsplit

from packages.research.reports import _clock
from packages.shared.numeric import require_finite

VERSION = "archived-validation-atlas-v1"


def _cell(value: Any) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, (list, tuple, dict)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _table(columns: list[str], rows: list[list[Any]]) -> list[str]:
    return [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
        *["| " + " | ".join(_cell(value) for value in row) + " |" for row in rows],
        *([] if rows else ["No archived observations; no rows invented."]),
        "",
    ]


def _header(run: dict[str, Any], title: str) -> list[str]:
    require_finite(run, "saved research report")
    _clock(run["asof"])
    if run["mode"] != "FIXTURE" or not re.fullmatch(r"[a-f0-9]{16}", run["run_id"]):
        raise ValueError("A source-bound fixture archive is required")
    lines = [
        f"# FIXTURE — {title}",
        "",
        f"Report {VERSION}; run {run['run_id']}; screening clock {run['asof']}.",
        "Rendered from saved fields only. Retrospective evaluation/outcome dates can "
        "extend beyond "
        "the screening clock; those results were not knowable predictors at that clock.",
        "Synthetic observations, inspected rules and a closed artificial universe provide no "
        "empirical alpha, probability, causal explanation or untouched-holdout evidence.",
        f"Model {_cell(run.get('model_version'))}; seed {_cell(run.get('seed'))}; "
        f"code SHA-256 {_cell(run.get('code_sha256'))}.",
        "",
        "## Source binding",
        "",
    ]
    sources = []
    for source in run.get("sources", []):
        digest, url = source.get("sha256"), source.get("url")
        if digest is not None and not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid archived source digest")
        if url:
            parsed = urlsplit(url)
            if (
                parsed.scheme not in ("https", "fixture")
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Private or unsupported archived source URL")
        sources.append(
            [
                source.get("source_id"),
                digest,
                url,
                source.get("coverage"),
                source.get("license_note"),
            ]
        )
    return lines + _table(["Source", "SHA-256", "URL", "Coverage", "License / scope"], sources)


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Invalid archived report object")
    return value


def _count(value: Any) -> str:
    if value is None:
        return "Unavailable"
    if not isinstance(value, list):
        raise ValueError("Invalid archived report observation list")
    return str(len(value))


def model_validation_report(run: dict[str, Any]) -> str:
    lines = _header(run, "saved model and portfolio validation")
    toy = _mapping(run.get("backtest"))
    validation = _mapping(run.get("validation"))
    portfolio = _mapping(run.get("portfolio"))
    partitions = _mapping(validation.get("partitions"))
    negative = _mapping(validation.get("negative_controls"))
    lines += [
        "## Evaluation periods, universe and execution",
        "",
        f"Legacy screening period: {_cell(toy.get('period_start'))} to "
        f"{_cell(toy.get('period_end'))}; {_count(toy.get('rows'))} saved windows.",
        f"Execution: {_cell(toy.get('execution'))}; round-trip cost "
        f"{_cell(toy.get('cost_round_trip_bps'))} bps. {_cell(toy.get('split'))}",
        f"Study anchor: {_cell(run.get('study', {}).get('anchor'))}; eligible closed-fixture "
        f"denominator {_cell(run.get('study', {}).get('denominator'))}. This is not a historical "
        "US-equities population or a current Finviz investable universe.",
        "The constrained policy below is separate from the legacy screening toy. "
        "Published/accepted "
        "filings plus processing lag govern dated inputs. No same-close signal/fill is implied.",
        "",
        "### Saved constrained policy",
        "",
        "```json",
        json.dumps(portfolio.get("policy"), indent=2, sort_keys=True, allow_nan=False),
        "```",
        "",
        f"Saved executions: {_count(portfolio.get('executions'))}; rejected selections: "
        f"{_count(portfolio.get('exclusions'))}. Participation, whole-share rounding and caps "
        "leave cash; no leverage, borrowing or broker orders are modeled.",
        "Cost assumptions are fixed proxies, not calibrated spread/impact or verified capacity. "
        "Unknown or untradable histories are not repaired with optimistic fills.",
        "",
        "## Chronology and holdout status",
        "",
        _cell(validation.get("holdout_status")),
        f"Partition status {_cell(partitions.get('status'))}; embargo "
        f"{_cell(partitions.get('embargo_days'))} calendar days. Date lists record the actual "
        "saved design; they do not establish an untouched experiment.",
        *_table(
            ["Partition", "Decision dates"],
            [[name, partitions.get(name)] for name in ("train", "validation", "holdout", "purged")],
        ),
        "## Legacy window comparators",
        "",
        "Return/ratio values below retain their saved units (fractional returns, not "
        "percentages). "
        "Sparse-window ratios and daily-close metrics use different sampling bases.",
        *_table(
            ["Comparator", "Windows", "Total return", "CAGR", "Drawdown", "Win rate", "Payoff"],
            [
                [
                    name,
                    *[
                        metrics.get(key)
                        for key in (
                            "windows",
                            "total_return",
                            "cagr",
                            "max_drawdown",
                            "win_rate",
                            "payoff_ratio",
                        )
                    ],
                ]
                for name, metrics in sorted(validation.get("metrics", {}).items())
            ],
        ),
        "## Saved constrained cost and turnover ledger",
        "",
        *_table(
            ["Decision", "Entry", "Exit", "Costs", "Turnover", "Deployment", "Entry cash"],
            [
                [
                    row.get(key)
                    for key in (
                        "decision",
                        "entry",
                        "exit",
                        "costs",
                        "turnover",
                        "deployment_fraction",
                        "entry_cash_fraction",
                    )
                ]
                for row in portfolio.get("rows", [])
            ],
        ),
        "## Saved legacy subgroups and illustrative uncertainty",
        "",
        "Subgroups below are archived descriptive security slices, not representative "
        "sector/regime/capitalization studies. Paired-window bootstrap intervals describe the "
        "saved legacy selector/equal-weight comparison, not portfolio CAGR "
        "or future hit probabilities.",
        "```json",
        json.dumps(
            {
                "subgroups": validation.get("subgroups"),
                "paired_window_bootstrap": validation.get("paired_window_bootstrap"),
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ),
        "```",
        "",
        "## Saved daily-close portfolio risk",
        "",
        "```json",
        json.dumps(portfolio.get("daily_risk"), indent=2, sort_keys=True, allow_nan=False),
        "```",
        "",
        "Daily-close drawdown misses intraday extrema. Annualization, zero risk-free assumptions, "
        "recovery/underwater status and sample sizes remain those recorded above.",
        "",
        "## Fixed-budget 5x/10x classification",
        "",
    ]
    classification = validation.get("classification")
    if classification is None:
        lines.append("Unavailable in this archive; no classification is recomputed.")
    else:
        lines += [
            f"Policy {_cell(classification.get('policy'))}; "
            f"{_count(classification.get('attempts'))} retained attempts. "
            "Missing outcomes remain unknown and infeasible budgets are not reduced.",
            *_table(
                [
                    "Family",
                    "Years",
                    "Multiple",
                    "Evaluated dates",
                    "Population",
                    "Missing",
                    "Precision",
                    "Recall",
                    "Base",
                    "Lift",
                ],
                [
                    [
                        row.get("family"),
                        row.get("horizon_years"),
                        row.get("threshold"),
                        row.get("evaluated_anchors"),
                        *[
                            row.get("metrics", {}).get(key)
                            for key in (
                                "population",
                                "unlabeled",
                                "precision_at_budget",
                                "recall",
                                "base_rate",
                                "lift",
                            )
                        ],
                    ]
                    for row in classification.get("summaries", [])
                ],
            ),
            "Ranks are not probabilities: calibration/Brier/reliability are unavailable. "
            "Missingness bounds are not confidence intervals; inspect classification.json for "
            "every unavailable interval and anchor reason. No best family is selected.",
        ]
    attempts = _mapping(validation.get("robustness")).get("attempts", [])
    lines += [
        "",
        "## Robustness and negative controls",
        "",
        *_table(
            ["Retained stress", "Status", "Reason"],
            [[row.get("id"), row.get("status"), row.get("reason")] for row in attempts],
        ),
        "Contributor exclusions are post-hoc diagnostics, not prospective selections. "
        "All attempts and source/policy bindings remain in robustness.json, including rejected "
        "or unavailable results. Frozen factor ablations remain in discovery_sensitivity.json.",
        f"Date-local negative controls: {_cell(negative.get('status'))}; "
        f"{_cell(negative.get('windows'))} testable windows. "
        "See negative_controls.json and discovery_negative_controls.json for full pools, null "
        "ranges and exclusions; descriptive checks are not p-values or multiple-testing "
        "correction.",
        "",
        "## Missing evidence and limitations",
        "",
        *[f"- {_cell(item)}" for item in run.get("limitations", [])],
        *[f"- {_cell(item)}" for item in portfolio.get("limitations", [])],
        "- Representative small/microcap total-return histories, original provider vintages and "
        "a genuinely untouched real holdout are not established by these fixture outputs.",
        "- Zero verified real investment theses; no recommendation follows from this report.",
    ]
    return "\n".join(lines) + "\n"


def failed_lookalikes_report(run: dict[str, Any]) -> str:
    lines = _header(run, "failed-lookalike and adverse-outcome atlas")
    study = _mapping(run.get("study"))
    cohorts = study.get("cohorts")
    raw_labels = cohorts.get("labels") if isinstance(cohorts, dict) else study.get("labels")
    _count(raw_labels)
    labels = raw_labels if raw_labels is not None else []
    failures = [
        row
        for row in labels
        if row.get("terminal_total_return") is not None and row["terminal_total_return"] <= 0
    ]
    missing = sum(row.get("terminal_total_return") is None for row in labels)
    lines += [
        "## Scope and denominators",
        "",
        f"{_count(raw_labels)} archived security/anchor/horizon observations, including "
        f"{missing if raw_labels is not None else 'Unavailable'} missing "
        f"terminal outcomes; {len(failures) if raw_labels is not None else 'Unavailable'} "
        "recorded nonpositive terminal outcomes. "
        "Overlapping horizons and repeated securities are correlated, not independent firms.",
        "An adverse terminal holding return differs from failing a maximum-hit threshold. "
        "A path may reach 5x/10x and later lose money; both values remain visible. Missing "
        "outcomes "
        "stay in coverage counts and never become losses, successes or zero proceeds.",
        "",
        *_table(
            [
                "Permanent ID",
                "Anchor",
                "Years",
                "Sector proxy",
                "Maximum multiple",
                "Terminal return",
                "Drawdown",
                "Delisted",
                "Coverage",
            ],
            [
                [
                    row.get(key)
                    for key in (
                        "security_id",
                        "anchor",
                        "horizon_years",
                        "sector",
                        "max_multiple",
                        "terminal_total_return",
                        "max_drawdown",
                        "delisted",
                        "coverage_flag",
                    )
                ]
                for row in failures
            ],
        ),
        "## Missing terminal outcomes retained for audit",
        "",
        *_table(
            ["Permanent ID", "Anchor", "Years", "Coverage"],
            [
                [
                    row.get(key)
                    for key in ("security_id", "anchor", "horizon_years", "coverage_flag")
                ]
                for row in labels
                if row.get("terminal_total_return") is None
            ],
        ),
        "## Recorded case/control assignments",
        "",
        "These are the saved retrospective assignments, not a fresh selection of attractive "
        "examples. Matching strata are fixture proxies; weights are sampling weights, not "
        "hit probabilities.",
        *_table(
            [
                "Anchor",
                "Case",
                "Control",
                "Years",
                "Hit threshold",
                "Strata",
                "Seed",
                "Control probability",
                "Control weight",
            ],
            [
                [
                    pair.get(key)
                    for key in (
                        "anchor",
                        "case_security_id",
                        "control_security_id",
                        "horizon_years",
                        "max_hit_threshold",
                        "strata",
                        "matching_seed",
                        "control_sampling_probability",
                        "control_weight",
                    )
                ]
                for pair in study.get("pairs", [])
            ],
        ),
        "## What was knowable / what remains unexplained",
        "",
        f"Anchor inputs: historical_cases.md at {_cell(study.get('anchor'))}; "
        "current profiles are not substituted for missing historical snapshots. Full retained "
        "cohort values and missingness are in cohort_grid.json.",
        "No causal explanation of why a control diverged is inferred from an outcome label. "
        "Industry evolution, financing, competition and catalysts require dated "
        "independent evidence. "
        "The artificial construction is itself an alternative explanation for these paths.",
        "Maximum multiples and holding returns follow the saved raw-price/split/cash-dividend/"
        "delist-wealth methodology. Known zero proceeds are preserved; unknown proceeds "
        "are not assumed zero.",
        "",
        "## Limitations",
        "",
        *[f"- {_cell(item)}" for item in run.get("limitations", [])],
        "- Hindsight atlas only: no predictor input, empirical base rate or verified "
        "investment thesis.",
    ]
    return "\n".join(lines) + "\n"
