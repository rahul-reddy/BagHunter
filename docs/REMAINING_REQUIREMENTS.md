# Remaining specification work — audit at main 15f6406 / 2026-10-26

This is an open-work register, not a claim that unlisted requirements are complete. The numbered
specifications remain authoritative. Final completion still needs item-by-item evidence for every
requirement; docs/ACCEPTANCE.md is an area summary only.

| Requirement | Current evidence | Remaining software or evidence |
| --- | --- | --- |
| 01/02/06: useful current-company research and cited scenario memos | Baseline Finviz desk has notes; SEC evidence and fixture Thesis Studio are separate | PR #32 merged the explicit issuer evidence, assumption scenarios, drafts and cited exports; broader evidence/thesis acceptance remains open |
| 02 E: 20/60-day volatility and contraction | technical-evidence-v1 computes 20/60-day volatility and zero-reference missingness | Current catalog final gates pending in STATUS.md; empirical calibration remains unavailable |
| 01/02 E: base duration, gap behavior and proximity to highs | Dated prior-high distance, opening/mean gap and bounded prior-window duration now implemented | Current catalog final gates pending; a duration/rank ignition gate needs a separate versioned policy |
| 02 E: market/industry relative ranks, participation and dispersion | Dated market/sector ranks, self-excluded sector-relative returns, participation and dispersion now implemented | Current catalog final gates pending; sector is a proxy and industry/PIT history remains unestablished |
| 02 D: t−120/t−60/t−20/t/t+20 pre-event paths | cohort_grid and anchor_features provide cohort/anchor snapshots | Implement pre-registered event-path study and failed-peer comparison; later points remain descriptive/hindsight |
| 02 E: gross-margin change, revenue/share, SBC and working capital | SEC adapter supports revenue/income/cashflow, EPS, shares, PPE and selected balances | Extend concept contracts and exact-period arithmetic; class/per-share applicability cannot be inferred |
| 05: risk-scaled and sector-neutral comparators | PortfolioPolicy selectors: momentum_63d, momentum_12_1, revenue_growth, seeded_random | Add allocation variants under identical cash/cost/capacity/sector constraints |
| 05: contributor/name/sector exclusions; lag/action sensitivities | Cost, weight/liquidity, subgroups and paired bootstrap exist | Implement declared robustness variants; retain failed/missing variants rather than select a best result |
| 07/08: final release evidence | Reviewed source archives/receipts exist; reports/RELEASE_READINESS.md is stale | Update matrix against final main, sampled outputs, commands and exact CI/review evidence |
| 01–09: empirical history/calibration and substantiated theses | Finviz current overview and one SEC entity archive exist; fixtures remain separate | Verify supported Finviz history/identity/unit/action contracts; retain unresolved vintages, universe/delist coverage and zero verified theses. Another subscription is not a default prerequisite |

Next after technical catalog acceptance: implement risk-scaled/sector-neutral portfolio allocation
variants, then the remaining event-path and financial concept work. Data limitations do not block software work.
