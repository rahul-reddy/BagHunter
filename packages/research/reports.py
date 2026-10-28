"""Source-attributed fixture reports. Missing evidence is never filled with an invented thesis."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from packages.shared.numeric import require_finite

REPORT_POLICY = "source-bound-reports-v2"


def _clock(value: str) -> datetime:
    clock = datetime.fromisoformat(value)
    if clock.utcoffset() is None:
        raise ValueError("Report clocks must include a timezone")
    return clock.astimezone(UTC)


def _evidence_lines(feature: dict[str, Any], asof: str) -> list[str]:
    """Do not turn a legacy missing clock or a later filing into knowable report evidence."""
    cutoff = _clock(asof)
    lag = feature.get("processing_lag_hours", 24)
    if type(lag) is not int or not 24 <= lag <= 720:
        raise ValueError("Invalid report processing lag")
    lines = []
    for fact in feature.get("evidence", []):
        require_finite(fact, "report filing evidence")
        url = fact.get("source_url")
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
                raise ValueError("Report citation must be a public source reference")
        source = f"[{fact['source_id']}]({url})" if url else "Source link unavailable"
        if not fact.get("accepted_at") or not fact.get("published_at"):
            lines.append(f"- {fact['metric']}: unavailable; legacy filing clocks missing. {source}")
            continue
        usable = max(_clock(fact["accepted_at"]), _clock(fact["published_at"])) + timedelta(
            hours=lag
        )
        if usable > cutoff:
            raise ValueError("Report contains filing evidence unavailable at its clock")
        lines.append(
            f"- {fact['metric']}: {fact['value']} {fact['unit']}; period {fact['period_end']}; "
            f"accepted {fact['accepted_at']}; published {fact['published_at']}; "
            f"usable after {usable.isoformat()} ({lag}h processing lag); "
            f"accession {fact['accession']}; source {source}"
        )
    return lines


def stage_history_report(run: dict[str, Any]) -> dict[str, Any]:
    discovery = run.get("discovery", {})
    histories = discovery.get("history")
    return {
        "run_id": run["run_id"],
        "asof": run.get("asof"),
        "policy": discovery.get("policy"),
        "history_scope": discovery.get("history_scope", "LEGACY_ARCHIVED_WINDOW"),
        "histories": histories
        if histories is not None
        else {s["security_id"]: s.get("stage_history", []) for s in run["signals"]},
    }


def candidate_memo(run: dict[str, Any], security_id: str) -> str:
    candidate = next((f for f in run["signals"] if f["security_id"] == security_id), None)
    if candidate is None:
        raise ValueError("No candidate in this run")
    evidence = "\n".join(_evidence_lines(candidate, run["asof"]))
    return (
        f"# FIXTURE RESEARCH DOSSIER — {candidate['ticker']}\n\n"
        f"Permanent ID {security_id}; run {run['run_id']}; as-of {run['asof']}.\n\n"
        f"Report format {REPORT_POLICY}; rendered from archived fields.\n\n"
        "Freshness: frozen historical snapshot, not a live quote; "
        "reading-time age is not supplied.\n\n"
        f"Model {run.get('model_version', 'Unavailable in archive')}; "
        "raw-price/action basis and source coverage remain those of the archived run.\n\n"
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
    anchor_clock = _clock(run["study"]["anchor"])
    screen_clock = _clock(run["asof"])
    lines = [
        "# FIXTURE historical case/control report",
        f"Report format {REPORT_POLICY}; rendered from archived fields.",
        "",
        f"Run {run['run_id']}; anchor {run['study']['anchor']}; "
        f"eligible denominator {run['study']['denominator']}.",
        "Retrospective sampling does not estimate population hit probability. Hindsight outcomes "
        "below are isolated from dated predictors. Return basis is split/dividend/delist cash-flow "
        "wealth; maximum-hit multiples are separate from terminal holding returns.",
        "",
    ]
    if anchor_clock > screen_clock:
        lines.append("Study anchor is later than the screening clock: retrospective study only.")
    for pair in run["study"]["pairs"]:
        lines.extend(
            [
                f"## {pair['case_security_id']} vs {pair['control_security_id']}",
                f"Control sampling weight {pair['control_weight']}; seed {pair['matching_seed']}.",
                "",
            ]
        )
        for sid in (pair["case_security_id"], pair["control_security_id"]):
            feature = next(
                (f for f in run["study"].get("anchor_features", []) if f["security_id"] == sid),
                None,
            )
            lines.extend([f"### {sid}: knowable anchor inputs", ""])
            if feature is None:
                lines.append(
                    "Independent anchor snapshot unavailable; no current profile substituted."
                )
            else:
                if _clock(feature["asof_time"]) != _clock(run["study"]["anchor"]):
                    raise ValueError("Historical report anchor binding mismatch")
                lines.append(f"Snapshot {feature['asof_time']}; raw-price diagnostic basis.")
                for field in (
                    "close",
                    "return_21d",
                    "relative_strength_63d",
                    "dollar_volume_20d",
                    "base_high_60d",
                    "base_width_60d",
                    "revenue_growth",
                    "operating_margin",
                ):
                    value = feature.get(field)
                    require_finite(value, "report anchor feature")
                    lines.append(f"- {field}: {value if value is not None else 'Unavailable'}")
                lines.extend(_evidence_lines(feature, run["study"]["anchor"]))
            lines.extend(["", "### Later hindsight outcomes — not anchor predictors", ""])
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
                f"Matching strata {pair.get('strata', 'Unavailable')}; "
                f"sampling probability {pair.get('control_sampling_probability', 'Unavailable')}.",
                "Sector matching is an explicit industry proxy. Different later paths do not "
                "establish a causal business explanation; no sourced customer/contract/catalyst "
                "history is supplied for these fictional companies.",
            ]
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


def discovery_digest(run: dict[str, Any], previous: dict[str, Any] | None = None) -> str:
    _clock(run["asof"])
    lines = [
        "# FIXTURE discovery digest",
        f"Report format {REPORT_POLICY}; rendered from archived fields.",
        "",
        f"Run {run['run_id']}; historical clock {run['asof']}.",
        "Not a live market digest or investment recommendation.",
        "",
    ]
    if previous is None:
        lines.append(
            "No prior run selected: no weekly interval or changes-since-last-run inferred."
        )
    else:
        if previous.get("mode") != run.get("mode") or _clock(previous["asof"]) >= _clock(
            run["asof"]
        ):
            raise ValueError("Digest requires an earlier run in the same source mode")
        lines.extend(
            [
                f"## Changes since run {previous['run_id']}",
                f"Explicit archived interval {previous['asof']} → {run['asof']}; "
                "no weekly cadence or live-market coverage inferred.",
            ]
        )
        if any(
            not archived.get("code_sha256")
            or not archived.get("model_version")
            or not archived.get("discovery", {}).get("policy_sha256")
            or not archived.get("sources")
            or any(not source.get("sha256") for source in archived.get("sources", []))
            for archived in (previous, run)
        ):
            lines.append(
                "Code/policy/source metadata is incomplete: comparability is unknown, "
                "not assumed to be the same."
            )
        if (
            previous.get("code_sha256") != run.get("code_sha256")
            or previous.get("model_version") != run.get("model_version")
            or previous.get("discovery", {}).get("policy_sha256")
            != run.get("discovery", {}).get("policy_sha256")
            or previous.get("sources") != run.get("sources")
        ):
            lines.append(
                "Code, policy or source changed: differences are not isolated market moves."
            )
        before = {f["security_id"]: f for f in previous["signals"]}
        after = {f["security_id"]: f for f in run["signals"]}
        for feature in before.values():
            _evidence_lines(feature, previous["asof"])
        for feature in after.values():
            _evidence_lines(feature, run["asof"])
        old_accessions = {
            (sid, fact["accession"])
            for sid, feature in before.items()
            for fact in feature.get("evidence", [])
        }
        newly_usable = set()
        for sid, feature in after.items():
            for fact in feature.get("evidence", []):
                if not fact.get("accepted_at") or not fact.get("published_at"):
                    continue
                known = max(_clock(fact["accepted_at"]), _clock(fact["published_at"])) + timedelta(
                    hours=feature.get("processing_lag_hours", 24)
                )
                if _clock(previous["asof"]) < known <= _clock(run["asof"]):
                    newly_usable.add((sid, fact["accession"]))
        lines.extend(["", "### Newly usable filing accessions in the retained queue"])
        lines.extend(f"- {sid}: {accession}" for sid, accession in sorted(newly_usable))
        if not newly_usable:
            lines.append("None in retained filing inputs; not an all-market filings census.")
        new_older = (
            {
                (sid, fact["accession"])
                for sid, feature in after.items()
                for fact in feature.get("evidence", [])
            }
            - old_accessions
            - newly_usable
        )
        if new_older:
            lines.append(
                "Newly represented older/undated accessions are not called fresh filings: "
                + ", ".join(f"{sid}/{accession}" for sid, accession in sorted(new_older))
            )
        lines.extend(["", "### Sector-proxy theme counts in the selected research queue"])
        old_themes = Counter(
            f.get("sector") or "Sector unavailable"
            for f in before.values()
            if f.get("stage") in ("EMERGING", "CONFIRMED")
        )
        new_themes = Counter(
            f.get("sector") or "Sector unavailable"
            for f in after.values()
            if f.get("stage") in ("EMERGING", "CONFIRMED")
        )
        for sector in sorted(old_themes.keys() | new_themes.keys()):
            lines.append(
                f"- {sector}: emerging/confirmed count "
                f"{old_themes[sector]} → {new_themes[sector]}; "
                "not an industry-wide breadth estimate."
            )
        lines.extend(["", "### Queue membership and stage changes"])
        for sid in sorted(before.keys() | after.keys()):
            old, new = before.get(sid), after.get(sid)
            if old is None:
                lines.append(f"- {sid}: added to the research queue.")
            elif new is None:
                lines.append(
                    f"- {sid}: absent from current queue; not assumed delisted or worthless."
                )
            elif old.get("stage") != new.get("stage"):
                lines.append(
                    f"- {sid}: {old.get('stage')} → {new.get('stage')}; "
                    f"{new.get('stage_reason', 'Reason unavailable in archive')}"
                )
        lines.append(
            "Personal browser watchlists and independently verified thesis breakers "
            "are not supplied."
        )
    for f in run["signals"]:
        history = f.get("stage_history", [])
        changes = [r for r in history if r["stage"] != r["previous_stage"]]
        lines.append(
            f"- {f['ticker']} ({f['security_id']}): {f['stage']}; score {f['score']}; "
            f"coverage {f['completeness']:.0%}; {len(changes)} transitions in retained history."
        )
        if f.get("stage") == "INVALIDATED":
            lines.append(f"  Setup invalidation: {f.get('stage_reason', 'Reason unavailable')}.")
        if f.get("completeness", 0) < 1:
            lines.append("  Data-quality alert: incomplete factor coverage; missing is not zero.")
        lines.extend(_evidence_lines(f, run["asof"]))
    lines.extend(["", "## Missing evidence", *[f"- {v}" for v in run["limitations"]]])
    return "\n".join(lines) + "\n"
