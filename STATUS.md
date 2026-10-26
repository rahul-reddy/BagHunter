# Current handoff — company/share-class comparison / 2026-10-26

## Implemented and executed

Reference PR #21 was squash-merged as a791727 before this branch began, with 154 backend and six
browser tests in CI, independent Claude approval with zero blockers, and identical reviewed/merged
trees. This increment adds a deterministic, read-only comparison of the same saved reference batch
against its verified Finviz source. No new provider requests or sample expansion occurred.

The evidence panel now shows both company names, exact/case-whitespace/different text comparisons,
missing composite/share-class IDs, and same-level identifier reuse across queried source tickers.
Every candidate remains REVIEW_REQUIRED; absent results remain NO_CANDIDATE_EVIDENCE. Raw archives,
Finviz null IDs/unknown types and fixture research outputs are unchanged. Comparisons preserve
punctuation, legal suffixes, accents and class designations. No fuzzy matching or automatic approval.

Reports carry both source IDs/hashes/times, a versioned policy and a canonical-JSON checksum.
GET /finviz/reference derives the separate report without writes or network access. The browser
checks report/source/batch binding and removes stale evidence on failure. The offline
reconcile-reference CLI prints aggregate provenance/counts only. See docs/REFERENCE.md.

Executed saved-source comparison: ten of 11,783 observations; three CASE_WHITESPACE_ONLY, seven
DIFFERENT_TEXT, no missing composite/share-class IDs or shared identifiers within this batch.
Zero promotions. Report SHA: e09210a1b88e2ed68bb10e1a2c5d5aa0df66b6d5b3be616370c4bcac7b90793d.
Original source/reference IDs and archive locations remain documented in docs/REFERENCE.md.
The API smoke check returned HTTP 200 with ten comparisons and this digest; no provider rows logged.

## Verification on this runtime revision

uv run ruff check ., ruff format --check . and mypy packages apps/api passed. Full pytest with
coverage/JUnit passed 168 tests, with two Windows symlink skips (Linux CI must run those boundaries).
Evidence: artifacts/test_results/reconciliation-pytest.xml and coverage.xml. Frontend lint, types
and production build passed. All six Playwright tests passed, including comparison labels, escaped
names, missing-class flags, source/report mismatch rejection, reload errors, keyboard access,
desktop/mobile accessibility and fixture research flows. Labeled fictional screenshots are under
artifacts/screenshots/. An initial browser run timed out on first-page load while other checks ran;
five other tests passed, then all six passed in the standalone rerun without code/test changes.
git diff --check passed. .env and all vendor archives/operational scripts remain ignored.
Current-head CI and independent review remain required before guarded squash merge.

## Limits and next action

Text agreement and present provider IDs do not verify a company or share class. Identifier reuse
checks cover this batch only and may indicate legitimate aliases. No independent issuer/class
evidence, historical identity, delisted universe, currency or market-cap scale gate is resolved.
No empirical result, candidate thesis or deployment. Exactly one next step: collect independent
issuer/share-class evidence for one queried candidate, archive provenance and unresolved differences,
then assess whether a current identity decision can be proposed. Do not expand/promote automatically.

---

# Archived handoff — current reference evidence / 2026-10-23

## Implemented and executed

OpenFIGI's documented public mapping API is now available through fetch-reference, with no API key,
account creation, .env read or purchase. It queries at most ten alphabetically selected public tickers
from the verified external Finviz snapshot. Request bytes, response bytes, timestamps, source binding,
hashes and derived candidate evidence are archived under ignored data/reference/openfigi/.
The client has 3.1-second spacing within a process, three-attempt retry budgets, Retry-After handling,
30-second HTTP timeouts, a 4 MiB response cap and 100 candidates/job. Redirects and unsafe contexts
are rejected. Other processes sharing the IP still need coordination.

