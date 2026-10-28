# Current-observation company research

Finviz Observations → choose a saved snapshot → **Research observation** opens a source-bound
desk. Notes, selected SEC archive ID and scenario input strings can be saved locally. This works
independently of the fixture screening run. No action starts provider downloads.

## Separate evidence and assumptions

For an external observation, choose a saved SEC entity archive explicitly. The API revalidates
original source bytes, derived historical metadata and normalized facts. The desk checks archive,
entity key and clock before showing annual/quarterly evidence. Current filer name/tickers/exchanges
come only from the verified original submissions response, with retrieval time/hash and bounded
display fields. Missing/unsupported metadata remains unavailable. Current fields are not historical
identity evidence or a security/share-class assignment.

The selection is an operator research association. It never approves a Finviz-to-CIK mapping,
assigns a permanent ID, creates a score or activates predictors. Changing/reloading a source clears
old evidence/results; failed verification disables combined exports. Late responses cannot replace
newer selections. Fixture observations cannot attach real SEC evidence.

Annual/quarterly tables retain dated citations and source limits. **Use selected SEC annual revenue
as an assumption** copies only that entity's annual revenue at the user's request. Shares, net debt,
reference price, growth, margin, multiple and dilution remain user inputs; horizon defaults to
three years. Finviz prices/caps are not converted to USD and weighted shares are not class shares.

Bear/base/bull use the bounded `/scenario` arithmetic. Bear subtracts ten growth percentage points,
five margin points and five multiple turns (floor zero); bull adds the same amounts. Exact case
inputs accompany results/exports. Unsupported cases fail without retaining stale calculations.
Net debt is constant; negative net debt is a net-cash assumption. No probability, discount-rate,
financing, tax or dividend model is implied. Modeled per-share values are not price forecasts.

## Persistence and reports

The existing per-mode/snapshot/ticker key is preserved. New v2 records additionally bind the CSV
checksum and explicit source context. Old notes-only records remain readable. Corrupt dates,
unknown schema, malformed source IDs/assumptions or context mismatch reject. Loaded archive IDs
must reverify; saved inputs require recalculation. Facts/results are not silently loaded from
browser storage. Notes stay private to that browser until explicitly exported.

**Export observation dossier** produces JSON with separate Finviz provenance, user notes, verified
selected-entity evidence, assumption strings and only current calculations. **Export observation
research memo** produces Markdown with questions, falsification/bear notes, dated citations, full
scenario inputs/outputs, independent source clocks and limits. Both retain USER_ASSERTIONS and
UNVERIFIED status. No draft changes the verified-thesis count. Snapshots have separate drafts.

Tests cover calculator responses, context binding, reload/recalculation, failed evidence, late
responses, legacy notes, export content and desktop/mobile accessibility. Current gates: STATUS.md.

Structured source categories, cited peer comparisons, horizon/opportunity-cost assumptions and
separately attributed critic packets are documented in [Research evidence](RESEARCH_EVIDENCE.md).
New v3 records preserve the existing storage key and read older records. These additions do not
verify an investment thesis or activate research predictors.
