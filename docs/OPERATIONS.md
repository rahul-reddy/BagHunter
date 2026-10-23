# Local operations

Start and verify using README commands. Services bind only to loopback. The Vite proxy keeps browser
requests on the same origin; the API exposes only read routes. `/health` reports readiness separately
from process liveness. Missing/corrupt data returns 503, never generated results.

Pipeline writes a new immutable run directory before atomically switching `CURRENT`. Keep raw SHA
snapshots, run folders and original source manifests together when backing up. To recover an old
fixture run, stop writers and set CURRENT to an existing 16-character hexadecimal run directory.
Do not edit raw evidence. Regenerate with the same source version, UTC as-of and seed for repeatability.
Do not run concurrent writers to the same output directory. Typical demo disk use is a few MB.

The fixed fixture is a bounded CPU job; no automatic scheduler/backfill or paid job runs. Cancel with
Ctrl+C; incomplete staging directories do not become active. Remove abandoned `run-*` directories
only after stopping all pipeline writers. Review their absolute paths before deleting anything.

Real SEC raw downloads go under data/real/sec/raw. Use one process, supply SEC_USER_AGENT explicitly,
honor failures/backoff, and retain digests/manifests. Cache stores immutable responses but does not
yet implement conditional HTTP fetching or historical pagination. Never treat current companyfacts
as historical financial snapshots without accession/publication checks.

No secrets in client bundles. `.env`, data and artifacts are ignored. Review exports and licensing
before sharing. No deployment target exists: future deployments need explicit owner confirmation,
must ship a commit already on main, and must record that SHA on the target.