The verified external batch queried 10 of 11,783 observations, returning ten SINGLE_CANDIDATE
results. Reference ID: c713cfb8f3a2d9700defc22d9fa8d386095f7e9ebec913b3af5662fc47df58ae.
It belongs to Finviz snapshot 84f34ecbc902a7c007e448a27afb83b93a7a5483fb1a5be5f48bbb2dac748567.
A preliminary local batch is retained as an ignored prototype; the documented selection above was
re-fetched after making archived request bytes identical to the actual HTTP body. No raw rows logged.

The optional Current reference evidence panel in Finviz Observations displays the explicitly selected
batch, queried/total counts, candidate names/FIGIs/types, ambiguity/no-match states and lineage.
GET /finviz/reference revalidates local evidence and source binding; it never fetches or writes.
The browser rejects a different source/mode and clears previous evidence on failure. Fixture labels
remain explicit. The preview API has the verified reference selected via environment, not a token.

## Executed verification and delivery gates

On the final runtime worktree: ruff check/format and mypy passed; full pytest with coverage/JUnit
passed 152 tests with two Windows symlink skips. Linux CI must execute both symlink boundaries.
Frontend lint, types and build passed. Six Playwright tests passed, including reference ambiguity,
external/fixture labels, mismatched-source rejection, reload errors, accessibility, mobile overflow,
and the existing fixture research flows. No actual provider rows are used in committed tests.
API and real-browser smoke checks displayed the selected ten-record batch, with zero identities
promoted and no provider rows logged. CLI printed aggregate counts only. Public source docs were
checked, local Markdown links and git diff whitespace verified. Evidence: artifacts/test_results/
reference-pytest.xml, coverage.xml and labeled fictional browser screenshots under artifacts/screenshots/.
Current-head CI and independent review remain required before guarded squash merge.

## Meaning and remaining work

These are current provider candidates, not a historical security master or verified company match.
Original Finviz IDs/types remain null/unknown; no research input, eligibility or ranking changed.
A single exact-ticker US/equity result is not identity promotion. Ticker reuse, company/share-class
matching, quote-time identity, delisted history, currency and market-cap export scale remain unresolved.
Unqueried names are not classified as no-match. Names/results with context mismatches or ambiguity
are retained without automatic selection. No new empirical study, candidate thesis or deployment.

Exactly one next implementation step: add auditable company/share-class reconciliation for the
queried candidates before considering current identity promotion or expanding the sample. Read
docs/REFERENCE.md for commands, provenance and limitations. Prior browser PR #20 was fully merged
as 06befae before this branch began; final CI passed 109 backend/5 browser tests, Claude approved
with zero blockers and the reviewed/merged Git trees matched. Source rows and .env remain ignored.

## Prior observation-browser handoff

### Current handoff — Finviz observation browser / 2026-10-23

#### Implemented increment

Finviz Observations is a separate read-only snapshot explorer with alphabetical search/pagination,
retrieval age, missing values, reported units, unknown type/identity labels and source lineage.
It works independently of the fixture research run. No score, common-share eligibility or historical
research promotion was added. The official screener help was checked again; it does not resolve
this CSV's market-cap scale or permanent security identity. Those gaps remain explicit.

GET /finviz/observations serves only a SHA-selected local archive via BAGHUNTER_FINVIZ_SNAPSHOT and
BAGHUNTER_FINVIZ_MODE. It verifies raw/derived integrity without writes, vendor calls or fallback.
Query/offset/page-size limits are enforced. Prices/cap retain provider scale; share volumes and
percentage display text avoid browser numeric rounding. Search/reload errors remove prior rows.
Fixture snapshots always show a synthetic label. The existing research pages still use fixtures.

#### Validation and delivery

