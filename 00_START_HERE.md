# BagHunter — 100-Bagger DNA Lab

> **Agent entrypoint.** Read this file first, then read the linked documents in order. Treat the combined package as the source of truth for the build.

## Mission
Build a **runnable, reproducible US-equities research platform** combining historical multibagger archaeology and forward-looking alpha discovery. Analyze successful and failed lookalikes using point-in-time evidence; turn robust findings into a screening and validation system; publish explainable candidate profiles and falsifiable theses. **Research and simulation only: no broker orders, auto-trading, promised returns or invented forecasts.**

## Read order
1. `01_MASTER_MISSION.md` — scope, success and rules.
2. `02_RESEARCH_METHODOLOGY.md` — historical case/control study and signal validation.
3. `03_DATA_AND_ARCHITECTURE.md` — schemas, providers, PIT treatment and software design.
4. `04_IMPLEMENTATION_SPRINTS.md` — implementation sequence and exit gates.
5. `05_BACKTEST_RISK_AND_VALIDATION.md` — independent validation and risk model.
6. `06_PRODUCT_UI_AND_REPORTS.md` — dashboard and written outputs.
7. `07_TESTS_ACCEPTANCE_AND_OPERATIONS.md` — executable quality gates, operation and release.
8. `08_AGENT_EXECUTION_CONTRACT.md` — autonomy, checkpoints, budget and handoff.

## First executable objective
**By Sprint 3, demonstrate a verified end-to-end vertical slice:** ingest a small REAL historical price/filing sample (or clearly labeled offline fixture where credentials are unavailable), construct a historical outcome cohort with controls, compute *point-in-time* eligible features, run a walk-forward toy screening evaluation, and display one traceable candidate profile. It is not acceptable to substitute fabricated market results.

## Agent kickoff command
Read all Markdown files. Inspect repository and environment. Write `SPRINT_STATUS.md` and `NEXT_ACTION.md`. Begin Sprint 0 and then build the vertical slice. Make the project runnable after each sprint; execute tests and preserve evidence. Do not stop at architecture or ask routine design questions. If data is unavailable, implement adapters plus flagged fixtures and explicitly distinguish demo results from real empirical conclusions. Do not subscribe, spend money, deploy publicly or trade without explicit permission.

## Required handoff
Repository, installation guide, reproducible data/feature pipeline, screeners, historical study, baselines, backtest notebooks or code, live-ish dashboard with freshness labels, 3–5 evidence-backed theses **if data suffices**, tests/results, source references, limitations, and final PASS/FAIL/BLOCKED matrix.

## Important warning
Even rigorous historical testing cannot establish that present-day candidates will become multibaggers. Report uncertainty, liquidity, dilution, opportunity cost, survivorship limitations and failed tests prominently.
