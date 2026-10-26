# Next action

Owner directive: finish the full application; keep the overall goal active across milestones.
Use docs/COMPLETION.md. PRs #24–25 are merged. Current work: feat/observation-workspace; see WORKSPACE.md.
Finish final acceptance, source-selection/browser tests, CI and independent review, then guarded
merge and reassess every remaining requirement. Data gaps do not block independent software work.
No purchases or deployment. Run `pwsh -NoProfile -File scripts/qa.ps1` after stopping workspace dev
servers to release Windows native dependency locks. Restart instructions remain below.

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
