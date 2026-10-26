"""Source-attributed fixture reports. Missing evidence is never filled with an invented thesis."""

from typing import Any


def candidate_memo(run: dict[str, Any], security_id: str) -> str:
    candidate = next((f for f in run["signals"] if f["security_id"] == security_id), None)
    if candidate is None:
        raise ValueError("No candidate in this run")
    evidence = "\n".join(
        f"- {f['metric']} {f['value']} {f['unit']}; period {f['period_end']}; "
        f"first public {f['published_at']}; accession {f['accession']}; source {f['source_id']}"
        for f in candidate["evidence"]
    )
    return (
        f"# FIXTURE RESEARCH DOSSIER — {candidate['ticker']}\n\n"
        f"Permanent ID {security_id}; run {run['run_id']}; as-of {run['asof']}.\n\n"
        "All observations are synthetic. This is not a verified investment thesis.\n\n"
        f"## Setup\nStage {candidate['stage']}: {candidate.get('stage_reason', 'Legacy rule')}. "
        f"Unvalidated score {candidate['score']}/100; coverage {candidate['completeness']:.0%}.\n\n"
        f"## Dated evidence\n{evidence or 'No known filings.'}\n\n"
        "## Bull/base/bear assumptions\nNot supplied. Use Thesis Studio to enter operating-growth, "
        "margin, dilution, multiple and debt assumptions; no probabilities are assigned.\n\n"
        "## Catalyst calendar\nNo independently verified future catalysts. Add citations and dates "
        "as explicit draft assertions in Thesis Studio.\n\n"
        "## Falsification / monitoring\nMonitor revenue growth, relative strength, liquidity and "
        "setup failure. Thresholds require explicit research judgment.\n\n"
        "## Bear argument\nThe fixture deliberately encodes artificial paths. Apparent momentum "
        "and filing relationships provide no investment evidence. "
        "Independent critique not supplied.\n\n"
        "## Risks / alternatives\nMissing historical universe/delist evidence, incomplete factors, "
        "dilution and financing uncertainty, competition, capacity and selection bias.\n\n"
        "## Decision\nResearch demonstration. No recommendation, identity promotion or order.\n"
    )


def case_report(run: dict[str, Any]) -> str:
    lines = [
        "# FIXTURE historical case/control report",
        "",
        f"Run {run['run_id']}; anchor {run['study']['anchor']}; "
        f"eligible denominator {run['study']['denominator']}.",
        "Retrospective sampling does not estimate population hit probability. Hindsight outcomes "
        "below are isolated from dated predictors.",
        "",
    ]
    for pair in run["study"]["pairs"]:
        lines.extend(
            [
                f"## {pair['case_security_id']} vs {pair['control_security_id']}",
                f"Control sampling weight {pair['control_weight']}; seed {pair['matching_seed']}.",
                "",
            ]
        )
        for sid in (pair["case_security_id"], pair["control_security_id"]):
            for label in run["study"]["labels"]:
                if label["security_id"] == sid:
                    lines.append(
                        f"- {sid} {label['horizon_years']}Y: maximum {label['max_multiple']}; "
                        f"terminal return {label['terminal_total_return']}; "
                        f"drawdown {label['max_drawdown']}; {label['coverage_flag']}"
                    )
    lines.extend(
        [
            "",
            "Missing horizons remain missing. Maximum-hit multiples are not holding returns.",
            "The fictional failed peer includes explicit zero-proceeds delisting. "
            "No real historical case study or empirical conclusion is claimed.",
        ]
    )
    return "\n".join(lines) + "\n"


def discovery_digest(run: dict[str, Any]) -> str:
    lines = [
        "# FIXTURE discovery digest",
        "",
        f"Run {run['run_id']}; historical clock {run['asof']}.",
        "Not a live market digest or investment recommendation.",
        "",
    ]
    for f in run["signals"]:
        history = f.get("stage_history", [])
        changes = [r for r in history if r["stage"] != r["previous_stage"]]
        lines.append(
            f"- {f['ticker']} ({f['security_id']}): {f['stage']}; score {f['score']}; "
            f"coverage {f['completeness']:.0%}; {len(changes)} stage transitions in saved window."
        )
    lines.extend(["", "## Missing evidence", *[f"- {v}" for v in run["limitations"]]])
    return "\n".join(lines) + "\n"
