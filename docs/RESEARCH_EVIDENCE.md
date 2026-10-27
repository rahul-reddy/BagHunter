# Source-bound qualitative research and critique

Open a saved Finviz observation's research desk. The structured workspace adds dated qualitative
evidence, cited peer comparisons, a time-to-thesis assumption, milestone conditions, opportunity
cost and a separately attributed critic. It works independently of the fixture ranking feed.
Nothing entered here becomes a predictor, verified identity or verified investment thesis.

## Evidence and clock

Record industry catalysts, customer concentration, products, contracts, management incentives,
moat, narrative saturation, capital raises, market-size assumptions and sector cycles. Tag each
entry as a primary-source transcription, human judgment, LLM judgment or assumption. Include
author/model attribution, a primary HTTPS citation, exact publication timestamp and a condition
that would disconfirm it. Missing sources remain incomplete; future publications are flagged.
Even a fully cited transcription is not independently verified by this application.

The research clock defaults to the actual session time and remains editable. It cannot precede
the selected Finviz retrieval or attached SEC retrieval/financial clocks when saving or exporting
combined research. This does not certify a historical PIT profile; original source clocks remain
separate. Dates require timezones, valid calendar dates and at most nine fractional-second digits.
Comparisons normalize offsets and retain submillisecond precision rather than rounding a future
source down into the current clock. Unknown dates are not guessed.

## Peer comparisons and assumptions

Enter company, reported P/E or EV/revenue or EV/operating-earnings multiple, denominator period
basis, reporting currency, dated primary source and a comparability rationale. Exact metric,
period-basis and currency groups stay separate; no conversion or automatic peer selection occurs.
Missing details, future sources and zero multiples are excluded with reasons. Negative, nonfinite
or malformed multiples reject. The bounded range is zero to 1,000,000; each workspace holds at most
50 peers and 50 qualitative entries. Original input strings/citations remain in exports.

`peer-comparisons-v1` reports count/minimum/median/maximum. Among otherwise eligible contemporaneous entries, repeated normalized company names in
the same comparison group are all excluded, so the same company is not silently double-weighted.
Normalization here only ignores case/whitespace; it does not assign security identities. One peer
is one comparison, not a representative valuation band. User transcriptions and selected sample
ranges do not establish fair value or the observation's currency/share class.

Time to thesis is an explicit 1–120-month assumption, with milestone/falsification conditions.
Opportunity-cost text records alternatives and unresolved comparisons. These fields do not create
price forecasts, probabilities, discount rates or expected benchmark returns.

## Separately attributed critic

1. Enter the primary research author, evidence and assumptions. Export the separate critic request.
2. Give that JSON packet to a different human or model. The app makes no model/network calls for
   critique. The packet contains its complete source-bound context and a response schema.
3. Paste the returned JSON into the critic response field and attach it. Include reviewer identity,
   human/LLM tag, counterargument, evidence gaps, falsification and dated primary citations.

A canonical SHA-256 fingerprint binds source/snapshot identity, selected SEC evidence, notes,
scenario inputs/results and structured research. Nonfinite or non-JSON request values reject.
Different reviewer attribution is required; case/whitespace variants of the primary author do not
pass. The app cannot prove reviewer identity, independence or factual correctness. A matching
review is labeled as such, with independence explicitly unverified. Missing/future critic sources
remain flagged. Changing any bound input makes the review stale; old text stays inspectable but
is not presented as a current review. A bear note or independent code review does not fill this step.

## Save, load and export

The existing mode/snapshot/ticker local-storage key remains. New records use
`observation-research-v3`; old notes/v2 records remain readable. V3 validates source context, exact
CSV checksum, typed bounded records and clocks. Loaded SEC archives reverify and scenarios need
recalculation; the saved issuer, rather than an unrelated current selection, supplies final clock
validation after load. Invalid source verification disables combined exports and critic attachment.

JSON dossiers and Markdown memos retain qualitative tags, source clocks, raw peer records and
exclusions, horizon/opportunity-cost assumptions, critic attribution/status and citations. A stale
review stays explicitly stale in both formats. Browser storage remains local; exports are explicit.
No provider requests, model spending, security promotion or deployment is triggered.
