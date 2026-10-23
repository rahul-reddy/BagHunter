# Current handoff — historical export staging / 2026-10-23

## Sequencing checkpoint

The complete BagHunter rename was committed/pushed, passed CI and local 23-backend/3-browser checks,
received Claude approval with zero blockers, then squash-merged through merge-pr.ps1 in
[PR #15](https://github.com/rahul-reddy/BagHunter/pull/15) as 389db89. The tracked worktree was clean
on main before feat/historical-data-import was created. The next item did not start before that merge.
Research output fingerprint before/after branding remained
84fcdf1abf85770ab82a5dcf9d4cb90a42b7c90e7adca1f4e53af1c827090fbb.

## Implemented increment

- packages/data/history.py: normalized local-export provider, dated membership/symbol reads,
  raw-bar policy, filing-lag cutoffs, source/ID/checksum validation and coverage audit.
- CLI: audit-history and ingest-history; errors suppress raw input values. No provider HTTP calls.
- Inputs: explicit license-use attestation, source vintage, expected sessions, seven hashed tables.
- Outputs: raw bytes, typed silver Parquet and coverage.json in immutable, separate fixture/external
  quarantine namespaces. No candidate activation, broker actions or empirical claims.
- Fixture example: two fictional instruments, five bars and one zero-proceeds delisting; facts missing.
- Limits: 20 MiB/table, 64 KiB manifest and five million instrument/session audit combinations.

## Executed evidence and gates

49 backend tests passed on the implementation worktree; ruff lint/format and mypy passed.
Actual CLI audit and ingestion produced QUARANTINED_NOT_RESEARCH_READY with FIXTURE_ONLY and
FUNDAMENTALS_MISSING. Snapshot bf12ff7006865a18d2c5dd4b7d56fd60688a64b38166d0a3526b9e64c31443a7.
Tests cover PIT revisions/expiry, future source clocks, price/action metadata, missing coverage,
source authorization, checksum and archive tampering, namespace separation, input caps and redaction.
Actual UTC ingestion time is retained on repeats; future ingestion records fail closed. A transient
workspace publish failure did not reproduce on retry; bounded file-lock retry is now regression-tested.
Example JSON is pinned to LF for checksum stability; all 26 history tests were rechecked after
normalizing working-copy line endings.
JUnit: artifacts/test_results/history-pytest.xml; coverage.xml is from the expanded suite.
History adapter file SHA-256 at local verification: 4c992180bd3fb852da8235764e20b2f0d1b4d6eeb02f8ad0e02c7de21640dcc5.
Current-head CI and independent approval remain mandatory before this increment may merge.

## Limitations and next step

No licensed provider/export has been supplied. All executable examples are synthetic. External
exports remain unverified: schema/checksum checks cannot independently prove licensing, archived
universe completeness, original bar vintage, calendar accuracy or correct delisting coverage.
No new research findings, activated real candidates or verified theses. Filing documents and vendor
API authentication are unsupported by this adapter. Large exports must be partitioned.

Next: map one authorized provider export to docs/HISTORICAL_IMPORT.md and independently audit its
coverage before adding explicit real-data research activation. No subscription or spending occurred.

Nonblocking branding review advisories remain recorded in PR #15: branded export regression coverage
and duplicate brandmark announcement. Its handoff heading advisory is addressed by this archive layout.
Prior CSV-encoding and framework tooling advisories remain as described below; no comments were changed.
Review access: API-funded Claude was unavailable; a process-local removal of API auth overrides used
its already logged-in claude.ai subscription for the independent review. No stored authentication settings were edited.

## Prior handoffs

### Current handoff — BagHunter branding / 2026-10-23

The app, browser title, header/footer/logo, Radar navigation, API title, CLI help, npm metadata,
project brief and documentation now use BagHunter. The watchlist export is baghunter_watchlist.csv.
This rename is isolated on feat/baghunter-branding and must be fully squash-merged before the next item.

Local validation on the rename worktree: 23 backend tests, ruff lint/format and mypy passed;
CLI help and imported API title checked. A tracked-file search found no stale product-name references.
Research signals, cohort study and toy evaluation have identical before/after SHA-256 fingerprint:
`84fcdf1abf85770ab82a5dcf9d4cb90a42b7c90e7adca1f4e53af1c827090fbb`.
Only run identity and the branded export filename change. Fixture-only research limitations persist.
Browser smoke now asserts the BagHunter page title; frontend checks and current-head CI/review are
required before merge. CI and independent approval are authoritative in the branding PR.

Next item remains the licensed PIT market-data adapter and coverage audit. Start it only after the
branding PR is merged and the tracked worktree is clean. The local preview was started during the
owner's prior session; restart the API after merge to pick up its title change.

#### Previous verified fixture release

### Current handoff — fixture MVP shipped / 2026-10-23

Sprint 0–3 fixture vertical slice merged through [PR #1](https://github.com/rahul-reddy/BagHunter/pull/1)
at `656cc7e8906cf0ea3add52404da10eb455034cf9`. The tested/reviewed PR head was
`7269b132db3b7cf202c6d86c7e249e2150eaee85`; both commits have identical Git tree
`e5493b495f18ca9f8c95dcd1244c14ca0d3f258a`. This handoff changes documentation only.

- [Linux CI](https://github.com/rahul-reddy/BagHunter/actions/runs/39962076649): PASS, including
  23 backend tests, 3 browser tests, builds, types/lint, harness and skill checks.
- [Windows harness](https://github.com/rahul-reddy/BagHunter/actions/runs/39962076692): PASS.
- [Gemini exact-head review](https://github.com/rahul-reddy/BagHunter/pull/1#issuecomment-6366233806):
  APPROVE, zero blocking findings. Merge executed only with scripts/merge-pr.ps1.
- Dependency advisories: no known Python/npm vulnerabilities. Gitleaks: no leaks found.
- Demo run `e0280e146da378f5`; package source digest
  `4f432c33286a64f0b56defd403209e300c25346d2c255e160c575fe9cb52670c`.

#### Executed evidence

- Initial full `pwsh -NoProfile -File scripts/qa.ps1` (20 backend / 3 browser tests): locked Python/npm installs, harness self-test, skill validation,
  ruff lint/format, mypy, integrity/API tests, demo CLI, frontend lint/types/build, 3 browser tests.
- Tests cover future filing/amendment rejection, negative/missing prices, ticker reuse, independent
  split/dividend/delist wealth expectations, missing horizons, matched peers, next-open costs,
  separated labels, manifest checksums, reproducibility, source failures and API readiness.
- Browser: profile factors/citations, case/control museum, evaluation/baselines, source ledger,
  search/empty state, missing backend, desktop/mobile axe scans and no page overflow. Screenshots
  inspected at artifacts/screenshots/command-center.png and mobile.png.
- Saved logs and JUnit: artifacts/test_results/. Local coverage.xml measured 89% on the initial 20-test suite; final CI includes its own coverage XML.
- Demo: 3 profiles, 12 horizon labels, 1 matched pair, 13 sequential screening windows.
- Historical anchor 2020-01-01; candidate clock 2022-01-03T23:00:00+00:00; toy period
  2019-12-31–2022-01-05.
- Latest synthetic source timestamp: 2023-03-30T22:00:00+00:00.
- Initial failures fixed: zero-volume denominator, missingness type inference, Windows directory lock
  retry, mismatched fixture peer strata, accessible score names and root data ignore pattern.

#### Review hardening

Both Gemini advisories were addressed: explicit UTF-8 run reads and deterministic split → dividend →
delist ordering. An additional audit found that missing evaluation exits could retain numeric wealth;
comparisons now fail closed instead. Research clocks normalize to UTC before calendar-date filters.
Three regression tests cover missing exits, reversed same-date action inputs and equivalent timezone
instants. Revised local checks: ruff lint/format, mypy, 23 pytest tests, CLI demo and browser suite.
Full QA and final CI logs remain at artifacts/test_results. Final reviewed-head proof is linked above.
Remaining nonblocking advisory: CSV exports lack explicit UTF-8 encoding; current fixture export
fields are ASCII. Fix before supporting real multilingual names. No advisory was hidden or deleted.

#### Remaining boundaries

Entirely synthetic fixture; no empirical alpha or real stock recommendations. Zero verified theses.
Real historical PIT universe/bars/actions entitlement is unavailable. SEC download needs a real
contact user agent; only a raw submissions client exists, with PIT fact parsing/pagination pending.
Full stage history, industry breadth, real market cap, rigorous holdout, capacity constraints and
live refresh remain unimplemented. Framework httpx TestClient deprecation and ESLint 9 support
notice are non-blocking tooling advisories; npm reported zero vulnerabilities locally.

No deployment, automatic jobs or currently running preview. Start services with README commands.
Automatic approval review rejected detached preview startup with "blocked by policy" and no more
specific reason. Terminal startup was verified by the automated browser suite.
Owner authorized public pushes. Original specification preserved in bootstrap main commit 6c994b5;
implementation goes through a squash PR and scripts/merge-pr.ps1 only.

Next implementation milestone: a licensed PIT market-data adapter and real-data coverage audit.
Real-data gates remain blocked; do not interpret fixture acceptance as empirical research success.
