# Finviz and SEC provider refresh

Direct quarterly/YTD statements, EPS, weighted shares and balance-sheet evidence from existing
verified bundles are documented in [SEC statements](SEC_STATEMENTS.md). No additional provider
refresh is needed to inspect them.

Owner direction, 2026-10-26: use Finviz Elite as the market-data provider and the SEC contact details
already added to the ignored `.env`. Another subscription is not a prerequisite for implementing
the available workflows. Unsupported historical coverage stays explicit rather than fabricated.

## Configure and run

Provider commands read only their allowlisted values from `.env`. Both `BAGHUNTER_SEC_USER_AGENT`
and `SEC_USER_AGENT` are supported; `FINVIZ_TOKEN` supplies the existing Elite token. Nonempty
process environment values take precedence over the file. Within either layer the canonical
`SEC_USER_AGENT` takes precedence over its alias. No value is exported to the process environment,
interpolated, evaluated, logged, embedded in the client or copied into an archive. The bounded
64 KiB UTF-8 file accepts plain/quoted values, optional `export` and comments. Duplicate target
keys or invalid quoting/control characters reject. No change to the owner's `.env` is required.

```powershell
uv run baghunter refresh-finviz --usage-authorized
uv run baghunter sync-sec --cik 1090872
```

Run from the repository root. `--env-file <local-path>` selects another private configuration file.
`sync-sec --asof <aware-ISO-timestamp>` freezes an earlier research clock; the default is now.
The CIK above is the previously investigated Agilent filer, not a security/share-class approval.
`sec-fetch` also supports `.env`/the alias and retains its raw-only download behavior.

## Finviz boundary

Refresh uses the already verified unfiltered overview endpoint and eleven-column CSV contract.
The token is sent only to HTTPS `elite.finviz.com`, on `/export.ashx` or `/export`; redirects to any
other origin, port, credential-bearing authority or path reject before credentials are forwarded.
At most three requests occur, spaced by at least 0.6 seconds between redirect hops. Run only one
provider refresh process per account; other consumers share the account's quota. HTTP 429 fails
without a request loop. The official [API announcement](https://finviz.com/blog/our-upgraded-api-higher-limits-clearer-data-and-more-ways-to-connect/)
documents the shared rolling quota and Retry-After handling.

Only successful bounded `text/csv` responses are parsed; unsupported shapes, oversized data or
credential-bearing bodies reject. The original export/credential-free manifest is archived under
`data/finviz/inbox/`, then the existing importer publishes an EXTERNAL_UNVERIFIED snapshot. It
does not change fixture CURRENT or infer security type, currency, scale or historical membership.
Select the new snapshot explicitly in Finviz Observations. Notes remain bound to their snapshot.

## SEC boundary and publication clock

Synchronization fetches submissions and companyfacts for one explicit CIK from the documented
[SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). Responses
must be JSON, match the requested CIK/resource, remain at most 20 MiB decoded, and must not redirect.
The client limits one process to two requests/second, with at most three attempts for 429/selected
transient server errors. Existing content-addressed raw files/manifests are revalidated and never
silently repaired or overwritten. No contact or request headers enter the archive.

Real submissions can contain nested primary-document paths. Bounded safe path segments are
retained; dot traversal, encoded traversal, backslashes and alternate origins reject. Some filing
dates differ from acceptance after hours; the SEC explains the distinction in
[Determine the Status of My Filing](https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/determine-status-my-filing).
Exact accession acceptance metadata remains mandatory. When supplied, the submissions filing date
must match companyfacts. Publication uses the later of acceptance and following UTC midnight of
the official filing day, then adds the configured 24-hour processing lag. This is a conservative
upper-bound proxy, not an asserted exact first-public time. Friday after-hours acceptance cannot
make a Monday filing visible over the weekend. The normalization policy is versioned in bundles.

Only supported annual USD entity-wide facts are normalized. Amendments remain separate; missing
old accession metadata and unsupported forms/periods/units are counted. Conflicting values reject.
Raw pairs, policy, as-of clock and normalized results publish as immutable bundles under
`data/real/sec/bundles/`. A CIK-based local entity key stays explicitly unverified as a security ID.
Original extraction vintages and quarter/custom-taxonomy interpretations are not certified.

## Inspect and reproduce

Data Quality → SEC filing evidence lists saved bundles, verifies both original hashes, recomputes
normalization and checks the stored result on selection. It works even without a fixture run.
Filter annual metrics, page through facts and follow dated source citations. Export explicitly
downloads the current page with its full source manifest and total count. Index metadata alone is
not verification. Failed/mismatched responses clear previous facts. API reads never fetch providers.

Executed locally: Finviz refreshed 11,772 current rows; SEC CIK 0001090872 produced 102 annual facts,
excluding 285 records without recent accession metadata and 384 unsupported form/period records.
These are source/normalization counts, not investment findings or a historical investable universe.
Full goal acceptance remains open. Next integrate additional supported Finviz/SEC workflows against
verified contracts, keeping real observations separate from synthetic cohort/backtest outcomes.


## Historical accession coverage and financial profile

`uv run baghunter sync-sec --cik 0001090872 --include-history` additionally fetches the
historical submissions files explicitly declared by that CIK's parent response. At most ten parts,
10,000 merged accessions and 60 MiB of raw input are supported; an exceeded bound rejects rather
than truncates. Exact overlaps deduplicate; conflicting accession metadata rejects. Raw parent,
companyfacts and historical parts remain unchanged. A separate deterministic derived submissions
index and its source hashes make the union reproducible. v1 bundles remain readable; history
bundles use `sec-bundle-v2-history`. API/browser reads never request these sources.

Executed for the existing CIK: one older part plus recent metadata yields 2,365 accession rows;
26 rows lack primary documents and stay excluded from citation-bearing normalization. The result
contains 165 supported annual facts, with zero missing-accession exclusions and 597 unsupported
form/period records. Current aggregate downloads do not certify original extraction vintages.

Data Quality displays a descriptive annual financial profile from the complete verified bundle,
independent of the fact table's metric filter and pagination. Revenue growth requires adjacent
330–400-day annual ends and positive prior revenue. Margins require same-period USD facts and
positive revenue; absent values remain unavailable. Latest revisions obey the frozen clock and
processing lag, with acceptance time breaking publication-bound ties. All used facts retain filing
citations. No per-share valuation, security identity, ranking or historical-universe promotion is
implied. The full profile has its own JSON export; fact exports contain only the current fact page.
