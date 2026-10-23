# Plan and decisions — 2026-10-23

Build the mandatory Sprint 0–3 vertical slice before adding research sophistication.
The repository initially contained only the owner's nine numbered specification files and no commits.

- Python 3.12, pydantic immutable records, PyArrow/Parquet, FastAPI, React/TypeScript/Vite.
- Fixture-first because no licensed historical market entitlement or SEC contact identity was provided.
- SEC raw submissions adapter is available; normalize accession-level facts before using real PIT data.
- Three fictional common shares, one benchmark, explicit zero-proceeds delisting and incomplete horizons.
- No container registry or deployment target. Build locally from lockfiles; never deploy automatically.
- Owner authorized public GitHub visibility and pushing on 2026-10-23, superseding private-by-default setup.
- New empty remote requires publishing the owner's existing specification as an initial main baseline;
  implementation is authored on feat/workflow-harness and lands only via reviewed squash PR.
- Harness copied from TenFold checkout `38d6c50170a373ede299f3fd96535c3dc47ed7e1`.
  Latest scripts/.github source commit: `336a043` (Gemini via Antigravity CLI, #141).
  Reviewer pool, model pins and effort settings preserved. Only approved project-specific areas changed.
- Critical paths: packages/data/, packages/shared/, packages/research/, packages/backtest/,
  packages/pipeline.py, apps/api/, scripts/, .github/workflows/. The gate and CI are critical themselves.

Next funded-data milestone: implement a licensed historical universe/bars/actions adapter, audit delisted
coverage and adjustment semantics, then replay the same acceptance gates with real observations.

Later: configurable stages and score families, broader event studies, purged validation and untouched
holdout, honest uncertainty, supported theses, incremental refresh. None are validated by fixture results.

2026-10-23 owner decision: use BagHunter consistently across app and documentation, including
Radar navigation and watchlist exports. Complete the reviewed branding squash merge before starting
the next implementation item. Research-output fingerprints must remain unchanged by the rename.

2026-10-23 sequencing checkpoint: branding was committed/pushed, CI passed, Claude independently
approved with zero blockers, and PR #15 was squash-merged as 389db89. The tracked worktree was clean
on main before the historical import branch was created. No provider credentials or entitlement were
supplied; implement a provider-neutral local-export adapter and coverage audit without subscriptions,
network data requests, fabricated observations or automatic research activation.

2026-10-23 provider clarification: the owner already has Finviz Elite. Official sources support
current screener CSV/API workflows but do not establish historical PIT membership or delisting
coverage. First inspect an owner-exported CSV before implementing its current-snapshot converter;
do not guess the authenticated export schema or backdate today's fundamentals. See FINVIZ.md.
