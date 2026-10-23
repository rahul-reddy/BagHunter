# 01 — Master mission and definition of success

## Vision
Create **Alpha Hunter: The 100-Bagger DNA Lab**, a reusable investment research lab for early detection of potentially asymmetric equity opportunities. Combine:

- **Archaeologist:** reconstruct what was knowable *before* extraordinary returns, including comparable nonwinners and delisted names.
- **Discovery engine:** detect early price/volume breaks from consolidation, relative strength, accelerating financial performance, balance sheet changes, capital-cycle shifts and catalysts.
- **Skeptical investment committee:** explain bull/base/bear cases, competitive advantages, dilution, liquidity, downside and thesis breakers.
- **Research terminal:** visualize every signal, supporting source, market-data timestamp, uncertainty and model version.

## User-oriented preferences
- Primary US common shares. Include microcaps and small caps, but do not exclude larger early compounders; segment analysis by market cap and liquidity.
- Highlight < $500M and $500M–$1B subuniverses separately when data quality permits.
- Emphasize momentum ignition after long consolidation; evaluate 1D/1W/1M/3M changes, 8/21 EMA, 20/60/120-day base behavior, volume expansion, relative strength, fundamental catalysts and sector breadth.
- Assign transparent stage tags: WATCH, IGNITION, EMERGING, CONFIRMED, EXTENDED/AGING, INVALIDATED. These are rule-based research labels, not trade commands.
- Provide ranked scores by fundamental inflection, business quality, valuation, price/volume, catalyst evidence, liquidity/risk, with confidence and missing-data penalties.
- Produce deeper scenarios for 3–5 names only when evidence is sufficient; otherwise return fewer and clearly say why.

## Non-negotiable research integrity
1. Never invent an observation, citation, price, financial report, result, confidence interval or ticker history.
2. Point-in-time as-of discipline: no future earnings, revised databases, contemporary sector classifications, hindsight winners or current constituents masquerading as historical knowledge.
3. Include failed lookalikes, delistings, bankruptcies and acquirer exits when licensed history permits. Report coverage gaps.
4. Use split/dividend/corporate action treatments explicitly; report both total return and relevant price return where appropriate.
5. Differentiate exploratory pattern mining from truly out-of-sample validation. Freeze model before untouched tests.
6. Assess turnover, spreads/slippage, liquidity/capacity, financing, transaction costs, benchmark selection and uncertainty.
7. No trading or portfolio allocation automation. Any order-routing feature is out of scope.
8. LLMs may summarize evidence and propose hypotheses, but may not fabricate numeric factors or secretly adjudicate scores.
9. Keep provider terms/licenses and API rate limits; avoid redistribution of restricted datasets.
10. No claim of guaranteed 10x or 'proven alpha'.

## Key research questions
- What patterns were statistically distinguishable **at the time** in eventual 5x/10x/20x+ stocks versus matching controls?
- Which patterns are stable across decades, sectors, capitalization and regimes?
- Which apparent signatures disappear after accounting for base rates and transaction costs?
- What proportion of candidates failed or became untradeable before the potential payoff?
- What changes in fundamentals and narrative coincided with price ignition, and did filings reveal them in time?
- Does a combined signal outperform naïve momentum, simple quality, small-cap benchmarks and random matched controls?
- What actionable *research questions*, not mere buy recommendations, emerge today?

## Deliverables
Working code; CLI; dashboard; data lineage; cohort dataset; reproducible notebooks; model cards; adverse case studies; live candidate watchlist with freshness; 3–5 thesis memos if substantiated; data-gap register; QA evidence; deployment instructions.

## Operational constraints
Prefer Python 3.12+, DuckDB/Parquet, Polars or pandas, PyArrow, pydantic, pytest, FastAPI; React/TypeScript/Vite for front end. Keep provider adapters replaceable. Favor free SEC data for filings and a licensed provider for historical OHLCV/universe/corporate actions. Do not commit keys. Use practical CPU-efficient jobs, caching, provenance and incremental updates.

## Research outcome truth table
- **Data valid, positive out-of-sample:** report measured effect and uncertainty, no promise.
- **Data valid, null/negative:** report falsification and keep useful diagnostics; do not cherry-pick.
- **Data incomplete:** mark inconclusive; do not state discovery success.
- **Only fixture data:** demo behavior, never empirical investment conclusions.
