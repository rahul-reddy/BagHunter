# Historical export adapter and coverage audit

This adapter ingests a **normalized local export**, not a vendor API. The owner has Finviz Elite;
no export or authenticated provider connection has been supplied. See [Finviz handoff](FINVIZ.md).
The adapter enables a licensed source to be brought into a bounded, auditable staging area.
It does not activate candidates, fit a model, establish alpha, or verify a data license independently.

## Try the explicitly fictional example

```powershell
uv run baghunter audit-history --bundle examples/history-fixture
uv run baghunter ingest-history --bundle examples/history-fixture --output data/imported
```

The example is entirely FIXTURE: two fictional instruments, five bars, a three-day invented calendar,
and a zero-proceeds delisting. January 1 is intentionally just a fixture date, not an exchange-session
assertion. Financial facts and point-in-time capitalization are missing. The resulting report must say
`QUARANTINED_NOT_RESEARCH_READY`, `FIXTURE_ONLY`, and `FUNDAMENTALS_MISSING`.

Imports write immutable folders at `data/imported/fixture/<snapshot-id>/` or
`data/imported/external-unverified/<snapshot-id>/`. Each contains exact raw bytes, typed silver Parquet
tables where nonempty, and coverage.json. Empty arrays remain in raw evidence and are reported as gaps.
The report records actual UTC ingestion time; repeated imports retain that original timestamp.
There is no CURRENT pointer or automatic promotion to the demo pipeline. The existing dashboard
continues to show only its labeled demo run. Repeating an import verifies its existing archive;
corruption or changed derived output fails closed. Partition larger exports before importing.

## Bundle contract

Supply `manifest.json` and seven UTF-8 JSON arrays: `instruments.json`, `symbols.json`, `universe.json`,
`bars.json`, `actions.json`, `facts.json`, and `sessions.json`. The committed example shows exact fields.
Every table, including an empty table, needs its actual file-byte SHA-256 in `manifest.files`.
Keep line endings unchanged after hashing; the example pins LF in Git for cross-platform checksums.

Manifest fields:

| Field | Required interpretation |
| --- | --- |
| schema_version | 1 |
| mode | FIXTURE or EXTERNAL_UNVERIFIED; never relabel synthetic observations as real |
| source_id / provider | source identity and provider name; no credentials |
| source_url | public HTTPS reference (fixture scheme allowed only for FIXTURE); no auth/query/fragment |
| retrieved_at | timezone-aware time after the latest included observation/publication |
| license_note | source terms and permitted local use, checked by the owner |
| usage_authorized | literal JSON true; caller attestation, not independent legal verification |
| universe_basis | archived_pit / current_only / unknown; current constituents are not a historical universe |
| delisted_coverage | included / excluded / unknown; this declaration still needs source evidence |
| actions_coverage | complete / unknown; never infer no actions from an empty table |
| files | SHA-256 for each of the seven required arrays |

The adapter fulfills the MarketProvider interface for exported instruments, raw bars, realized actions,
and knowable fundamental facts. `get_filings` raises an explicit unsupported error; it does not invent
an empty filing history. Credentialed vendor HTTP access and historical SEC parsing remain separate work.

## Point-in-time and integrity boundaries

- Permanent IDs must be unique and all table references must resolve. Fixture Instrument bucket
  defaults are not used for external instruments. Missing capitalization/sector remain null.
- Universe observations include `asof_time`, `published_at`, explicit `valid_until`, eligibility and
  exclusion reason. Queries select only known revisions and do not carry expired membership forward.
- Symbol intervals are half-open and publication-timestamped. Missing or ambiguous as-of mappings fail.
  As-of instrument outputs omit hindsight delisted flags and future last-seen dates.
- Bars must be raw, finite, positive, internally consistent, unique per security/session, within listing
  intervals, and unavailable before their session. No corrected bar silently overwrites another.
- Fundamental reads retain all originally available revisions and enforce a 24-hour processing lag.
- Expected sessions are provider-supplied, sorted, unique dates. The audit counts missing bars while
  retaining delisted instruments. Unresolved terminal proceeds stay a gap; zero is never inferred.
- Source declarations and input checksums cannot independently establish complete PIT coverage,
  correct exchange calendars, licensing, or original vendor vintage. These limitations always remain
  visible, even if the structural contract passes.
- Input files stay within the selected bundle directory and have a 20 MiB per-table cap; manifest cap
  is 64 KiB. The calendar audit allows at most five million instrument/session combinations.
- Failed validation does not activate or overwrite an existing candidate run. CLI errors do not echo
  raw provider input, which can contain private metadata. Keep licensed files under ignored data paths.

Next step after a provider/export is supplied: map its original format to this contract, independently
audit coverage and entitlements, and only then add explicit real-data research activation with tests.
