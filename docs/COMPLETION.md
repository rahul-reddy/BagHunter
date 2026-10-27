# BagHunter implementation completion audit

Dated technical catalog continuation: see [TECHNICAL_FEATURES.md](TECHNICAL_FEATURES.md) for
formulas, reference clocks, sector-proxy scope and missingness. Added diagnostics retain the
existing unvalidated score/stage policy; current final gates are recorded in STATUS.md.

The granular open-work register is [REMAINING_REQUIREMENTS.md](REMAINING_REQUIREMENTS.md).
Current company-research work connects Finviz notes to explicitly selected SEC evidence,
assumption scenarios and cited saved/exported drafts. This does not approve identities or certify
investment theses; final gates are tracked in STATUS.md and COMPANY_RESEARCH.md.

Arithmetic/validation continuation: finite-input ratio overflow now retains explicit missing
factors or rejects unrepresentable calculations before ranking/publication. Configured six-factor
and momentum ranks have distinct mature-only negative-control reports with dated pools, policy
fingerprints, within-date permutations and prior-known-identity irrelevant ranks. UI downloads,
legacy states and mobile keyboard scrolling are implemented. Final revision gates are in STATUS.md;
these fixture diagnostics do not establish empirical calibration or complete the overall goal.

SEC statement continuation: separate verified-source quarterly, annual, cumulative and instant
reports now provide EPS, weighted diluted shares, YoY changes, balance-sheet evidence and narrow
CFO-less-PPE arithmetic. Periods/units/citations and missingness stay explicit; original bundles
remain unchanged. Source and arithmetic boundaries are documented in SEC_STATEMENTS.md.
Current-revision QA, CI and independent review are tracked in STATUS.md; full goal remains active.

Owner correction, 2026-10-26: finish the application against the complete specification.
The prior single-candidate evidence milestone did not satisfy that goal. The active goal remains
open across individual PRs. Data entitlements block empirical claims, not software implementation.

| Specification | Starting implementation | Required completion work |
| --- | --- | --- |
| Command Center | Three fixture counts and queue | Regime/breadth, stage counts, refresh changes, saved watchlist |
| Radar | Search, stage and two sorts | Sector/liquidity/coverage/technical filters, configurable rules, exports |
| Candidate DNA | Raw chart, score, revenue filings | Relative strength, bases, stage timeline, risk and catalyst monitoring |
| Museum | One fixture pair and horizon table | Cohort filters, outcome thresholds, case/control diagnostics and exports |
| Discovery | WATCH/IGNITION/EXTENDED | All six stages, policy version/config, dated history and run differences |
| Thesis Studio | Missing | Editable assumption scenarios, dilution/debt sensitivity, evidence/catalyst/falsification workspace, memo export |
| Validation | Fixed 13-window toy | Chronological partitions, purge/embargo, metrics, sensitivity, constraints and honest sample status |
| Data Quality | Fixture source ledger | Provider/import state, explicit acceptance gates and report access |
| Settings | Missing | Persistent local preferences, thresholds, watchlist, provider state and safe CLI job instructions |
| Runs/refresh | CURRENT only | Read-only archive browsing, comparisons, cache/recovery and refresh commands |
| Reports | Two CSVs, fixed prose | Downloadable case/cohort/watchlist/validation/thesis/source/limitations reports |
| SEC fundamentals | Raw submissions only | Accession-bound normalized filing adapter, publication/amendment/lag tests |
| Historical adapter | Quarantined local exports | Keep entitlement gates; implement reusable research workflow without silent activation |
| Operations/release | Local MVP QA | Full feature browser coverage, reproducibility/load checks, packaging/runbook, final requirement matrix |

Evidence standard: an implemented feature requires working code and acceptance tests. A page title,
placeholder, or description of missing data is not an implementation. A tested fixture workflow is
software acceptance, never empirical validation. Independent review/CI must cover the final head.

## Current implementation assessment

The starting gaps above are retained as the audit baseline. This branch implements the following
software workflows; full final-runtime checks and PR review are still required:

