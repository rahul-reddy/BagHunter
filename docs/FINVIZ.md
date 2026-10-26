# Finviz Elite data handoff — checked 2026-10-23

The owner has an existing Finviz Elite subscription and authorized a local API export using
FINVIZ_TOKEN from the ignored .env. The export succeeded on 2026-10-23. No purchase occurred.
On 2026-10-26 the owner confirmed Finviz Elite is the only available provider.

## Source-bound observation research

Finviz Observations supports exact reported-sector/country filters, reported-price availability,
minimum current/last-session share volume and maximum positive reported P/E. Filters operate over
the entire verified selected archive before pagination. Missing numeric fields are excluded when
their numeric filter is active; zero P/E is unresolved and excluded from the positive P/E filter.
No market-cap conversion, candidate score, identity decision or eligibility inference is added.

Click a ticker to open its observation research desk. Save/load hypotheses, sources/questions,
falsification conditions, bear arguments and a review date in this browser. Draft keys bind mode,
snapshot and ticker; loading also checks the original CSV checksum. Different snapshots do not
share notes implicitly. JSON dossier export includes the original reported fields, source binding,
limitations and separately labeled user assertions. Source/filter/page changes clear the open desk.
This does not make an observation a permanent security or a verified investment thesis.

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

CSV shape and archived-byte checksum were checked. Market-cap scale, security types, provider
observation timestamps and historical coverage remain unverified. A typed local snapshot importer
is implemented below; it does not activate the dashboard. Export itself remains a local operational
script, not a supported CLI command.

## Verified capabilities and remaining evidence

