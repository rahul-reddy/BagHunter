# Next action

The BagHunter branding checkpoint is merged in PR #15 (389db89), before historical adapter work.

Exactly one recommended next implementation step: map one authorized provider export to the
normalized historical import contract, independently checking PIT membership, calendars, delistings
and permitted use before enabling real-data research. Required external input: provider name and
licensed export/entitlement. Never put credentials in chat, manifests, commits or logs.

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
