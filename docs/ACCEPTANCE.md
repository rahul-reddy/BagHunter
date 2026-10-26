# Full specification acceptance and known issues

Area-level PASS labels below are bounded software assessments, not full-spec completion proof.
See [remaining requirements](REMAINING_REQUIREMENTS.md) for concrete unfinished software and
[company research](COMPANY_RESEARCH.md) for the current source-bound workflow and pending gates.

This matrix separates executable software from empirical research. The complete goal is not
satisfied by opening nine pages or passing fixture tests. Commands and current counts are recorded
in STATUS.md; exact-head CI, independent model review and guarded merges are recorded in each PR.
The original numbered specifications remain authoritative.

| Requirement family | Status | Concrete implementation / remaining evidence |
| --- | --- | --- |
| Local installation, CLI, API, responsive terminal | PASS software | Locked installs, demo publication, read-only API, nine views; scripts/qa.ps1 and browser accessibility/mobile checks |
| Immutable ingestion, lineage, identity intervals, PIT lag/amendments | PASS fixture/staging scope | Validated records/Parquet, SHA archives, cutoff/revision/action/integrity/tampering tests; external identities remain unverified |
| Replaceable historical adapter | PASS quarantined import | Provider-neutral local bundle audit/ingest; explicit entitlement/action/coverage flags; never silently activates research |
| Finviz available-provider workflow | PASS software; real fields unverified | Supported manual overview refresh, immutable importer, saved source selection/search/pagination, reported-field filters and snapshot-bound drafts/dossiers |
| SEC fundamental normalization | PASS bounded real-source path | Private contact/.env alias, submissions/companyfacts sync, exact accession/official filing-day publication upper bound, annual USD facts, revisions/lag, bounded historical accession parts, cited descriptive financial profile, direct quarterly/YTD/instant statements with EPS/shares/PPE evidence, source-verified Data Quality browser; quarantined output |
| Historical archaeology and controls | PASS fixture mechanics | Multi-anchor/horizon/threshold/sector cohorts, failures/delist denominators, matched controls and case exports |
| Discovery, dated history and explainability | PASS software | Six stages, configurable weights/thresholds, technical/available financial diagnostics, missingness, watchlists and source-attributed profiles |
| Refresh/reproducibility | PASS software | Code/data/as-of/seed/policy-bound runs, cache integrity verification, run comparison, manual refresh templates and recovery guide |
| Constrained portfolio and risk | PASS fixture mechanics | Whole shares/cash, costs, position/sector/participation caps, actions/delists, daily close marks and risk, independent comparators, filtered execution ledger |
| Validation design and diagnostics | PASS descriptive software | Chronological purge/embargo, window metrics, daily risk assumptions, cost sensitivity, paired illustrative bootstrap, explicit dated-factor weight/liquidity variants |
| Thesis and committee workspace | PASS assumption/draft software | Bear/base/bull arithmetic, dilution/debt, source questions, falsification/bear text, catalyst calendar, review dates and source-bound exports |
| Reports, source manifest, limitations and model card | PASS software | Downloadable JSON/CSV/Markdown, dossiers, policies, comparison/sensitivity exports; MODEL_CARD.md documents formulas/scope |
| Large real PIT universe and empirical archaeology | BLOCKED | Finviz Elite is the sole provider; archived membership, actions/delist proceeds and historical export semantics are not yet established; continue verifying supported Finviz contracts |
| Real contemporaneous facts, common-share identities and field units | BLOCKED | Original filing vintages, independent security/class assignments, reported scale/currency and source-time continuity remain unresolved |
| Multi-decade/regime, small/microcap benchmarks, capacity and calibrated impact | BLOCKED | Representative real histories/benchmarks and execution evidence unavailable; fixture subgroups do not satisfy these requirements |
| Frozen negative-control mechanics | Implemented; current revision gates in STATUS.md | Matured outcomes only, same-date label permutations, predated irrelevant rank with prior-known IDs, complete pools, deterministic reports/UI; no p-value or predictive claim |
| Empirical calibration, negative-control study and untouched holdout | BLOCKED | No representative real labeled sample or untouched period; fixed fixture has been inspected, no fitted probability model or empirical claim |
| 3–5 evidence-backed theses and independent factual bear critique | BLOCKED | Zero real verified theses; operator notes/scenarios and independent code review do not establish factual investment evidence |
| Source-only release packaging | Required after final merge | git archive from reviewed main; install via README; exclude local credentials/licensed archives and generated dependencies |
| Public deployment | NOT REQUESTED | Manual owner-confirmed deployment only, from main; no target configured |

## Known issues and deliberate limits

- Unreported-quarter reconstruction, custom taxonomy interpretation, original-vintage certification and histories beyond the bounded declared-parts
  import are unsupported. They require source contracts and
  boundary fixtures; annual aggregate facts must not be backdated into historical research.
- Current Finviz exports are not an archived investable universe. No ticker/name agreement or
  mapping-candidate result opens the common-share/PIT gates. Unknown cap units are not converted.
- Fixture regimes, sectors and artificial return paths cannot estimate real base rates or market
  performance. Rank sensitivity is arithmetic, not a robustness study. No best variant is selected.
- Daily-close risk misses intraday losses; fixed costs do not model actual spread/impact. Cash earns
  zero. The weekday fixture calendar omits exchange holidays. These assumptions accompany exports.
- Browser drafts/watchlists are local to the browser. Export them for backup. Saved observation
  drafts deliberately remain separate between snapshots until a researcher reconciles them.
- Windows skips seven symlink cases; Linux CI runs them. Current framework deprecation/support
  notices remain visible in logs and do not substitute for failed tests.

For empirical acceptance, first establish the documented real-data gates for a bounded sample and
replay the existing cutoff/action/cohort/validation pipeline. Do not purchase data, force a pick
count, infer absent observations or rerun an inspected fixture as an untouched holdout.
