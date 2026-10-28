# Local operations

Start and verify using README commands. Services bind only to loopback. The Vite proxy keeps browser
requests on the same origin; the API exposes only read routes. `/health` reports readiness separately
from process liveness. Missing/corrupt data returns 503, never generated results.

Pipeline writes a new immutable run directory before atomically switching `CURRENT`. Keep raw SHA
snapshots, run folders and original source manifests together when backing up. To recover an old
fixture run, stop writers and set CURRENT to an existing 16-character hexadecimal run directory.
Do not edit raw evidence. Regenerate with the same source version, UTC as-of and seed for repeatability.
Do not run concurrent writers to the same output directory. Archives accumulate per source/code/policy revision; measure the actual directory rather than assuming a fixed size.

The fixed fixture is a bounded CPU job; no automatic scheduler/backfill or paid job runs. Cancel with
Ctrl+C; incomplete staging directories do not become active. Remove abandoned `run-*` directories
only after stopping all pipeline writers. Review their absolute paths before deleting anything.

Real SEC raw downloads go under data/real/sec/raw. Use one process, configure BAGHUNTER_SEC_USER_AGENT
(or SEC_USER_AGENT) in private .env/environment, honor failures/backoff and retain digests/manifests. Cache stores immutable responses but does not
implement conditional HTTP fetching. Bounded historical pagination is supported only through the
SEC parent-declared submission files with `sync-sec --include-history`; see PROVIDER_REFRESH.md. Never treat current companyfacts
as historical financial snapshots without accession/publication checks.

No secrets in client bundles. `.env`, data and artifacts are ignored. Review exports and licensing
before sharing. No deployment target exists: future deployments need explicit owner confirmation,
must ship a commit already on main, and must record that SHA on the target.

Provider commands and the real SEC evidence browser: [Provider refresh](PROVIDER_REFRESH.md).
Manual CLI requests use the existing Finviz subscription and supplied SEC contact. No API/browser
action starts downloads, changes credentials, approves identities or activates historical research.

## Bounded local acceptance

Stop refresh writers, keep the API running, and run:

```powershell
uv run python scripts/operations_audit.py --root data/fixture/latest --disk-budget-mib 512 --api http://127.0.0.1:8000
```

The audit reads the generated fixture tree, rejects linked entries or an exceeded declared disk
budget, verifies all active-run manifest entries, copies the active archive into an automatically
removed temporary directory, verifies the copy, and checks that CURRENT did not change. It never
switches the source pointer. An optional load check makes twelve GETs at concurrency four against
an explicit IPv4 loopback HTTP API. It checks readiness, run binding, HTTP success and a 20 MiB
per-response limit, with 30-second request timeouts. It follows no redirects or environment proxies.
Outputs contain timing, sizes and digests, never response bodies or credentials. This is a bounded
smoke check, not a production throughput guarantee. Omit --api for offline recovery only.

A generated-archive copy is not a full evidence backup. Separately retain raw SHA files, original
provider manifests, source version/configuration, policies and browser-exported drafts. Protect
credentials separately. Never move real evidence into fixture directories. Before restoring an
old run, stop writers, copy the whole selected run and corresponding raw sources to a separate
location, verify every manifest checksum, then atomically replace CURRENT with the known 16-hex ID.
Do not use an unverified path or edit an immutable run to make it pass.

Cancellation before publication leaves the previous CURRENT active and cleans staging on a normal
Python interruption. A hard process kill may leave staging; stop writers before inspecting it.
There is no mid-calculation CPU checkpoint: rerun the same source/as-of/seed/policies. Complete
verified archives are reused; corrupt archives fail closed and are never silently repaired. A
crash after publishing a complete run but before CURRENT changes leaves that run inspectable;
rerunning verifies it before activation. Keep the last known-good archive until the rerun passes.

The default audit budget is 512 MiB for generated fixture history, configurable from 1 to 10240 MiB.
This is an inspection gate, not an automatic retention/deletion policy or a RAM limit. Allow room
for one complete temporary copy of the active run. Provider bounds are separate: SEC history has
at most ten parts, 10000 accessions and 60 MiB raw input; real current Finviz archives accumulate
independently. No automatic backfill, pruning or scheduler is installed. CPU/RAM depend on hardware
and retained work; measure before broader local studies. Resource exhaustion is a failed operation,
not permission to drop records or publish partial results.
