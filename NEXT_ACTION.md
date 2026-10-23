# Next action

The fixture implementation is merged via PR #1 (656cc7e); its exact reviewed head is 7269b13.

Restart demo: `uv run baghunter demo`.
Backend: `uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`.
Frontend in a second terminal: `npm --prefix apps/web run dev`.
Open http://127.0.0.1:5173. Stop services with Ctrl+C.
Rerun acceptance: `pwsh -NoProfile -File scripts/qa.ps1`.
Initial Chromium install: from apps/web, `npx playwright install chromium`.

Exactly one recommended next implementation step: implement and audit a licensed historical
PIT market-data adapter against this fixture-tested pipeline. Required external prerequisite:
owner-supplied entitlement/credentials and verified coverage/license. SEC raw ingestion separately
needs a real SEC_USER_AGENT contact identity; never infer one or mix raw real sources into fixtures.
