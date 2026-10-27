# Remaining specification work — audit at main 00092299 / 2026-10-27

This is an open-work register, not a claim that unlisted requirements are complete. The numbered
specifications remain authoritative. Final completion still needs item-by-item evidence for every
requirement; docs/ACCEPTANCE.md is an area summary only.

| Requirement | Current evidence | Remaining software or evidence |
| --- | --- | --- |
| 01/02/06: useful current-company research and cited scenario memos | Baseline Finviz desk has notes; SEC evidence and fixture Thesis Studio are separate | PR #32 merged the explicit issuer evidence, assumption scenarios, drafts and cited exports; broader evidence/thesis acceptance remains open |
| 02 E: 20/60-day volatility and contraction | technical-evidence-v1 computes 20/60-day volatility and zero-reference missingness | PR #33 delivered the catalog; empirical calibration remains unavailable |
| 01/02 E: base duration, gap behavior and proximity to highs | Dated prior-high distance, opening/mean gap and bounded prior-window duration now implemented | PR #33 delivered diagnostics; a duration/rank ignition gate needs a separate versioned policy |
| 02 E: market/industry relative ranks, participation and dispersion | Dated market/sector ranks, self-excluded sector-relative returns, participation and dispersion now implemented | PR #33 delivered diagnostics; sector is a proxy and industry/PIT history remains unestablished |
| 02 F / 04 S5: complete configured stage criteria and full signal history | Current stage-policy branch adds explicit v2 duration/rank gates, original triggers, cited annual inflections and full replay | Current-source acceptance/review/delivery pending; catalysts require supported evidence, annual proxies remain explicit |
| 02 E/I / 04 S7 / 06: qualitative evidence, peer valuation and separate critique | Freeform source questions, bear text, calendar assertions and scenario inputs exist | Add source-bound qualitative categories, cited peer bands, opportunity-cost/time-to-thesis fields and separately attributed critic workflow; verified conclusions depend on evidence |
| 02 D: t−120/t−60/t−20/t/t+20 pre-event paths | Current calendar-event-paths-v1 adds 17 declared anchors, 240 dated points, matched failures and missing/unmatched records | Final gates pending in STATUS.md; later snapshots stay hindsight and broader company evolution still requires qualitative evidence |
| 02 E: gross-margin change, revenue/share, SBC and working capital | Current financial-concepts branch implements typed concepts, same-period/filing ratios, cited derivation reasons and grouped UI | PR #37 delivered through CI/review/main preview; saved source lacks GrossProfit and contiguous four-quarter coverage; class/per-share applicability cannot be inferred |
| 05: risk-scaled and sector-neutral comparators | Current allocation-v1 adds equal weight, inverse volatility, equal-sector targets and cash with full ledgers | PR #34 delivered bounded comparisons; sector/benchmark neutrality and empirical efficacy remain unestablished |
| 05: contributor/name/sector exclusions; lag/action sensitivities | Cost, weight/liquidity, subgroups and paired bootstrap exist | Implement declared robustness variants; retain failed/missing variants rather than select a best result |
| 04 S8 / 07: operational resource/recovery evidence | Immutable cache/run publication, bounded provider calls, manual refresh templates and Ctrl+C cleanup guidance exist | Audit disk/resource budgets, resume/recovery procedures and basic load evidence; docs/OPERATIONS.md still has pre-history-pagination prose to reconcile |
| 07/08: final release evidence | Reviewed source archives/receipts exist; reports/RELEASE_READINESS.md is stale | Update matrix against final main, sampled outputs, commands and exact CI/review evidence |
| 00–08: empirical history/calibration and substantiated theses | Finviz current overview and one SEC entity archive exist; fixtures remain separate | Verify supported Finviz history/identity/unit/action contracts; retain unresolved vintages, universe/delist coverage and zero verified theses. Another subscription is not a default prerequisite |

Next after event-path acceptance: extend remaining financial concepts, then complete the stage,
qualitative/critic, robustness and operations work before the final requirement-by-requirement audit.
Data limitations do not block independent software work.
