# Research model and acceptance boundaries

BagHunter's shipped research feed is an inspected synthetic fixture, not a fitted investment
model. The three fictional common shares and fictional market comparator cover weekday prices
from 2019-01-01 through 2023-03-30. The default research clock is 2022-01-03 23:00 UTC. The legacy
toy has 13 independent windows from decisions 2019-12-31 through 2022-01-05; the constrained
simulation uses its separately exported decision/entry/exit ledger. No fixture is untouched.

## Discovery

`DiscoveryPolicy` freezes six component weights, liquidity/price floors and stage thresholds.
Weights sum to one; missing components retain their unavailable weight rather than boosting
available factors. Coverage is covered weight, not confidence. Unknown quality, valuation and
catalyst evidence must stay missing. Stages use a 21-session history initialized at WATCH and
dated information only. The defaults and score ranges are unvalidated heuristics.

The sensitivity report holds dated factors fixed and explicitly compares frozen weights, equal
factor weights, price/volume only, fundamental inflection only and two stricter liquidity floors.
It reports changed ranks, covered weight and excluded observations. It neither fits a policy nor
measures its future performance. Stable ranks in a tiny fixture establish no robustness result.

## Historical outcomes

Hindsight labels are separately materialized for multiple anchors, 1/2/3/5-year horizons and
5x/10x/20x/100x maximum-hit thresholds. Maximum hits differ from holding returns. Incomplete
horizons remain null and in eligible denominators. Matched retrospective controls do not estimate
population base rates. Predictors never accept the outcome-label table as an input.

## Validation and simulation

Chronological 60/20/20 partitions with purge/embargo are a design diagnostic on previously inspected
fixtures. No trained classifier, calibrated success probability, untouched holdout result,
multiple-decade study or statistically established excess return is shipped. Classification
precision/recall/calibration would require a defined model and representative real labeled data.

The long-only constrained simulation uses next-open entry, whole shares, cash, position/sector caps,
prior known dollar-volume participation, fixed assumed one-way costs and explicit corporate actions.
Missing exits or held-session marks reject. Dividends remain cash; no reinvestment, leverage,
borrowing, shorting, financing costs or broker transmission. Corporate-action proceeds and terminal
equity reconcile. Market impact and actual spread/capacity are not calibrated.

Daily-close drawdown excludes intraday extrema. Annualized volatility/Sharpe/Sortino assume 252
sessions, zero risk-free rate and zero target return. Calendar-day CAGR uses the exported dates.
Equity exhaustion and zero variance leave undefined ratios explicit. The artificial weekday
calendar is not a US-exchange calendar. Window-end metrics are separately labeled. Comparator
policies cover 12–1 momentum, dated revenue growth and seeded random ranking with common constraints.
Real small/microcap total-return benchmarks and earnings-quality tests need unavailable history.

## Real observations and narratives

The owner has Finviz Elite only. Saved current observations remain separate from fixture research.
Sector/country/volume/positive-P-E filters are reported-field queries, not common-stock eligibility
or a candidate ranking. Unknown permanent identities, price currency/adjustments, market-cap scale,
provider observation timestamps and historical continuity remain unresolved.

SEC normalization accepts local accession-bound annual USD facts under documented lag/amendment
rules, but output remains quarantined. Original extraction vintages, real identity verification,
quarterly/YTD interpretation and custom taxonomies are not certified. No contact is invented.

Thesis scenarios are explicit user arithmetic with no probabilities or forecasts. Notes, source
citations, catalysts and bear arguments are operator assertions. Calendar status changes do not
verify them. Independent code review is not an investment-committee review of a thesis.
**Zero real investment theses are verified.** No minimum pick count is forced.

## Required evidence before empirical acceptance

Licensed PIT universe and dated membership; action/adjustment/delist coverage including failures;
verified class/permanent identities and provider units; original filing/publication vintages;
representative controls and benchmarks; frozen protocol followed by a truly untouched real holdout;
independent factual critique. Until then, research conclusions are inconclusive.
