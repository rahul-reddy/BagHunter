# Sprint status — 2026-10-23

Current increment: bounded OpenFIGI current-reference evidence, after browser PR #20 merged.
Local suite: 152 backend tests passed, two Windows symlink skips; six browser tests passed.
Ten of 11,783 source observations were queried; ten candidates, zero identity promotions.
Owner authorized a Finviz Elite API export; 11,783 screener rows are saved locally, separate from
the synthetic dashboard. The ingest-finviz CLI stages typed JSON/Parquet observations with source
checksums, missingness and unknown identity/unit flags. Finviz Observations now provides a separate,
explicitly selected read-only snapshot browser; field units/types/IDs remain unverified. Historical
PIT/delisting coverage remains unverified. External imports stay quarantined. See docs/FINVIZ.md.
The Sprint 4 empirical gates remain BLOCKED. See docs/HISTORICAL_IMPORT.md and STATUS.md.

| Sprint | Acceptance | Evidence / limits |
| --- | --- | --- |
| 0 | PASS locally | Python 3.12/React scaffold; locked installs; lint, types, tests, build; health and dashboard |
| 1 | PASS fixture path; real SEC BLOCKED | immutable raw SHA, permanent IDs/symbols, validated Parquet, as-of profiles; raw-only SEC adapter |
| 2 | PASS fixture scope | PIT cutoff, known filing revisions, 1/2/3/5Y labels with missing horizons, failed-peer matching, features |
| 3 | PASS local P0 fixture path | CLI → storage → API → browser, candidate charts/evidence, failed peer, 13-window toy baseline comparison |
| 4–9 empirical research | BLOCKED / deferred | no licensed historical PIT universe, real actions/delist coverage or substantiated candidates |

Initial local `scripts/qa.ps1`: 20 pytest tests; 3 Playwright tests; desktop/mobile accessibility;
ruff, mypy, TypeScript, ESLint, Vite build; review harness self-test and skill validation.
After review hardening, 23 backend tests and 3 browser tests passed locally and in final CI.
Evidence: artifacts/test_results/, coverage.xml, apps/web/playwright-report/, artifacts/screenshots/.
Fixture run `e0280e146da378f5`; latest source `2023-03-30T22:00:00+00:00`.
Raw lineage SHA: `7d8ee2fcb1af8c890f9eb5b7991926f5162d9615a0a79fb6ccc7c0071a2b2be7`.

Scope: 3 fictional common shares + market baseline, weekday observations 2019-01-01–2023-03-30;
case/control anchor 2020-01-01; toy decisions 2019-12-31–2022-01-05 including execution.
No empirical conclusions or verified theses. Missing subscriptions: historical PIT market data.
No real SEC ingestion without contact identity; no historical financial parser yet.

Initial observed failures and fixes are recorded in STATUS.md. Next priority: a licensed PIT market-data adapter and coverage audit.

Release: PR #1 merged via merge-pr.ps1 as 656cc7e, with the same tree as tested/reviewed
head 7269b13. Final Linux CI, Windows harness and Gemini review passed (zero blockers).
23 backend tests include fail-closed evaluation, same-day actions and UTC clock equivalence.
One nonblocking CSV UTF-8 advisory remains; fixture exports use ASCII fields.
