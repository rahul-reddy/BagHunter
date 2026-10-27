# Portfolio allocation comparisons

The fixture simulator now separates ranking (`selector`) from allocation (`allocation`).
`allocation-v1` preserves the legacy `cap_ranked` default and adds equal weight, inverse volatility,
equal-sector targets and cash. These are predeclared software comparisons, with no fitted
parameters, winning-policy selection or empirical investment conclusion.

| Allocation | Requested capital envelope before execution |
| --- | --- |
| cap_ranked | Each dated candidate requests max_position; the legacy rank order fills while cash and sector capacity remain. Requests can sum above capital. |
| equal_weight | 1/N for every dated candidate passing the configured price/liquidity floor |
| inverse_volatility | Normalize reciprocal population standard deviation of daily simple close returns × sqrt(252), over the configured 20 or 60 available returns |
| sector_neutral | 1/G for each available sector, divided equally among its candidates; an equal-sector proxy target |
| cash | Zero stock allocation, no trades, no cash yield |

Inverse-volatility normalization uses min(volatility)/volatility before normalization, avoiding
overflow from computing an unbounded reciprocal. Zero or missing volatility is excluded with
its reason and source evidence, rather than receiving an invented weight. Nonfinite arithmetic
and unrepresentable underflow fail. Known bars must respect both UTC session date and publication
cutoff; duplicates fail. Source IDs, latest publication, observation count and window accompany
the estimate. Raw-price corporate-action effects and missing sessions are not repaired. A window
counts available observations, not elapsed calendar days.

For nonlegacy targets, position caps apply first, then each sector scales proportionally down to
its cap. No capital is redistributed after clipping. The same next-open fills, execution dates,
whole-share rounding, costs, historical dollar-volume participation, price/liquidity floors,
distributions, splits, delist proceeds and daily cash/wealth accounting apply to every variant.
Requested/planned weights are **entry capital envelopes including entry fees**, rather than just
stock notional. Missing entry bars remain unfilled, with explicit exclusions and reserved cash.
Unfilled capital, participation caps and rounding leave cash without increasing other targets.

Equal-sector targets use the sectors available in the dated candidate pool. Blank sectors are
excluded for that variant. Dated benchmark sector weights/industry history are unavailable.
Realized sector envelopes can differ from requested equal-sector targets after position caps,
capacity, rounding or missing entries; subsequent prices can further move sector exposure. The
UI and ledgers show both requested and realized entry weights. This does not establish benchmark
neutrality or a market-hedged strategy. All paths remain long-only with no borrowing.

Default comparisons vary one axis at a time: the other three ranking selectors retain the primary
allocation, and the other four allocations retain the primary ranking. A cash primary omits the
redundant ranking-only cash copies. All other policy values stay identical. Every run retains its
policy, decision/entry/exit rows, target ledger, execution/exclusion ledger, daily curve and risk
metrics, including zero-trade and undefined-risk results. Cash has zero volatility and an
undefined Sharpe when constant; missing risk is not fabricated.

`portfolio.json` retains backward-compatible summaries and full `comparator_runs`.
`portfolio_comparators.json` materializes all comparison runs, served by the read-only run-bound
download. Legacy archives return no new ledgers and retain their old summaries. Validation Lab
provides ranking/allocation comparisons, a decision selector, target and sector tables, risk input
clocks, explicit cash and definitions. No browser job execution or provider credentials are added.

Use the ordinary `uv run baghunter demo` startup to generate the default comparisons. To select
a different primary, supply a local `--portfolio-policy` JSON with `allocation` and optionally
`volatility_window` (20 or 60), alongside the existing caps/costs. Keep all simulation artifacts
under the fixture namespace. See STATUS.md for checks and the PR audit trail for delivery gates.
