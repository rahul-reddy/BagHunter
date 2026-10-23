# Research method / glossary

- **As-of**: decision clock in UTC. Only bars already available and facts published/accepted plus a
  conservative 24-hour processing lag can enter a feature. Period end is never a publication date.
- **Revision**: accession-specific immutable fact. The newest knowable revision per period is selected;
  future amendments never overwrite history. The fixture currently supplies annual revenue only.
- **Permanent ID**: security identity independent of ticker. Symbol intervals are half-open and ambiguous
  or missing mappings fail. No assumption that a reused ticker denotes the same firm.
- **Max multiple**: largest future wealth / anchor wealth within a prespecified horizon.
- **Terminal total return**: terminal wealth / anchor wealth minus one. Cash dividends are held without
  reinvestment, splits multiply shares; delisting proceeds are per share. Return methodology is labeled.
- **Missing outcome**: a horizon without complete history is null, never a zero or a silently dropped row.
- **Cohort**: closed fixture universe at a predetermined anchor; does not require future survival.
  One-year 5× max-hit cases are paired with date/sector/cap/liquidity/price-bucket noncases using seed 7.
  Buckets are fixture metadata, not derived empirical market caps; sampling weights are recorded.
- **Score**: fixed placeholder weighted sum with missing factors retaining null. Available weights are
  not rescaled. Coverage measures available factor weight, not confidence or calibrated probability.
- **Walk-forward toy**: fixed 63-session momentum, no learning/tuning, disjoint holding windows and
  explicit next-open fills. Costs are 20 bps entry + 20 bps exit, subtracted as 0.004 of entry notional.
  Unresolved exits are flagged. Fixture universe capacity and sector diversification are not modeled.

Features implement 1/5/21/63-session momentum, 8/21 EMA, 60-session base width, relative volume,
20-session dollar volume and knowable annual-revenue growth. Relative strength, industry breadth,
quality, valuation and catalyst factors remain missing. No feature assembler accepts outcome labels.

The fixture is constructed to exercise success and failure paths, so its return differences are
tautological software demonstrations. No hypothesis, hit rate, significance or investment inference
is established. A real study requires licensed PIT membership, as-of share counts, original filings,
delist history, independent controls, chronological splits, horizon-based purge/embargo, clustered
uncertainty, negative controls and a registered untouched holdout before predictive claims.