Finviz describes screener CSV exports and authenticated API workflows in its
[October 7 API announcement](https://finviz.com/blog/our-upgraded-api-higher-limits-clearer-data-and-more-ways-to-connect/).
API setup is under the account profile's **API and Exports** page; the public link redirects to
marketing when unauthenticated. The saved export verifies overview columns and view 111. Other views
and endpoint parameters still require authenticated documentation; do not guess from scrapers.

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

Do not pass CSV directly to
`audit-history`: that command accepts the normalized seven-table JSON bundle described in
[HISTORICAL_IMPORT.md](HISTORICAL_IMPORT.md).

## Import the saved overview CSV

```powershell
uv run baghunter ingest-finviz --csv data/finviz/inbox/screener.csv --manifest data/finviz/inbox/manifest.json --mode EXTERNAL_UNVERIFIED --usage-authorized
```

Only the exact eleven-column unfiltered overview format above is supported. The accompanying
manifest must have the structure of the credential-free local export manifest: provider/source URL,
view 111, empty filters, aware request/retrieval times, null provider observation time, CSV hash,
byte/row counts and columns, plus the unverified status/coverage declarations. Unknown fields,
token-bearing URLs, unsupported parameters and future/naive retrieval clocks are rejected.
The command does not read .env or make network requests. Authorization is an explicit local-use
attestation; FIXTURE and EXTERNAL_UNVERIFIED modes use separate namespaces and snapshot IDs.

Outputs are immutable data/finviz/snapshots/<mode>/<snapshot-id>/ directories containing raw.csv,
source-manifest.json, observations.json, observations.parquet and coverage.json. Repeat ingestion
checks raw/JSON bytes, semantic Parquet values/types and the report, retaining original ingestion time.
The fixed ignored subtree rejects symlink traversal. Publishing stages all files before one rename;
no CURRENT pointer is created. Input caps: 20 MiB CSV, 64 KiB manifest, 100,000 rows, 512 chars/text.

Decimals retain provider scale; explicit Change percentages become fractions. The
[official screener help](https://elite.finviz.com/help/screener) describes Volume as shares traded
today or in the last session. Market-cap export scale remains unverified, so there is no USD
normalization or capitalization-based eligibility. Missing markers (empty, -, N/A) become null.
Zero volume remains zero. Zero reported P/E is retained and counted, without valuation inference.
Ticker duplicates, unexpected columns/ordinals, malformed percentages and nonfinite/invalid numbers
fail closed. Security types remain unknown and permanent IDs remain null.
Numeric inputs support at most eight fractional places and 28 significant digits; values beyond
that precision are rejected before decimal arithmetic can silently round them.

The actual local import has 11,783 observations; missing market cap 5,883, P/E 8,857, price 13 and
change 21. Four reported P/E values are zero. All 11,783 permanent identities remain unresolved.
Snapshot ID: 84f34ecbc902a7c007e448a27afb83b93a7a5483fb1a5be5f48bbb2dac748567.

Store imported observations as unverified current snapshots, separate from the fixture dashboard and
historical research bundles. Do not manufacture membership intervals, accepted filing times, actions,
calendars or historical OHLCV from screener fields. Owner subscription confirmation is not independent
verification of redistribution rights or complete research coverage.

Repeatable supported API ingestion is a later step. Verify account-specific documentation and read
credentials from the local environment without logging authenticated URLs. The API announcement states
a shared account limit of 10 requests per rolling five seconds across Export/API endpoints and
HTTP 429 with `Retry-After: 5`; any client must respect concurrent account usage and bounded retries.
No supported Finviz download client or credential storage is implemented by this increment.

## Local observations browser

The **Finviz Observations** navigation item shows a selected saved snapshot independently of the
fixture run. It has search across ticker/company/sector/industry and alphabetical pagination, not
candidate scores, historical profiles or eligibility decisions. Missing values stay visible and zero
reported P/E is marked unresolved. Price and market cap display provider-reported scale without USD
formatting. Unknown types/IDs remain unknown; a sector, industry or missing capitalization is not
evidence that an observation is a common share or fund.

Official screener help was checked again on 2026-10-23. It defines field meanings but does not
establish this CSV's capitalization scale or permanent security identity. The authenticated API
documentation still redirects to marketing without a browser login. Those gaps remain unresolved;
the informational browser exposes them rather than promoting data into research inputs. Historical
research and common-stock eligibility remain blocked on the missing evidence.

Run from the repository root, after ingesting the local export:

```powershell
$env:BAGHUNTER_FINVIZ_SNAPSHOT='84f34ecbc902a7c007e448a27afb83b93a7a5483fb1a5be5f48bbb2dac748567'
$env:BAGHUNTER_FINVIZ_MODE='EXTERNAL_UNVERIFIED'
uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal with `npm --prefix apps/web run dev`, open
http://127.0.0.1:5173 on this computer and choose Finviz Observations. These environment variables
select a local archive, not a credential. Do not put the token in browser configuration. For fictional
test archives only, mode FIXTURE displays a prominent synthetic label. There is no fixture fallback
when an external snapshot is missing or corrupt. No snapshot is selected automatically.

GET /finviz/observations accepts q (at most 100 characters), offset (0–100,000) and limit (1–100;
default 50). Every read verifies the bounded original CSV/manifest, snapshot identity, derived JSON,
Parquet values/types and coverage report. It never imports, repairs or writes data. Invalid selection,
symlinks and corruption fail closed with a generic 503 response. A missing fixture run does not block
this endpoint or browser. No network calls, automatic download or refresh of vendor data occur.

Retrieval age is displayed; 24 hours marks a saved snapshot stale. This is a local age threshold,
not proof of provider quote freshness: provider observation time remains unknown at every age.
Responses are paginated, and changing a query or failing a reload removes old displayed rows.
Reported decimals, exact percentage text and share volumes are sent as strings to avoid browser
rounding of large integers; counts and retrieval ages remain numeric.
Percentage values are numerically exact; insignificant trailing zeros may be normalized for display.
Original lexical formatting is retained in the raw CSV, not guaranteed in the displayed percentage.
The licensed dataset stays under Git-ignored data/ and is served only by the configured local API.
Bind to localhost; no public hosting or redistribution is configured or authorized by this feature.

Current identity evidence can now be queried through the bounded [OpenFIGI reference adapter](REFERENCE.md)
and inspected in this page's reference panel. Its candidates do not resolve the original observations'
identities automatically. Next: reconcile company/share-class evidence before any current identity
promotion. Export-unit evidence and historical membership remain separate unmet gates.
