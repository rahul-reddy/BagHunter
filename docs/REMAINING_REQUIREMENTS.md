# Remaining specification work — checkpoint at main 7a104f7 / 2026-10-28

This is an open-work register, not a claim that unlisted requirements are complete. The numbered
specifications remain authoritative. Final completion still needs item-by-item evidence for every
requirement; docs/ACCEPTANCE.md is an area summary only.

| Requirement | Current evidence | Remaining software or evidence |
| --- | --- | --- |
| 01/02/06: useful current-company research and cited scenario memos | Baseline Finviz desk has notes; SEC evidence and fixture Thesis Studio are separate | PR #32 merged the explicit issuer evidence, assumption scenarios, drafts and cited exports; broader evidence/thesis acceptance remains open |
| 02 E: 20/60-day volatility and contraction | technical-evidence-v1 computes 20/60-day volatility and zero-reference missingness | PR #33 delivered the catalog; empirical calibration remains unavailable |
| 01/02 E: base duration, gap behavior and proximity to highs | Technical catalog and discovery-v2 duration/rank/original-trigger gates are delivered | Empirical calibration remains unavailable; see STAGE_POLICY.md |
| 02 E: market/industry relative ranks, participation and dispersion | Dated market/sector ranks, self-excluded sector-relative returns, participation and dispersion now implemented | PR #33 delivered diagnostics; sector is a proxy and industry/PIT history remains unestablished |
| 02 F / 04 S5: complete configured stage criteria and full signal history | PR #38 delivered v2 duration/rank gates, original triggers, cited annual inflections and full replay | CI/review/main-preview evidence is tracked in STATUS.md; catalysts require supported evidence, annual proxies remain explicit |
| 02 E/I / 04 S7 / 06: qualitative evidence, peer valuation and separate critique | PR #39 and #43 delivered both research desks, sixteen risk topics, peer bands, horizons, source-bound critic packets and saves/exports | Source statements and reviewer independence remain unverified; real evidence-backed theses are blocked by source gaps |
| 02 D: t−120/t−60/t−20/t/t+20 pre-event paths | Current calendar-event-paths-v1 adds 17 declared anchors, 240 dated points, matched failures and missing/unmatched records | PR #35/#36 delivered with CI/review/main preview; later snapshots stay hindsight and broader company evolution still requires qualitative evidence |
| 02 E: gross-margin change, revenue/share, SBC and working capital | Current financial-concepts branch implements typed concepts, same-period/filing ratios, cited derivation reasons and grouped UI | PR #37 delivered through CI/review/main preview; saved source lacks GrossProfit and contiguous four-quarter coverage; class/per-share applicability cannot be inferred |
| 05: risk-scaled and sector-neutral comparators | Current allocation-v1 adds equal weight, inverse volatility, equal-sector targets and cash with full ledgers | PR #34 delivered bounded comparisons; sector/benchmark neutrality and empirical efficacy remain unestablished |
| 05: contributor/name/sector exclusions; lag/action sensitivities | PR #41 delivered twelve retained stresses, constrained ledgers, recovery metrics and six feature ablations | Main preview passed; independent adjusted series is unavailable and fixture checks do not prove empirical robustness |
| 04 S8 / 07: operational resource/recovery evidence | PR #40 delivered disk/restore/load audit and cancellation/rerun acceptance | Main audit verified 74,217,257 archive bytes, restore and twelve concurrent-bounded requests; no RAM enforcement, automatic pruning or CPU checkpoint is claimed |
| 01/03/06: named report detail and reproducible notebook | Current report branch repairs links/clocks/anchor/interval templates; a seven-cell notebook and runner are locally tested in a separate branch | Finish exact-head delivery and inspect final artifacts; target schema/field and classification metrics need item-level audit |
| 07/08: final release evidence | Reviewed source archives/receipts exist; reports/RELEASE_READINESS.md is stale | Update matrix against final main, sampled outputs, commands and exact CI/review evidence |
| 00–08: empirical history/calibration and substantiated theses | Finviz current overview and one SEC entity archive exist; fixtures remain separate | Verify supported Finviz history/identity/unit/action contracts; retain unresolved vintages, universe/delist coverage and zero verified theses. Another subscription is not a default prerequisite |

Next: deliver report/notebook increments and finish the explicit schema, field, classification and
per-item release audit. Do not treat passing area summaries as complete specification proof.
Data limitations do not block independent software work.
