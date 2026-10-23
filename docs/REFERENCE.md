# Current reference evidence — OpenFIGI

This increment gathers **current mapping candidates**, not a historical security master. A ticker
can be reused; the provider's present name/type/FIGI does not establish identity at an older Finviz
observation time. No Finviz security_id/security_type, research universe, score or historical table
is changed. Name and share-class reconciliation remain unverified even for one returned candidate.

## Source and bounded public access

The [official OpenFIGI API documentation](https://www.openfigi.com/api/documentation) describes a
public, free mapping API, including unauthenticated access. No signup, purchase or API key was used.
Only public tickers and US/equity request context are sent; no Finviz prices, companies, credentials,
portfolio or full CSV is uploaded. Finviz .env credentials are never read by this client.

Official unauthenticated mapping limits checked 2026-10-23: 25 requests/minute and 10 jobs/request,
shared by IP. The client spaces requests at least 3.1 seconds apart within one process, permits at
most three attempts, honors numeric Retry-After up to 60 seconds and rejects longer waits rather
than retrying early. It retries HTTP 429 and selected server errors, not authentication/client errors
or redirects. Coordinate other processes sharing the IP; this is not an account-wide rate limiter.
HTTP timeouts are 30 seconds, response cap 4 MiB, and derived audit cap 100 candidates/job. Oversized
responses are rejected; candidates are never silently truncated.

The documented request is TICKER with exchCode US, marketSecDes Equity and
includeUnlistedEquities false. This US composite context is an assumption based on the Finviz
US-listed screen, not independent exchange verification. Other contexts and ticker punctuation
rewrites are unsupported. The default excludes unlisted instruments and provides no delisting
coverage. It must not be substituted for PIT membership or an original symbol history.

## Fetch one deterministic sample

From the repository root, with the existing external snapshot:

```powershell
uv run baghunter fetch-reference --snapshot 84f34ecbc902a7c007e448a27afb83b93a7a5483fb1a5be5f48bbb2dac748567 --offset 0 --limit 10
```

The limit is 1–10 and offset selects an alphabetical source slice. This CLI makes one public mapping
batch (plus bounded retries) and prints aggregate counts only. There is no scheduler or whole-market
download. The source archive is verified before request construction. An invalid source or selection
fails before any provider request. Fixture-mode source archives cannot be fetched by this command.

Results live under ignored data/reference/openfigi/<mode>/<reference-id>/ as manifest.json,
request.json, response.json and evidence.json. Source mode, source snapshot ID, alphabetical sample,
request/retrieval timestamps and raw hashes are retained. Later requests get distinct vintage IDs.
Publication is atomic. Repeat archive writes validate existing evidence; corruption/symlinks reject.
Reading evidence revalidates its source archive, request selection, original response and derived
bytes. Reads neither repair archives nor make network requests. No CURRENT pointer is created.

The verified external batch queried 10 of 11,783 observations and returned 10 SINGLE_CANDIDATE
results. Reference ID: c713cfb8f3a2d9700defc22d9fa8d386095f7e9ebec913b3af5662fc47df58ae.
It is a deterministic convenience sample, not representative research or a completed universe.

## Interpretation

| Status | Meaning |
| --- | --- |
| SINGLE_CANDIDATE | One exact-ticker US/equity provider candidate, with no name/identity promotion |
| AMBIGUOUS | Multiple candidates; none selected automatically |
| CONTEXT_MISMATCH | A returned ticker/exchange/market context differs from the request |
| NO_MATCH_REPORTED | Provider explicitly reported no identifier; not evidence of delisting |
| NO_CANDIDATES | Empty candidate array; not evidence of invalidity |
| PROVIDER_ISSUE | Other provider error/warning, retained in raw response; not a successful mapping |

Response/job cardinality, field types/lengths, identifier syntax, duplicate FIGIs and printable text
are validated. A syntactically valid FIGI is not independent proof of assignment or company identity.
Unknown or conflicting response shapes fail closed. Raw provider error messages are not displayed
or logged. Mode FIXTURE uses fictional test candidates and a prominent synthetic label.

## Inspect locally

Select the same Finviz snapshot and source mode used by the reference batch, then add:

```powershell
$env:BAGHUNTER_REFERENCE_SNAPSHOT='c713cfb8f3a2d9700defc22d9fa8d386095f7e9ebec913b3af5662fc47df58ae'
```

Restart the localhost API with these environment variables as shown in [Finviz setup](FINVIZ.md).
In Finviz Observations choose **Inspect reference evidence**. The panel shows queried/total counts,
candidate names/FIGIs/types, ambiguity/no-match states and lineage. No lookup runs from the browser.
GET /finviz/reference is read-only and requires the explicitly selected batch to match the selected
Finviz snapshot and mode. Cross-source/missing/corrupt selections return a generic 503. The browser
also checks source binding and clears earlier evidence on a failed reload. No fixture fallback.

Market-cap scale, price currency/adjustments, company-name match and PIT security identity remain
unresolved. This provider response supplies no currency or market-cap unit evidence. Exactly one
next implementation step: add auditable company/share-class reconciliation for these candidates
before considering current identity promotion or expanding the mapping sample.