On the final runtime worktree, ruff lint/format and mypy passed; pytest with coverage/JUnit passed
108 tests plus one Windows symlink skip. The Linux CI gate must exercise the symlink boundary.
Frontend lint/types/build and all five browser tests passed before the final metadata-type fix;
UI code is unchanged by that fix. Browser acceptance covers search, pagination, error/empty states,
separation when fixture data is unavailable, exact large numbers, escaped text, keyboard scrolling,
desktop/mobile axe scans and viewport overflow. Browser final results are recorded in the PR.
The first browser run exposed a nonfocusable scroll region; it was made keyboard accessible and
retested without relaxing the accessibility assertions. No vendor rows are committed or captured in
browser test screenshots; fixtures shape the UI tests. Evidence: artifacts/test_results/
finviz-browser-pytest.xml and artifacts/screenshots/finviz-desktop.png, finviz-mobile.png.
A final precision audit added rejection above 28 significant digits before decimal arithmetic, plus
two regressions for unsupported precision and exact supported large percentages. Head b61595b
passed CI (104 backend/5 browser) and Claude review with zero blockers. Before merge, addressed its
scalar-coverage advisory with an object-type guard and five regression cases (generic 503 without
raw values). All 108 local backend tests passed again, plus the Windows symlink skip. Current-head
CI and the same independent reviewer are required again before guarded merge.

The real local API smoke check returned HTTP 200, total 11,783, mode EXTERNAL_UNVERIFIED, unknown
permanent identity and unverified cap units from the existing immutable snapshot. Source data and
.env remain ignored. The preview API was restarted with an explicit snapshot selection; no deploy.

#### Limitations and next action

No historical PIT membership, original filing vintages, security master, currency/adjustment or
market-cap export-scale evidence was established. The browser is observational; empirical research
and verified theses remain blocked. Provider observation time is unknown even for a recent export;
the 24-hour stale threshold measures retrieval age only. Local browser setup is in docs/FINVIZ.md.

Next: obtain authoritative export-unit and security master evidence before adding currency-aware
filters, common-share eligibility or candidate research. No new manual CSV input is needed.
Prior importer PR #19 was fully squash-merged as eebfb42 before this branch began; its reviewed and
merged trees matched. It passed 92 backend/3 browser CI tests and Claude approval with zero blockers.

#### Prior importer handoff

### Current handoff — Finviz current snapshot importer / 2026-10-23

#### Implemented and locally executed

packages/data/finviz.py and CLI ingest-finviz now validate the exact unfiltered overview CSV and
its credential-free export manifest. Local ingestion of all 11,783 saved observations succeeded.
Immutable snapshot: data/finviz/snapshots/external_unverified/
84f34ecbc902a7c007e448a27afb83b93a7a5483fb1a5be5f48bbb2dac748567/.
The coverage report says QUARANTINED_CURRENT_SNAPSHOT; the fixture dashboard is still synthetic.
Source bytes, manifest, typed JSON/Parquet and coverage are retained. No API call or .env read is
performed by the importer. All licensed observations and credentials remain Git-ignored.

Missing fields: market cap 5,883; P/E 8,857; price 13; change 21. Four reported P/E values are zero,
retained and counted. All permanent IDs are null and security types unknown. Market-cap provider
scale is preserved without an unverified USD multiplier. Explicit percentages become fractions;
volume uses reported shares for the current/last session, not historical session bars.

#### Validation and delivery

Final runtime worktree: ruff check/format and mypy passed; pytest with coverage/JUnit passed
91 tests with one Windows skip (symlink creation unavailable). The Linux CI run must exercise that
symlink boundary. Tests include missing/zero values, decimal units, invalid numeric/text/CSV schemas,
clock/hash/source authorization, mode separation, archive tampering, atomic publish failure/retry,
future ingestion timestamps and CLI redaction. Repeat real-source ingestion was executed to verify
existing archive semantics and retention of ingestion time. Current-head CI and independent review
are required before guarded squash merge. No new UI behavior; browser acceptance runs in CI.
JUnit: artifacts/test_results/finviz-pytest.xml. Local Markdown links and whitespace are checked.

Initial head 8f61b02 passed Linux CI (88 backend/3 browser) and Claude review with zero blockers.
Before merge, addressed its malformed-percent advisory: %, -%, N/A% and +% must reject rather than
become missing values. Four regression cases were added; Observation validation also hides inputs.
The full local suite and real-source repeat import passed again after this fix. Final-head CI and
the same independent reviewer are required again. Empty/corrupt archives intentionally fail closed;
remaining advisory comments are preserved in PR #19.

