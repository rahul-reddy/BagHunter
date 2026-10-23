# Sources and entitlements — checked 2026-10-23

The runnable sample uses only the local deterministic fixture generator. Its `fixture://` URLs are
source identifiers, not real filing citations. The dashboard links them to the local source ledger.

- [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces):
  unauthenticated submissions and XBRL endpoints. Current submissions include recent filing metadata
  and references to older pages. The implemented client fetches the primary submissions page only;
  historical pagination and accession-level fact normalization are pending.
- [SEC developer resources](https://www.sec.gov/about/developer-resources): declared contact user agent,
  efficient downloads and at most 10 requests/s aggregate. Our client caps itself at 2 requests/s in a
  single process, retries transient failures, uses timeouts and content-addressed raw storage.
  It does not auto-coordinate concurrent processes; run one download job at a time.
- [Massive stocks](https://massive.com/stocks): candidate provider only. No selection, subscription,
  account request or entitlement has occurred. Marketing coverage is not proof that any particular
  plan includes historical PIT universe, delisting proceeds or redistribution rights.

No real SEC filing was ingested in this release because a proper identifying user agent was not
supplied. An actionable client exists; the real-data gate remains BLOCKED. No keys are needed for
the fixture; licensed market data requires explicit entitlement and coverage verification.

Normalized local history export staging is now available (docs/HISTORICAL_IMPORT.md). The committed
example is entirely fictional; no provider data was purchased or fetched. License use is a
caller attestation and coverage remains unverified. Imports preserve original bytes and expose
missingness without becoming a live source or an empirical study automatically.

The owner confirmed an existing **Finviz Elite** subscription on 2026-10-23. Public official
documentation supports screener CSV/API workflows; historical PIT and delisting coverage remain
unverified. An owner-authorized API export was saved locally on 2026-10-23, with original bytes,
retrieval timestamp and checksum retained under ignored data/finviz/inbox/. See [Finviz handoff](FINVIZ.md)
for checked sources and the implemented local snapshot importer. No additional manual CSV input is
needed for this increment. Screener field semantics were checked against the official help page;
market-cap export scale and security types remain unverified.
