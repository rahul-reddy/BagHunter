# Descriptive historical event paths

`calendar-event-paths-v1` declares quarter-start anchors from a bounded synthetic weekday
calendar, before computing outcome groups. The calendar spans the stored fixture's first/last
price session and includes exchange holidays; it is not an exchange calendar. Offsets are fixed
at −120, −60, −20, 0 and +20 synthetic weekdays. The first partial quarter, if any, starts at the
first fixture weekday in the source range. Calendar bounds and a date-list digest are archived.
This is a declared software policy, not an external preregistration or untouched empirical study.

All common instruments eligible by dated first/last-seen identity at each anchor remain in its
denominator. Benchmark instruments are excluded. This diagnostic cohort does not apply the Radar
price/liquidity floors. Every member's points are constructed before any outcomes are consulted.
`path_snapshot` accepts only one instrument, prices, facts, symbol history and its clock; it
cannot accept labels, corporate actions, case/control roles or other point vectors.

Each available point has an independent UTC clock at 23:00, exact-session quote publication
check, 121-observation minimum, known symbol, past-return/price/volume metrics, dated technical
catalog, statement ratios, citations and latest included source publication. Financial processing
lag is 24 elapsed UTC hours after acceptance/publication. Shared cutoff/revision sorting and
fact timeline validation now compare UTC instants: changing offsets or a repeated local hour
cannot shorten the lag, reverse revisions, or hide publication before acceptance. No later point, anchor close or outcome normalizes
earlier feature values. Raw close paths can contain corporate-action effects. Discovery scores
and stages are deliberately absent: these are price/fundamental vectors, not a reconstruction of
the separate bounded-history discovery stage policy.

Missing points retain explicit states: outside calendar, ineligible at the point, no quote
available by that point, or insufficient historical prices. No prior close or later filing is
substituted. Delisted peers stay in the anchor cohort and retain their realized outcome label;
a later ineligible/missing point remains missing. Incomplete horizons stay in the denominator.

After all vectors exist, independent wealth-path outcomes assign retrospective maximum-hit case,
noncase and missing groups. The configurable horizon is 1/2/3/5 years and threshold 1–100×.
Maximum attained multiples remain distinct from terminal holding return and drawdown. Seeded
controls use the same dated anchor, sector/cap/liquidity/price strata and actual selected horizon
and threshold. Sector is a fixture industry proxy. Control probability/weight and unmatched cases
remain explicit; matched selection is not a population probability or causal estimate.

Every t+20 point is post-anchor descriptive hindsight. Even earlier vectors in this retrospectively
grouped report stay outside predictor assembly. JSON/Markdown reports and `hindsight/event_paths.parquet`
hold the diagnostic; gold feature Parquet receives no event-path/outcome fields. The read-only
run-bound downloads use archived data, including original policy fingerprints. Legacy archives
return no fabricated event study. Resource limits reject more than 32/duplicate instruments,
64 anchors, 2,048 points, a span over 6,000 days or non-weekday observations; no silent truncation.

The fixture currently yields 17 anchors, 240 member points and one matched 1Y/5× pair, with early
missing vectors, missing horizons and a delisted peer. These are artificial paths, not real
historical research. Capital raises, customer concentration, TAM, valuation and narrative company
evolution still need primary-source evidence and the remaining qualitative workflow.

Run `uv run baghunter demo --event-policy examples/event-policy.json` and open the 100-Bagger
Museum. Select an anchor/pair or an unmatched cohort member, a metric and a point for citations.
Charts break at missing points and visibly distinguish post-anchor hindsight. JSON and Markdown
downloads are source-run bound. Policy content participates in the immutable run/cache key; changing
only the threshold creates another run while the underlying dated vectors remain identical.
The ordinary demo uses the same default policy and CLI seed; no browser action launches a job.

Validation evidence is recorded in STATUS.md and delivery gates in the PR audit trail. Final
software completion still requires the remaining specification work in REMAINING_REQUIREMENTS.md.