| Area | Implemented capability | Remaining acceptance / external boundary |
| --- | --- | --- |
| Product views | Nine functional views, responsive filters and saved watchlist | Final browser/accessibility run |
| Discovery | Six stages, frozen policy, dated transitions, relative strength/breadth, technical and financial diagnostics | Unvalidated rules; no empirical score calibration |
| Museum | Multi-anchor/sector cohorts, horizon/threshold filters, failed controls and exports | Artificial universe only; real PIT membership/delists unavailable |
| Thesis Studio | Editable scenarios, dilution/debt, source/falsification/bear draft, dated multi-event catalyst calendar, save/load/export | No verified live theses or independent factual critique without real evidence |
| Validation | Chronological purge/embargo, metrics/sensitivity/bootstrap, daily marked equity/risk, cash/caps/participation/cost/action simulation and multiple baselines | Inspected fixture is not untouched holdout; no intraday-risk or calibrated market-impact claim |
| Settings | Persistent display preferences, exportable discovery/portfolio policies, provider/recovery controls | Read-only API means refresh is an explicit CLI action |
| Sources | Browser-selectable Finviz/reference archives, source binding and failure clearing | Identities, units, currency and current-to-historical continuity remain unverified |
| SEC | Local accession-bound annual fact parser, amendment/lag/unit/conflict checks | Original extraction vintages, quarters/custom tags and identity verification remain unsupported |
| Runs/operations | Saved-run inspection/comparison, integrity manifests/cache reuse, UTF-8 reports, refresh templates | No automatic scheduler, subscriptions, broker or deployment |

Do not equate this assessment with full goal completion. After review/merge, reassess the original
specifications and keep any independent software gaps in the active queue. Empirical gates stay
BLOCKED until their actual evidence exists; a polished fixture app does not open them.

Daily mark-to-market portfolio risk and the structured multi-event catalyst calendar passed
Linux CI (254 backend / 13 browser), independent Gemini review and guarded merge as PR #25.
Source-bound Finviz research drafts/dossiers and complete-archive reported-field filters passed
Linux CI (256 backend / 14 browser), independent Gemini review and guarded merge as PR #26.
Dated-factor weight/liquidity sensitivity, reusable policy downloads, a model card and complete
acceptance/known-issues matrix are now implemented in feat/policy-sensitivity. Full local QA passed on
the combined PR #26 base: 254 backend / 15 browser tests with five Windows symlink skips;
exact-head CI/review remain required.
See ACCEPTANCE.md and MODEL_CARD.md for the requirement-by-requirement limits. Final delivery
packages reviewed main without local data or credentials. Finviz Elite is the only available
provider (owner confirmation). The full empirical goal is not declared complete.

Externally blocked acceptance: licensed historical PIT membership/bars/actions/delist coverage;
verified real security identities, field units/currencies, original filing vintages and enough
observations for independent empirical validation. Zero real verified investment theses. Do not
close the full goal merely because these gates are documented; complete all independent software
work first and report the remaining requirements individually.

## Finviz/SEC continuation — 2026-10-26

Owner confirms Finviz is enough and added SEC contact in .env. PR #27 is merged as d0210e1
(259 backend / 15 browser in Linux CI, independent Gemini approval). Current provider-refresh
work reads the supplied alias safely, refreshes the supported Finviz CSV, synchronizes real SEC
raw pairs and exposes source-verified filing evidence in Data Quality. Real execution produced
11,772 fresh Finviz rows and 102 annual SEC facts; full QA/CI/review remain separate gates.
Do not turn unestablished historical semantics into a request for another subscription by default.
Use the available Finviz/SEC stack and finish independent software against verified contracts.
Publication timing now covers after-hours/weekend filing dates conservatively; original extraction
vintages and security/class identities still need their own evidence. See PROVIDER_REFRESH.md.


SEC history continuation (feat/sec-history): bounded declared older submissions parts recover 165
annual facts for the existing filer, with zero missing-accession fact exclusions. The API and
browser expose a full-bundle annual financial profile with growth/margins, dated citations,
coverage counts and independent JSON export. Original sources remain immutable and v1 archives
remain supported. Current-revision QA, CI and independent review are tracked in STATUS.md.