#### Remaining boundaries and next action

No PIT history, archived universe, original fundamental vintages or delisting evidence is established.
No real candidates or empirical findings are activated. Market-cap scale, currency/adjustments and
security identities/types need source evidence. Do not infer security types from missing cap or
manufacture permanent IDs from tickers. CSV/manifest are capped at 20 MiB/64 KiB, rows at 100,000.
Repeat imports compare Parquet values and schema, not version-sensitive serialized bytes.

Next: verify export-unit and security-type/identity evidence before adding a separately labeled
current-data browser. No further manual export is needed. See docs/FINVIZ.md for the current command.
Branding PR #15, historical staging PR #16 and Finviz handoff/export PRs #17–18 were fully merged
before this implementation branch. No deployment, subscription purchase or trading occurred.

#### Prior handoffs

### Current handoff — Finviz Elite input identified / 2026-10-23

The owner authorized export using FINVIZ_TOKEN in ignored .env. HTTP 200 text/csv was retrieved at
2026-10-23T17:57:17.673674+00:00: 11,783 rows, 11,783 unique nonempty tickers, 11 columns,
1,320,890 bytes. Original bytes and credential-free manifest are under ignored
data/finviz/inbox/20261023T175717Z/, with convenience copies at data/finviz/inbox/screener.csv and
manifest.json. SHA-256 verified: 148ad7a687652508a6c5425df40def965ad90d76ea3ccf02a65b56ca850a9c05.
CSV shape was validated; no vendor rows, tokens or authenticated URLs were logged or committed.
git check-ignore confirmed .env, the CSV/manifest and local operational script are ignored.
docs/FINVIZ.md records observed endpoint behavior and current-snapshot boundaries.
No supported Finviz importer is implemented yet; units and security types require further inspection.
Historical PIT universe, original filing vintages, actions and delisting coverage remain unverified.
The dashboard and runnable examples still use synthetic fixtures; local export is separate.

Delivery checkpoints: branding PR #15 squash-merged as 389db89 before the historical adapter branch;
historical adapter PR #16 squash-merged as b0c205b after exact-head CI and independent Claude approval
with zero blockers. Its reviewed and merged Git trees matched. Main CI run 39992228855 passed.
That implementation's CI ran 49 backend and 3 browser tests. Those are prior implementation results,
not a new test run for this documentation-only change.

Validation for this handoff: official Finviz FAQ, Elite feature page and October 7 API announcement
read on 2026-10-23; local Markdown links and git diff whitespace checked. Current-head CI and
independent review must pass before this documentation branch merges. No runtime code changed.

Next: use the saved CSV to verify units/security types and implement a current-snapshot importer.
The owner does not need to perform the export manually. API export authorization supersedes the
earlier manual-input handoff. No new input is needed for inspection of the saved file.
Do not treat current screens as archived historical membership or today's statements as old vintages.

#### Archived historical staging handoff

#### Sequencing checkpoint

