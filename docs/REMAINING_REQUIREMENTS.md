# Remaining specification work — audit at main ed0042ce / 2026-10-26

This is an open-work register, not a claim that unlisted requirements are complete. The numbered
specifications remain authoritative. Final completion still needs item-by-item evidence for every
requirement; docs/ACCEPTANCE.md is an area summary only.

| Requirement | Current evidence | Remaining software or evidence |
| --- | --- | --- |
| 01/02/06: useful current-company research and cited scenario memos | Baseline Finviz desk has notes; SEC evidence and fixture Thesis Studio are separate | PR #32 merged the explicit issuer evidence, assumption scenarios, drafts and cited exports; broader evidence/thesis acceptance remains open |
| 02 E: 20/60-day volatility and contraction | technical-evidence-v1 computes 20/60-day volatility and zero-reference missingness | PR #33 delivered the catalog; empirical calibration remains unavailable |
| 01/02 E: base duration, gap behavior and proximity to highs | Dated prior-high distance, opening/mean gap and bounded prior-window duration now implemented | PR #33 delivered diagnostics; a duration/rank ignition gate needs a separate versioned policy |
| 02 E: market/industry relative ranks, participation and dispersion | Dated market/sector ranks, self-excluded sector-relative returns, participation and dispersion now implemented | PR #33 delivered diagnostics; sector is a proxy and industry/PIT history remains unestablished |
| 02 F / 04 S5: complete configured stage criteria and full signal history | discovery-v1 uses a 60-day high/volume/width rule and a 21-session initialized history | Add explicit duration/rank ignition gates, maintained breakout and multiple filing/catalyst evidence criteria under a versioned policy; full history still needs implementation |
| 02 E/I / 04 S7 / 06: qualitative evidence, peer valuation and separate critique | Freeform source questions, bear text, calendar assertions and scenario inputs exist | Add source-bound qualitative categories, cited peer bands, opportunity-cost/time-to-thesis fields and separately attributed critic workflow; verified conclusions depend on evidence |
| 02 D: t−120/t−60/t−20/t/t+20 pre-event paths | cohort_grid and anchor_features provide cohort/anchor snapshots | Implement pre-registered event-path study and failed-peer comparison; later points remain descriptive/hindsight |
| 02 E: gross-margin change, revenue/share, SBC and working capital | SEC adapter supports revenue/income/cashflow, EPS, shares, PPE and selected balances | Extend concept contracts and exact-period arithmetic; class/per-share applicability cannot be inferred |
| 05: risk-scaled and sector-neutral comparators | Current allocation-v1 adds equal weight, inverse volatility, equal-sector targets and cash with full ledgers | Current final gates pending in STATUS.md; sector/benchmark neutrality and empirical efficacy remain unestablished |
| 05: contributor/name/sector exclusions; lag/action sensitivities | Cost, weight/liquidity, subgroups and paired bootstrap exist | Implement declared robustness variants; retain failed/missing variants rather than select a best result |
| 04 S8 / 07: operational resource/recovery evidence | Immutable cache/run publication, bounded provider calls, manual refresh templates and Ctrl+C cleanup guidance exist | Audit disk/resource budgets, resume/recovery procedures and basic load evidence; docs/OPERATIONS.md still has pre-history-pagination prose to reconcile |
| 07/08: final release evidence | Reviewed source archives/receipts exist; reports/RELEASE_READINESS.md is stale | Update matrix against final main, sampled outputs, commands and exact CI/review evidence |
| 00–08: empirical history/calibration and substantiated theses | Finviz current overview and one SEC entity archive exist; fixtures remain separate | Verify supported Finviz history/identity/unit/action contracts; retain unresolved vintages, universe/delist coverage and zero verified theses. Another subscription is not a default prerequisite |

Next after portfolio comparison acceptance: implement event-path and remaining financial concepts,
then the declared robustness variants and final requirement-by-requirement audit. Data limitations
do not block independent software work.
