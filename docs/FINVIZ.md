# Finviz Elite data handoff — checked 2026-10-23

The owner has an existing Finviz Elite subscription. No export, API token or authenticated
documentation has been supplied to BagHunter. No subscription purchase is needed for this handoff.

## Verified capabilities and remaining evidence

Finviz describes screener CSV exports and authenticated API workflows in its
[October 7 API announcement](https://finviz.com/blog/our-upgraded-api-higher-limits-clearer-data-and-more-ways-to-connect/).
API setup is under the account profile's **API and Exports** page; the public link redirects to
marketing when unauthenticated. Endpoint parameters and actual export columns still need inspection
from the owner's export or authenticated documentation; do not guess them from third-party scrapers.

The [official FAQ](https://elite.finviz.com/help/faq) says fundamentals update with recent information
and that Finviz cannot sell raw historical data to third parties. The
[Elite feature page](https://finviz.com/elite) also advertises price exports and eight years of
financial statements. These statements do not establish original publication vintages, an archived
historical universe, delisted-security coverage, action adjustments or terminal proceeds.
The FAQ does not by itself prove that every available price export lacks history.

BagHunter's decision: use Finviz first as a source of **current screener observations**.
Historical research eligibility remains unverified. Historical fiscal periods in today's financial
statements must not be interpreted as facts known at those past dates. A ticker is not a permanent
security ID, and today's selected screen is not the past investable universe.

## Next input: one local CSV export

1. In the owner's existing Finviz Elite session, open the desired stock screen and export CSV.
   Include ticker/company and, where offered, sector, industry, capitalization, price and volume.
   Missing fields remain missing; these are requested fields, not a verified column contract.
2. Save the original file under `data/finviz/inbox/screener.csv` in this checkout. The root `data/`
   directory is Git-ignored. Keep licensed observations local; do not add them to the public repo.
3. Alongside it, record the actual export time with timezone, filters, selected columns, and any
   provider timestamp/delay/adjustment notes. Do not backdate export time to a fiscal period.
   Exclude token-bearing links, passwords, account identifiers and cookies from notes.
4. Tell the agent the local file path. No password or API key is required for CSV inspection.

This is an input handoff, **not an implemented Finviz importer**. Do not pass CSV directly to
`audit-history`: that command accepts the normalized seven-table JSON bundle described in
[HISTORICAL_IMPORT.md](HISTORICAL_IMPORT.md).

## Implementation after the export arrives

Inspect headers and units before writing the converter. Preserve original bytes and their hash,
record ingestion time separately from provider observation time, validate finite numbers and missing
markers, and reject ambiguous duplicate observations. Keep ticker observations separate from resolved
permanent identities. Test with fictional CSV rows shaped like the export; never commit vendor rows.

Store imported observations as unverified current snapshots, separate from the fixture dashboard and
historical research bundles. Do not manufacture membership intervals, accepted filing times, actions,
calendars or historical OHLCV from screener fields. Owner subscription confirmation is not independent
verification of redistribution rights or complete research coverage.

Automated API access is a later step. Verify account-specific documentation and read credentials
from the local environment without logging authenticated URLs. The official API announcement states
a shared account limit of 10 requests per rolling five seconds across Export/API endpoints and
HTTP 429 with `Retry-After: 5`; any client must respect concurrent account usage and bounded retries.
No API access or credential storage is implemented by this documentation change.
