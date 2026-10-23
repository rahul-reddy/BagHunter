# 05 — Independent validation, backtesting, and risk

## Strategy claims versus research claims
The dashboard is a research discovery tool. An apparent signal does not imply executable excess return. Maintain separate evaluations of **prediction** (future outcomes) and **portfolio performance** (tradable returns).

## Backtest protocol
- Define research question, universe, eligible observation times, training period, validation period, true holdout and benchmark *before* evaluation.
- Walk-forward rebalance at predetermined cadence; all features/capitalization/eligibility as of decision time. Account for earnings/filing delay and execution after signal formation.
- Handle overlaps for 1–5-year forward outcome labels with purge/embargo, not random row splitting.
- Record stock splits, distributions, symbol changes, delist proceeds and worthless securities. Do not silently drop bankruptcies.
- State trading assumption: next open/VWAP/close as appropriate, explicitly conservative and availability justified. No same-close fill using same-close signal without trade latency.
- Restrict by historical dollar volume, price, volatility and market cap. Apply participation caps and minimum tradable lot assumptions.
- Include commissions/fees, bid-ask spread, market impact, borrow costs if ever shorting (default long only), and margin financing if modeling leverage (default none).
- Limit per-position and sector concentration; compare equal weight, volatility/risk scaled and cash-aware baselines.
- Mark unresolved instruments untradable rather than force optimistic fills.

## Primary metrics
CAGR, total return, annualized volatility, Sharpe/Sortino with stated risk-free assumption, maximum drawdown, turnover, concentration, hit rate, payoff ratio, downside tail, skewness, recovery time, worst cohort, liquidity capacity. For classification: precision/recall at specified budget, 5x/10x hit rates, absolute base rates, false positives, lift, calibration and confidence intervals. Include number of observations and data coverage per period.

## Independent comparators
- Broad-market total return (e.g. appropriately dated US benchmark).
- Small-cap and microcap proxies consistent with the tested universe.
- Basic 12–1 momentum, relative strength + minimum liquidity, simple earnings-growth quality and random matched portfolios.
- Sector-neutral variations and date-matched controls.

## Failure-oriented robustness
1. Different decades, rate environments and market regimes.
2. Excluding highest-contribution name and sector.
3. Wider slippage; reduced position sizes; longer data-publication lag.
4. Higher dollar-volume cutoffs and exclusion of microcaps.
5. Delisted securities included; alternate delist handling sensitivity.
6. Alternate price adjustment and return metric where economically justified.
7. Feature ablations, penalty for missing data, alternate model weights.
8. Paired/bootstrap intervals clustered by time; multiple testing audit.
9. Negative controls such as permuted date-safe labels and lagged irrelevant features.
10. Walk-forward holdout from an untouched period with frozen configuration.

## Risk register fields
Liquidity; dilution and ATM offerings; customer concentration; refinancing; accounting quality; binary catalysts; insider/promoter incentives; governance; momentum crowding; industry cycles; technology obsolescence; macro rates; data/vendor limitations; regime drift; backtest overfitting; source licensing.

## Output rubric
For every strategy show actual periods, universe construction, transaction-cost version, data-coverage exclusions, validation methodology, whether sample is fixture/demo, uncertainty and limitations. Never optimize a 10x outcome label against recent hindsight winners and report that as independent predictive power.