The complete BagHunter rename was committed/pushed, passed CI and local 23-backend/3-browser checks,
received Claude approval with zero blockers, then squash-merged through merge-pr.ps1 in
[PR #15](https://github.com/rahul-reddy/BagHunter/pull/15) as 389db89. The tracked worktree was clean
on main before feat/historical-data-import was created. The next item did not start before that merge.
Research output fingerprint before/after branding remained
84fcdf1abf85770ab82a5dcf9d4cb90a42b7c90e7adca1f4e53af1c827090fbb.

#### Implemented increment

- packages/data/history.py: normalized local-export provider, dated membership/symbol reads,
  raw-bar policy, filing-lag cutoffs, source/ID/checksum validation and coverage audit.
- CLI: audit-history and ingest-history; errors suppress raw input values. No provider HTTP calls.
- Inputs: explicit license-use attestation, source vintage, expected sessions, seven hashed tables.
- Outputs: raw bytes, typed silver Parquet and coverage.json in immutable, separate fixture/external
  quarantine namespaces. No candidate activation, broker actions or empirical claims.
- Fixture example: two fictional instruments, five bars and one zero-proceeds delisting; facts missing.
- Limits: 20 MiB/table, 64 KiB manifest and five million instrument/session audit combinations.

#### Executed evidence and gates

49 backend tests passed on the implementation worktree; ruff lint/format and mypy passed.
Actual CLI audit and ingestion produced QUARANTINED_NOT_RESEARCH_READY with FIXTURE_ONLY and
FUNDAMENTALS_MISSING. Snapshot bf12ff7006865a18d2c5dd4b7d56fd60688a64b38166d0a3526b9e64c31443a7.
Tests cover PIT revisions/expiry, future source clocks, price/action metadata, missing coverage,
source authorization, checksum and archive tampering, namespace separation, input caps and redaction.
Actual UTC ingestion time is retained on repeats; future ingestion records fail closed. A transient
workspace publish failure did not reproduce on retry; bounded file-lock retry is now regression-tested.
Example JSON is pinned to LF for checksum stability; all 26 history tests were rechecked after
normalizing working-copy line endings.
JUnit: artifacts/test_results/history-pytest.xml; coverage.xml is from the expanded suite.
History adapter file SHA-256 at local verification: 4c992180bd3fb852da8235764e20b2f0d1b4d6eeb02f8ad0e02c7de21640dcc5.
Current-head CI and independent approval remain mandatory before this increment may merge.

#### Limitations and next step

No licensed provider/export has been supplied. All executable examples are synthetic. External
exports remain unverified: schema/checksum checks cannot independently prove licensing, archived
universe completeness, original bar vintage, calendar accuracy or correct delisting coverage.
No new research findings, activated real candidates or verified theses. Filing documents and vendor
API authentication are unsupported by this adapter. Large exports must be partitioned.

Next: map one authorized provider export to docs/HISTORICAL_IMPORT.md and independently audit its
coverage before adding explicit real-data research activation. No subscription or spending occurred.

Nonblocking branding review advisories remain recorded in PR #15: branded export regression coverage
and duplicate brandmark announcement. Its handoff heading advisory is addressed by this archive layout.
Prior CSV-encoding and framework tooling advisories remain as described below; no comments were changed.
Review access: API-funded Claude was unavailable; a process-local removal of API auth overrides used
its already logged-in claude.ai subscription for the independent review. No stored authentication settings were edited.

#### Prior handoffs

##### Current handoff — BagHunter branding / 2026-10-23

The app, browser title, header/footer/logo, Radar navigation, API title, CLI help, npm metadata,
project brief and documentation now use BagHunter. The watchlist export is baghunter_watchlist.csv.
This rename is isolated on feat/baghunter-branding and must be fully squash-merged before the next item.

Local validation on the rename worktree: 23 backend tests, ruff lint/format and mypy passed;
CLI help and imported API title checked. A tracked-file search found no stale product-name references.
Research signals, cohort study and toy evaluation have identical before/after SHA-256 fingerprint:
`84fcdf1abf85770ab82a5dcf9d4cb90a42b7c90e7adca1f4e53af1c827090fbb`.
Only run identity and the branded export filename change. Fixture-only research limitations persist.
Browser smoke now asserts the BagHunter page title; frontend checks and current-head CI/review are
required before merge. CI and independent approval are authoritative in the branding PR.

Next item remains the licensed PIT market-data adapter and coverage audit. Start it only after the
branding PR is merged and the tracked worktree is clean. The local preview was started during the
owner's prior session; restart the API after merge to pick up its title change.

###### Previous verified fixture release

##### Current handoff — fixture MVP shipped / 2026-10-23

Sprint 0–3 fixture vertical slice merged through [PR #1](https://github.com/rahul-reddy/BagHunter/pull/1)
at `656cc7e8906cf0ea3add52404da10eb455034cf9`. The tested/reviewed PR head was
`7269b132db3b7cf202c6d86c7e249e2150eaee85`; both commits have identical Git tree
`e5493b495f18ca9f8c95dcd1244c14ca0d3f258a`. This handoff changes documentation only.

- [Linux CI](https://github.com/rahul-reddy/BagHunter/actions/runs/39962076649): PASS, including
  23 backend tests, 3 browser tests, builds, types/lint, harness and skill checks.
- [Windows harness](https://github.com/rahul-reddy/BagHunter/actions/runs/39962076692): PASS.
- [Gemini exact-head review](https://github.com/rahul-reddy/BagHunter/pull/1#issuecomment-6366233806):
  APPROVE, zero blocking findings. Merge executed only with scripts/merge-pr.ps1.
- Dependency advisories: no known Python/npm vulnerabilities. Gitleaks: no leaks found.
- Demo run `e0280e146da378f5`; package source digest
  `4f432c33286a64f0b56defd403209e300c25346d2c255e160c575fe9cb52670c`.

###### Executed evidence

- Initial full `pwsh -NoProfile -File scripts/qa.ps1` (20 backend / 3 browser tests): locked Python/npm installs, harness self-test, skill validation,
  ruff lint/format, mypy, integrity/API tests, demo CLI, frontend lint/types/build, 3 browser tests.
- Tests cover future filing/amendment rejection, negative/missing prices, ticker reuse, independent
  split/dividend/delist wealth expectations, missing horizons, matched peers, next-open costs,
  separated labels, manifest checksums, reproducibility, source failures and API readiness.
- Browser: profile factors/citations, case/control museum, evaluation/baselines, source ledger,
  search/empty state, missing backend, desktop/mobile axe scans and no page overflow. Screenshots
  inspected at artifacts/screenshots/command-center.png and mobile.png.
- Saved logs and JUnit: artifacts/test_results/. Local coverage.xml measured 89% on the initial 20-test suite; final CI includes its own coverage XML.
- Demo: 3 profiles, 12 horizon labels, 1 matched pair, 13 sequential screening windows.
- Historical anchor 2020-01-01; candidate clock 2022-01-03T23:00:00+00:00; toy period
  2019-12-31–2022-01-05.
- Latest synthetic source timestamp: 2023-03-30T22:00:00+00:00.
- Initial failures fixed: zero-volume denominator, missingness type inference, Windows directory lock
  retry, mismatched fixture peer strata, accessible score names and root data ignore pattern.

###### Review hardening

Both Gemini advisories were addressed: explicit UTF-8 run reads and deterministic split → dividend →
delist ordering. An additional audit found that missing evaluation exits could retain numeric wealth;
comparisons now fail closed instead. Research clocks normalize to UTC before calendar-date filters.
Three regression tests cover missing exits, reversed same-date action inputs and equivalent timezone
instants. Revised local checks: ruff lint/format, mypy, 23 pytest tests, CLI demo and browser suite.
Full QA and final CI logs remain at artifacts/test_results. Final reviewed-head proof is linked above.
Remaining nonblocking advisory: CSV exports lack explicit UTF-8 encoding; current fixture export
fields are ASCII. Fix before supporting real multilingual names. No advisory was hidden or deleted.

###### Remaining boundaries

Entirely synthetic fixture; no empirical alpha or real stock recommendations. Zero verified theses.
Real historical PIT universe/bars/actions entitlement is unavailable. SEC download needs a real
contact user agent; only a raw submissions client exists, with PIT fact parsing/pagination pending.
Full stage history, industry breadth, real market cap, rigorous holdout, capacity constraints and
live refresh remain unimplemented. Framework httpx TestClient deprecation and ESLint 9 support
notice are non-blocking tooling advisories; npm reported zero vulnerabilities locally.

No deployment, automatic jobs or currently running preview. Start services with README commands.
Automatic approval review rejected detached preview startup with "blocked by policy" and no more
specific reason. Terminal startup was verified by the automated browser suite.
Owner authorized public pushes. Original specification preserved in bootstrap main commit 6c994b5;
implementation goes through a squash PR and scripts/merge-pr.ps1 only.

Next implementation milestone: a licensed PIT market-data adapter and real-data coverage audit.
Real-data gates remain blocked; do not interpret fixture acceptance as empirical research success.
