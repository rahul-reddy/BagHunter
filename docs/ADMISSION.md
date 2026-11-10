# Dated admission and comparator availability

Portfolio policy JSON supports optional `min_capitalization_usd`,
`max_capitalization_usd` and `max_annualized_volatility_20d`. Null disables each
bound; zero is an explicit bound. Capitalization requires an explicit finite USD
observation with observed, published and expiry clocks, source and security IDs.
The default maximum age is five UTC calendar days. Conflicts, expired records and
future publications are unavailable. Current Finviz reported market-cap values
are never converted or backdated without established units and source evidence.
The twenty-return population volatility is annualized using sqrt(252); missing
history does not satisfy a configured ceiling. Every exclusion and accepted target
retains admission evidence. These are fixture simulation controls, not order gates.

`earnings_growth` ranks dated `annual_net_income` USD facts after the configured
filing processing lag (at least 24 hours). It requires adjacent annual periods
(330–400 days), a positive prior denominator and a current period no older than
550 days by default. Latest knowable revisions are used; conflicting latest values,
unsupported units and stale or missing pairs remain unavailable. Revenue growth
and quarterly income are separate inputs and cannot substitute for annual earnings.

The saved `comparator_catalog.json` lists every predeclared ranking/allocation
attempt. The default fixture has no annual earnings pairs: that comparison retains
`UNAVAILABLE_DATED_ANNUAL_EARNINGS` and null metrics, alongside seven available
fixture reports. It is not presented as a zero-return cash result. Validation Lab
shows and downloads the catalog. Older archives retain an explicit unavailable
catalog; their missing attempts are not reconstructed.

Normalized historical bundles may include a checksum-listed `market_caps.json`
array using the capitalization observation schema. It is bounded to 100,000 rows,
requires known instrument/source IDs and publication no later than retrieval, and
archives original bytes plus Parquet in quarantine. Omitting it reports
`DATED_USD_CAPITALIZATION_MISSING`. Import does not activate external observations
for fixture research or promote identity/evidence claims.
