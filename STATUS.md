# Current handoff — 2026-10-23

Sprint 0–3 fixture vertical slice implemented on feat/workflow-harness. Local checks ran against the
implementation worktree being submitted in the initial PR. Run `e0280e146da378f5`; package source digest
`4f432c33286a64f0b56defd403209e300c25346d2c255e160c575fe9cb52670c`. Initial head dc64336 passed Linux CI, Windows harness, dependency/secret audits and Gemini review
(APPROVE, zero blockers). The revised head must pass the same gates before merge.

## Executed evidence

- Initial full `pwsh -NoProfile -File scripts/qa.ps1` (20 backend / 3 browser tests): locked Python/npm installs, harness self-test, skill validation,
  ruff lint/format, mypy, integrity/API tests, demo CLI, frontend lint/types/build, 3 browser tests.
- Tests cover future filing/amendment rejection, negative/missing prices, ticker reuse, independent
  split/dividend/delist wealth expectations, missing horizons, matched peers, next-open costs,
  separated labels, manifest checksums, reproducibility, source failures and API readiness.
- Browser: profile factors/citations, case/control museum, evaluation/baselines, source ledger,
  search/empty state, missing backend, desktop/mobile axe scans and no page overflow. Screenshots
  inspected at artifacts/screenshots/command-center.png and mobile.png.
- Saved logs and JUnit: artifacts/test_results/. Coverage XML: coverage.xml; last measured total 89%.
- Demo: 3 profiles, 12 horizon labels, 1 matched pair, 13 sequential screening windows.
- Historical anchor 2020-01-01; candidate clock 2022-01-03T23:00:00+00:00; toy period
  2019-12-31–2022-01-05.
- Latest synthetic source timestamp: 2023-03-30T22:00:00+00:00.
- Initial failures fixed: zero-volume denominator, missingness type inference, Windows directory lock
  retry, mismatched fixture peer strata, accessible score names and root data ignore pattern.

## Review hardening

Both Gemini advisories were addressed: explicit UTF-8 run reads and deterministic split → dividend →
delist ordering. An additional audit found that missing evaluation exits could retain numeric wealth;
comparisons now fail closed instead. Research clocks normalize to UTC before calendar-date filters.
Three regression tests cover missing exits, reversed same-date action inputs and equivalent timezone
instants. Revised local checks: ruff lint/format, mypy, 23 pytest tests, CLI demo and browser suite.
Prior full QA logs remain at artifacts/test_results; current-head CI/review proof is in
https://github.com/rahul-reddy/BagHunter/pull/1. Never infer approval of a revised head from prior review.

## Remaining boundaries

Entirely synthetic fixture; no empirical alpha or real stock recommendations. Zero verified theses.
Real historical PIT universe/bars/actions entitlement is unavailable. SEC download needs a real
contact user agent; only a raw submissions client exists, with PIT fact parsing/pagination pending.
Full stage history, industry breadth, real market cap, rigorous holdout, capacity constraints and
live refresh remain unimplemented. Framework httpx TestClient deprecation and ESLint 9 support
notice are non-blocking tooling advisories; npm reported zero vulnerabilities locally.

No deployment or automatic jobs. Start local services with README commands; tests stop their services.
Owner authorized public pushes. Original specification preserved in bootstrap main commit 6c994b5;
implementation goes through a squash PR and scripts/merge-pr.ps1 only.

Next action: wait for CI on the PR head, execute cross-review.ps1, address blockers, then gated merge.
Next implementation milestone: a licensed PIT market-data adapter and real-data coverage audit.
