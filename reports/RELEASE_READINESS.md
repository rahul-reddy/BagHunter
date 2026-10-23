# Release readiness — fixture MVP / 2026-10-23

| Gate | Status | Evidence |
| --- | --- | --- |
| Locked installs / lint / types / frontend build | PASS locally | scripts/qa.ps1; artifacts/test_results |
| PIT / amendments / identity / actions / missing outcomes | PASS fixture scope | 23 pytest tests; pytest.xml |
| Deterministic CLI / separated Parquet / checksums | PASS fixture scope | run e0280e146da378f5; manifest and repeat-run tests |
| API → browser / source citations / stale and missing states | PASS locally | 3 Playwright tests; apps/web/playwright-report |
| Desktop/mobile accessibility and layout | PASS scanned views | axe: command center desktop/mobile, data ledger; screenshots inspected |
| Copied review harness / repository skill | PASS locally | cross-review-selftest.ps1; validate_skills.py |
| GitHub exact-head CI / independent PR review / guarded merge | PENDING revised head | initial dc64336 passed CI and Gemini; PR #1 records revised-head gates |
| Real historical provider / delisted coverage | BLOCKED | no licensed entitlement configured |
| Real SEC PIT-normalized sample | BLOCKED | identifying contact not supplied; historical fact parser pending |
| Empirical OOS findings / verified theses | BLOCKED | no real evidence; zero verified theses |
| Public deployment | NOT REQUESTED | local application only |

The 13-window comparison covers 2019-12-31–2022-01-05 and uses only fictional prices.
It demonstrates next-open execution, costs, equal-weight and market comparators; it cannot establish
predictive power. No fitted model, untouched holdout, confidence intervals or production capacity claims.
Missing long-horizon labels remain null. The fixture contains a zero-proceeds failed security.

Real empirical Sprint 4–9 gates are not satisfied. Highest risks: absent PIT historical market
membership/actions/returns, missing real filings, synthetic sample selection, unvalidated stage/score
rules and incomplete tradability/capacity modeling. Current framework TestClient deprecation and
ESLint 9 support notice do not prevent the tested release from running.
