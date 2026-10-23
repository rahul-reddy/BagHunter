# Finviz Elite data handoff — checked 2026-10-23

The owner has an existing Finviz Elite subscription and authorized a local API export using
FINVIZ_TOKEN from the ignored .env. The export succeeded on 2026-10-23. No purchase occurred.

## Completed local export

An unfiltered overview request (view 111) to the official Elite export endpoint redirected from
/export.ashx to /export on the same HTTPS host and returned HTTP 200 text/csv. Redirects were limited
to Finviz HTTPS hosts; authenticated URLs and response rows were not printed or committed.

The original CSV and credential-free manifest are in ignored data/finviz/inbox/20261023T175717Z/;
convenience copies are data/finviz/inbox/screener.csv and manifest.json. Retrieval time was
2026-10-23T17:57:17.673674+00:00. The 1,320,890-byte CSV has 11,783 unique, nonempty tickers and
11 columns: No., Ticker, Company, Sector, Industry, Country, Market Cap, P/E, Price, Change, Volume.
SHA-256: 148ad7a687652508a6c5425df40def965ad90d76ea3ccf02a65b56ca850a9c05.
These counts describe the export, not a verified common-stock research universe.

CSV shape and archived-byte checksum were checked. Units, security types, provider observation
timestamps and historical coverage remain unverified. No typed importer or dashboard activation
has occurred. The export procedure remains a local operational script, not a supported CLI command.

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

## Manual alternative for later exports

1. In the owner's existing Finviz Elite session, open the desired stock screen and export CSV.
   Include ticker/company and, where offered, sector, industry, capitalization, price and volume.
   Missing fields remain missing; these are requested fields, not a verified column contract.
2. Save the original file under `data/finviz/inbox/screener.csv` in this checkout. The root `data/`
   directory is Git-ignored. Keep licensed observations local; do not add them to the public repo.
3. Alongside it, record the actual export time with timezone, filters, selected columns, and any
   provider timestamp/delay/adjustment notes. Do not backdate export time to a fiscal period.
   Exclude token-bearing links, passwords, account identifiers and cookies from notes.
4. Tell the agent the local file path. No password or API key is required for CSV inspection.

This is an export handoff, **not an implemented Finviz importer**. Do not pass CSV directly to
`audit-history`: that command accepts the normalized seven-table JSON bundle described in
[HISTORICAL_IMPORT.md](HISTORICAL_IMPORT.md).

## Next implementation using the saved export

Inspect headers and units before writing the converter. Preserve original bytes and their hash,
record ingestion time separately from provider observation time, validate finite numbers and missing
markers, and reject ambiguous duplicate observations. Keep ticker observations separate from resolved
permanent identities. Test with fictional CSV rows shaped like the export; never commit vendor rows.

Store imported observations as unverified current snapshots, separate from the fixture dashboard and
historical research bundles. Do not manufacture membership intervals, accepted filing times, actions,
calendars or historical OHLCV from screener fields. Owner subscription confirmation is not independent
verification of redistribution rights or complete research coverage.

Repeatable supported API ingestion is a later step. Verify account-specific documentation and read credentials
from the local environment without logging authenticated URLs. The official API announcement states
a shared account limit of 10 requests per rolling five seconds across Export/API endpoints and
HTTP 429 with `Retry-After: 5`; any client must respect concurrent account usage and bounded retries.
No supported API client or credential storage is implemented by this documentation change.
