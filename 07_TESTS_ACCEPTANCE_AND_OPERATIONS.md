# 07 — QA, acceptance criteria and operations

## Tests (must be real and reproducible)
### Data integrity
- [ ] SEC filing cutoff rejects any fact after research timestamp.
- [ ] Amended financial records do not overwrite originally available snapshots silently.
- [ ] Ticker changes map to permanent ID; duplicate symbols do not merge firms.
- [ ] Split, dividend and delisting treatment validated with independent fixtures.
- [ ] No survival-only filtering in historical denominators without prominent scope tag.
- [ ] Source metadata, checksum and ingested-as-of are available.
- [ ] Missing provider data yields explicit error/coverage flag, never fabricated values.

### Features/cohorts
- [ ] Feature functions are deterministic for frozen inputs.
- [ ] Hindsight label columns are inaccessible to prediction feature assembly.
- [ ] Case/control selection samples only as-of peers.
- [ ] Signals obey stage transition rules and have audit trail.
- [ ] No zero division, invalid price, infinite factor or silent NaN ranking.

### Model/backtest
- [ ] Holdout is chronologically separated and config frozen.
- [ ] Overlapping-label leakage addressed.
- [ ] Benchmark series and transaction costs accounted for.
- [ ] Untradable securities handled explicitly.
- [ ] Rerun from fixed raw manifest and seed reproduces metrics.
- [ ] Negative controls and sensitivity checks included.

### API/UI
- [ ] Local pipeline -> API -> browser works using a labeled sample.
- [ ] Missing provider or stale data displays warning.
- [ ] Profile source citations resolve and show publication dates.
- [ ] Backtest chart always shows run config, OOS distinction and data coverage.
- [ ] Accessibility scan and browser smoke test executed.
- [ ] No secrets in client bundle or git.

## P0 vertical slice acceptance (Sprint 3)
From clean checkout: install; start backend and web; ingest a controlled dataset; produce one historical case matched with nonwinner; generate features that pass as-of cutoff; produce one signal and baseline comparison; open browser and inspect evidence/candidate chart; run automated smoke test. **P0 passes only if commands actually run and evidence is saved.** Real and fixture data must have distinguishable output directories/labels.

## Suggested commands to implement
```bash
make bootstrap
make lint
make typecheck
make test
make test-pit
make ingest-demo
make study-demo
make backtest-demo
make api
make web
make test-e2e
make qa
```
Add CLI options for `--asof`, `--universe`, `--source-manifest`, `--seed`, `--config`, `--output`. Record versions and hashes.

## Operational runbook
- Data backfill and incremental refresh, API budget limits, retries and checkpointing.
- Run status, outage behavior, source change detection, stale flags and manual reruns.
- Secret injection via environment, never hard-coded API keys.
- Backups for curated data/config and immutable manifests; transactional writes of outputs.
- Resource caps, cancellation/resume checkpoints and local disk budget.
- Provider terms and redistributable output review before deployment.
- Explicit human approval for cloud spending, provider subscriptions and public distribution.

## Final release evidence
`artifacts/test_results/`, `artifacts/pit_audit/`, `artifacts/backtests/`, `artifacts/screenshots/`, `reports/RELEASE_READINESS.md`. Every gate labeled PASS/FAIL/BLOCKED with command output or documented empirical reason. No unrun test may be reported as passing.
