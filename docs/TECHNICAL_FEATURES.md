# Dated technical evidence

`technical-evidence-v1` computes diagnostic fields from raw bars with session date and
publication at or before the UTC research clock. Duplicate known sessions fail. Other identities,
future sessions and delayed publications are excluded. No outcome labels enter this interface.
The catalog is attached to discovery signals, gold feature Parquet, candidate profiles and the
run-bound `technical_evidence.json` report; API downloads use archived values without recomputing.
Legacy runs keep their original values and display an unavailable catalog.

| Field | Definition / minimum history |
| --- | --- |
| SMA20/50/200 | Arithmetic mean of the last N available closes; N observations |
| EMA8/21 | Recursive EMA with alpha 2/(N+1), initialized at the first available close |
| Prior high20/60/120 | Maximum high of the preceding N observations, excluding current; N+1 observations |
| High distance / breakout | Current close / prior high − 1; breakout is strictly greater, equality is false |
| Volatility20/60 | Population standard deviation of N daily simple returns × sqrt(252); N+1 observations |
| Contraction | Volatility20 / volatility60; zero reference volatility is explicitly missing |
| Opening gap | Current open / previous available close − 1; two observations |
| Mean absolute gap20 | Mean absolute opening gap over the latest 20 transitions; 21 observations |
| ATR20 | Mean max(high−low, abs(high−previous close), abs(low−previous close)); 21 observations |
| Base duration | Consecutive prior 20-observation rolling windows with high/low−1 no greater than the configured max_base_width; current bar excluded |

Base counting stops at the first nonqualifying window, known history or a 252-window cap. If all
examined windows qualify, `base_left_censored=true` and the count is a lower bound, including when
the cap is reached. A known failing first window yields zero; fewer than 21 observations yields
missing. This diagnostic is distinct from the existing 60-session base-width stage rule. Counts
refer to observations, not elapsed trading days. Raw prices may contain corporate-action effects;
no adjustment, missing-session repair or source-vintage promotion is implied. Nonfinite derived
arithmetic fails before ranking or publication. Missing reasons are explicit field/reason records.

`cross-section-evidence-v1` uses the same clock's eligible known common equities with sufficient
history **before** price/liquidity filters. The benchmark is excluded. Percentile rank is
`(number strictly below + (number tied − 1)/2)/(N−1)`; one-name ranks are missing. Sector-relative
63-day return subtracts the mean of **other** members of the reported sector. Participation is the
fraction of the entire sector group with positive 21-day return. Dispersion is the population
standard deviation of 63-day returns. Single-member participation/dispersion are missing. Blank
sector metadata has no group. Per-signal reference identities, price sessions, clocks, latest
included price publications and source IDs identify the denominator's inputs.

Sector is a declared proxy: dated industry membership is unavailable. None of these additional
diagnostics changes score weights or stage thresholds. The existing heuristic policy stays
`discovery-v1-unvalidated`. Adding a base-duration or relative-rank ignition gate still requires
an explicit versioned policy change; the present catalog does not claim that requirement complete.
Fixture tests establish software arithmetic and availability, not empirical efficacy or real
market calibration. Finviz current snapshots are not silently converted into price histories.

Run `uv run baghunter demo`, start the API/web app per README, and open a Candidate DNA profile.
The dated technical panel shows values, formulas, missingness and an immutable run download.
Current validation and independent review evidence is recorded in STATUS.md.
