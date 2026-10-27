# Dated stage policy and history

`discovery-v2-unvalidated` is the default descriptive fixture policy. The earlier
`discovery-v1-unvalidated` remains explicitly selectable for reproducing its 21-session algorithm.
Neither policy has empirical calibration or establishes real investment theses. Download the
frozen policy in Settings and supply it through `baghunter demo --policy <file>`.

## Rules

- WATCH requires basic eligibility and the configured liquidity floor, but lacks a qualifying
  ignition or sufficient maintained-breakout/filing evidence. Missing relative ranks cannot pass.
- IGNITION requires a close strictly above the prior 20- or 60-session high (configured through
  `breakout_lookback`), relative volume at least 1.5, 60-session width at most 0.4, at least 20
  consecutive qualifying base-duration windows and a cross-sectional 63-session rank of at least
  0.8. Duration counts overlapping prior 20-session windows, not independent bases. The first
  qualifying high becomes the original trigger reference and is not moved up with later highs.
- EMERGING requires holding that original reference, positive 21-session return, EMA8 above EMA21,
  positive benchmark-relative 63-session return, and an available filing inflection signal.
  Positive trend without a recorded ignition cannot qualify.
- CONFIRMED additionally requires three prior consecutive active-stage observations with the
  same strength conditions, at least 50% positive-return sector peers (excluding the candidate),
  at least two distinct filing-inflection kinds and evidence from at least two accessions.
  Missing peers or filing evidence never pass. Sector is a fixture proxy, not an industry model.
- EXTENDED/AGING uses configured stretch over EMA21 (0.25) or the original base (0.5). It retains
  the original reference; returning closer to the base does not invent another ignition.
- INVALIDATED records ineligibility/price-floor failure, a close below the original reference,
  or available revenue growth at or below -0.2. Price/filing invalidation takes precedence over
  reduced liquidity. A failed trigger is removed; subsequent advancement needs another ignition.

Thresholds above are defaults, frozen with the policy/digest in each run. They are assumptions,
not optimized or validated choices. Missing price observations produce WATCH with an explicit
reason and do not accumulate a confirmation streak. Unknown sectors do not produce peer breadth.

## Filing evidence

Only known facts after acceptance/publication plus 24 hours are considered. Latest knowable
revisions remain separately cited. The current dataset contract supports annual facts, so the
four possible signals are explicitly annual proxies: positive revenue growth, revenue-growth
acceleration, operating-margin improvement and operating-cashflow-margin improvement. YoY needs
330–400-day ends and positive reference revenue. Margin comparisons require numerator/revenue
from the same period and accession. Overflow produces missing evidence, never a positive signal.

The newest fiscal period must be within `max_filing_age_days` (550 by default); stale periods
produce no growth or inflection signal. Filing ages, availability clocks, kinds and exact input
identities/citations accompany history observations. Operator notes and browser catalyst statuses
are not verified facts and do not enter these gates. Quarterly acceleration and verifiable
catalyst-driven advancement need their own supported dataset evidence.

## Full history

V2 starts with the first possible 121-session observation in the knowable dataset and replays
every subsequent available calendar session through the requested as-of time. Each historical
clock separately restricts bars, facts, identities and cross-sectional peers; no later outcome or
snapshot enters an earlier decision. The archive retains original/evaluated trigger references,
current moving references, rank/duration evidence, filing inputs, transition reason and prices.
Ineligible instruments retain explicit invalidation rows with unavailable price/score, even when
they no longer appear in the current signal list. No history truncation is hidden behind the UI.

Candidate DNA's history explorer pages 20 newest observations at a time, selects any archived
instrument and exports its full history. Older archives keep their declared/legacy window scope.
Current chart markers cover only charted dates; they are not the full archive.

The complete run-bound report is `GET /runs/{id}/reports/stage_history.json` and is stored at
`reports/stage_history.json` in each new immutable run. Its run ID, clock, policy, history scope
and all instrument records match the API download. Legacy windows are labeled as legacy.

Walk-forward evaluation calls a separate ranking snapshot path: its dated score inputs match full
discovery, but it omits stage fields and does not claim history. This avoids replaying the entire
history at every evaluation date. The default public discovery call always retains full history.
