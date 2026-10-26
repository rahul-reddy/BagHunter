# Active implementation — SEC statements / 2026-10-26

PR #29 is merged as 28a2fda (324 backend / 17 browser in CI, Gemini approval and final real-data
preview passed). Current feat/sec-statements implements quarterly/YTD/instant statements, EPS,
share/cashflow evidence and exact-period arithmetic from saved SEC archives. Finish current-head
QA, CI, independent review and guarded merge, then verify main and continue the full specification.
Use Finviz and existing SEC configuration. See STATUS.md and docs/SEC_STATEMENTS.md.

---

# Previous active implementation — 2026-10-26

PR #28 is merged as da7ce12 with 296 backend / 17 browser tests in Linux CI and independent
Gemini approval. Current feat/sec-history adds older SEC accession coverage and a cited annual
financial profile. Complete current-revision QA, CI, review and guarded merge; refresh the local
preview and continue full-app acceptance. Finviz + existing SEC configuration are sufficient to
continue; no identity promotion or fabricated empirical results. See STATUS.md.

---

# Next action

Finish the full application with Finviz Elite and SEC; owner supplied SEC contact in .env.
Current branch: feat/provider-refresh. The CLI now supports the contact alias/.env, refresh-finviz
and sync-sec; Data Quality has source-verified real SEC evidence. Both real provider commands ran.
Finish full current-runtime QA, exact-head CI, independent review and guarded merge, then activate
only the saved-source browser selections on main. Research inputs stay fixture/quarantined until
actual acceptance gates pass. Do not ask for a different provider as the default next step.
Read STATUS.md and docs/PROVIDER_REFRESH.md. No subscriptions, broker actions or deployment.

---

## Archived provider-evidence sequencing

The BagHunter branding checkpoint is merged in PR #15 (389db89), before historical adapter work.

The historical staging adapter is merged in PR #16 (b0c205b). The owner has Finviz Elite.
Authorized API export completed: ignored `data/finviz/inbox/screener.csv` and manifest.json;
immutable timestamped source copy in data/finviz/inbox/20261023T175717Z/. A typed local snapshot
importer is implemented and has staged all 11,783 rows under data/finviz/snapshots/external_unverified/.
See [Finviz handoff](docs/FINVIZ.md) for the ingest-finviz command, format and coverage report.
The separate Finviz Observations browser now supports read-only search/pagination of an explicitly
selected saved snapshot. Unknown units/types/IDs are shown without currency conversion or ranking.
The bounded OpenFIGI reference adapter now archives current mapping candidates for a deterministic
sample and exposes source-bound evidence in the browser. Ten of 11,783 observations were queried;
all ten returned a single candidate. No Finviz identity/type was promoted or historical gate opened.
Company/share-class comparison is now implemented: three case/whitespace agreements, seven text
differences, no missing or reused composite/share-class IDs within the ten-record batch. Every
candidate remains unverified. Reports retain both names, review flags and a reproducible digest.
Independent issuer/share-class evidence for one queried candidate is now archived and audited:
the issuer-hosted annual-report cover associates ticker A with a registered common-equity class.
Its first-public timestamp is unknown, and no independent FIGI assignment or continuity to saved
source times is established. Exactly one next step: obtain independently attributable FIGI-to-class
assignment evidence covering the saved source times before proposing any identity decision or a
larger sample. See docs/ISSUER_EVIDENCE.md for the executed assessment and audit-issuer command.
Export-scale/currency and historical master evidence remain unmet gates. No manual CSV input needed.
Never put credentials in chat, manifests, commits or logs. Finviz historical PIT/delisting coverage
remains unverified; current screens cannot fill historical universe or original filing-vintage gaps.

Verified staging commands:
- `uv run baghunter audit-history --bundle examples/history-fixture`
- `uv run baghunter ingest-history --bundle examples/history-fixture --output data/imported`

The example is synthetic and its output stays quarantined. Read docs/HISTORICAL_IMPORT.md.
No import activates the dashboard or changes the demo's CURRENT pointer.

Restart demo: `uv run baghunter demo`.
Backend: `uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`.
Frontend in a second terminal: `npm --prefix apps/web run dev`.
Open http://127.0.0.1:5173. Stop services with Ctrl+C.
Rerun acceptance: `pwsh -NoProfile -File scripts/qa.ps1`.
