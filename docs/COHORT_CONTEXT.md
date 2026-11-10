# Dated industry matching and benchmark cohort context

Industry classifications have permanent security ID, exact industry label/taxonomy version,
source ID, half-open validity dates and publication timestamp. An assignment enters a matching
query only after publication and during its validity interval. Immutable revisions are selected
within the same source/taxonomy/validity interval; conflicting known sources or overlapping
classifications remain ambiguous instead of choosing a convenient current label.

Where the case has a known dated classification, controls must have the same known taxonomy and
industry plus the declared cap/liquidity/price strata. A current sector match cannot override a
different dated industry. Ambiguous cases/controls are excluded; missing case classifications use
an explicitly recorded sector proxy. Seeds, sampling probabilities, matching basis and each side's
publication/source context are archived. Unknown industry is never inferred from current Finviz.

The fixture supplies three explicitly fictional industry assignments. They test dated mechanics,
not real GICS classifications or original reference vintages. `silver/industry_history.parquet`
retains them separately; the source Dataset checksum covers the records.

The multi-anchor cohort grid also records a dated benchmark proxy. It requires exactly one as-of
listed benchmark, the anchor price and 64 consecutive fixture-weekday observations known at the
anchor. The sign of the 63-session raw-price return defines UP_63D, DOWN_63D or FLAT_63D. Missing,
stale or ambiguous history is UNAVAILABLE, never flat/zero. This proxy does not measure macro
regimes, adjusted total return or representative small/microcap benchmarks.

Museum filters archived regimes and sectors, including all-anchor views. Repeated securities and
overlapping horizons are correlated observations, not independent companies or population base
rates. Legacy archives show unavailable context without reconstruction. Dated industry/source
clocks remain in case reports and full cohort downloads; no outcome column enters predictors.

Normalized history bundles may optionally include checksum-listed `industry_history.json`.
The v3 importer validates its IDs, source binding, publication/vintage clocks and bounded shape,
retains raw/Parquet records in quarantine and exposes a publication-cutoff query. Seven original
required tables remain supported unchanged. Current classifications cannot be silently backdated;
source vintages and empirical identity/industry coverage still require independent evidence.
