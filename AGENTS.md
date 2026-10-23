# BagHunter contributor contract

Alpha Hunter: a point-in-time US-equities research laboratory. Read `docs/PLAN.md`, `STATUS.md`,
`SPRINT_STATUS.md`, `NEXT_ACTION.md` and `00_START_HERE.md` before changing behavior.

## Layout
- packages/: validated data, research features, hindsight labels, screening evaluation, CLI.
- apps/api/: read-only FastAPI; apps/web/: React/TypeScript research terminal.
- tests/: integrity and API tests; apps/web/e2e/: real browser and accessibility tests.
- docs/: decisions, schemas, sources and operations.

## Workflow
- main is the integration branch. Use feat/<topic>, fix/<topic>, or docs/<topic> branches and focused commits.
- Open a PR, run CI, review the diff, then squash merge. Never force-push main.
- The current GitHub plan does not support branch protection on this private repository. Keep visibility as explicitly authorized by the owner (public approved 2026-10-23). After reviewing the diff, use scripts/merge-pr.ps1 to require successful CI and match the reviewed head SHA.
- Preserve unrelated changes. Coordinate file ownership before multiple agents edit the same files.
- Update STATUS.md with evidence, remaining work and next action in every meaningful handoff.
- Do not claim tests passed unless you ran them on the current revision.

## Cross-model code review
Multiple AI agents work on this repository, sequentially or simultaneously. No commit
merges on its own model's approval alone.

- Every commit trailer must name its authoring model: `Co-Authored-By: Claude ... <noreply@anthropic.com>`,
  `Co-Authored-By: Codex ... <noreply@openai.com>` or `Co-Authored-By: Gemini ... <noreply@google.com>`.
  Commits with no such trailer are human-authored, are not required to go through this
  gate, and may still be reviewed on request with `-Reviewer`.
- **The reviewer pool is `gemini`, `codex`, `claude`, `grok`** (tried in that order). Gemini goes
  first because commits here are authored by Claude or Codex, never Gemini, so it always
  gives an independent third opinion instead of one authoring model reviewing the other.
  The rule is "reviewed by a model that did not write it", never "reviewed by one specific
  model": any pool member that did not co-author the commits may satisfy the gate, and if
  Gemini is unavailable the fallback is whichever of Codex/Claude did NOT write the commit.
  Pinning this to a single provider meant one usage limit blocked every PR that model
  had written.
- Before merging, run `scripts/cross-review.ps1 -Number <PR>`. It reads the trailers,
  excludes the authoring model(s), and tries the remaining reviewers in pool order until
  one completes a review, posting its verdict as a marker comment that records which
  model gave it. A reviewer that cannot run — usage limit, crash, unparseable output —
  is neither an approval nor a rejection: the script says so and falls through to the
  next. If none can run, nothing is approved and the gate stays shut.
- A completed review **stops the search**, whether it approves or rejects. Re-running to
  find a friendlier model is not a way past a rejection.
- `scripts/merge-pr.ps1` merges only when some eligible reviewer has approved the exact
  current head **and** no eligible reviewer has an unresolved blocking finding on it.
  One reviewer's approval never overrides another's rejection. Pushing a fix moves the
  head, which retires the old rejection — so the way past a rejection is to address it.
- Findings are `blocking` (a correctness bug, a violation of a boundary in this file, a
  security issue, or a missing test for risk-affecting behavior — must be fixed, or
  rebutted and re-reviewed, before merge) or `advisory` (style/simplification — worth
  reading, never blocking). Never hand-edit or delete a review comment to open the gate.
- If a finding is a false positive, reply in the PR thread with the reasoning, then
  re-run with `-Rebuttal "<why it doesn't apply>"`. The reviewing model reconsiders and
  issues a fresh verdict; nothing bypasses this locally.
- **Grok is the last-resort backup** (owner decision, 2026-09-30): it is tried only when
  every other eligible reviewer is unavailable, so one provider's outage or quota never
  leaves the gate with nobody to ask. It is pinned to `grok-4.7` (xAI's newest, frontier
  model) and takes `reasoning_effort` (`high` for critical/standard, `low` for low tier,
  confirmed live), so it is eligible on critical diffs too. It runs through the xAI API,
  not a CLI: it has no repository access at all and reviews from AGENTS.md plus the full
  diff in the prompt. `scripts/cross-review.ps1` reads `XAI_API_KEY` from the environment
  or this repository's `.env` (never echoed) and fails closed if the response names any
  model other than the pinned one. Commits co-authored by Grok/xAI exclude it as usual.
- Keep every pool member frontier-class. A weak reviewer that rubber-stamps is worse
  than a blocked PR: it launders false confidence into the audit trail while catching
  nothing. Waiting for a usage limit to reset is an acceptable outcome; lowering the bar
  to avoid waiting is not. If a weaker model is ever added, gate it so it cannot be the
  sole reviewer for changes touching the critical paths listed below, by adding it to `$script:CriticalTierExcluded`. Gemini 3.8 Flash at high
  effort is NOT gated: the owner accepted it as a sole reviewer for every tier, critical
  included (2026-10-20), after it blocked a planted bug in a live test.
- **Blast-radius tiering** (`Get-BlastRadiusTier` in `scripts/lib/cross-review.ps1`)
  classifies the changed files into `critical` / `standard` / `low`, which
  `Get-ReviewerEffort` and `Get-ReviewerModel` both key off (below). `critical` (any of
  `packages/data/`, `packages/shared/`, `packages/research/`, `packages/backtest/`,
  `packages/pipeline.py`, `apps/api/`, `scripts/`, `.github/workflows/`) is meant to
  get each CLI's highest effort, though the owner-chosen per-tier settings below (see
  `Get-ReviewerEffort`) may deliberately fall short of that ceiling for cost reasons —
  `Get-BlastRadiusTier` only computes the tier, it does not guarantee an effort level.
  Reviewers listed in `$script:CriticalTierExcluded` may not decide a critical diff; the
  list is currently empty, so critical diffs go to Gemini first like every other tier
  (owner decision, 2026-10-20). `low` (prose-only: `*.md`,
  `docs/`, `*.css`, non-workflow `.github/`, or an ADDITIVE-only diff to `tests/` or
  `apps/web/e2e/`) gets reduced effort. A test-path file with ANY deleted line — a
  removed or weakened test — is never `low`: that is exactly the "missing test for
  risk-affecting behavior" category this contract calls blocking, so lowering scrutiny
  on it would be self-defeating. A file the deletion count could not be confirmed for
  is treated the same way, per this project's own rule against trusting missing data.
  Everything else is `standard`. The computed tier and per-reviewer effort are printed
  and recorded in the posted PR comment.
- **The model is pinned per reviewer per tier** in `$script:ReviewerModels`, because none
  of these CLIs guarantee a specific model on their own: Antigravity's `agy` uses whatever
  model its IDE last selected, and Codex takes its default from a mutable
  `~/.codex/config.toml`. Either could silently answer with a different model than
  intended, whose APPROVE would still satisfy the gate. Command-line arguments outrank
  both. A pinned model the account cannot use makes the CLI fail, so the reviewer reports
  unavailable and the pool falls past it — fail-closed. `agy` also reports the model it
  loaded, and the review fails closed if that is not the pin. Update the pins when a
  provider renames a model (`agy models` lists Antigravity's).
- **Reasoning effort is tuned by tier** (owner decision, 2026-09-14; a same-day
  critical-tier `gpt-5.6-sol`/`high` experiment for Codex was reverted the same day as
  overkill in the other direction):
  - **Codex** stays on `gpt-6-astra` (OpenAI's most capable) at every tier, but runs it
    at `low` ("light") effort across the board — including the **critical** tier. This
    means Codex gives app/risk.py-class changes no more scrutiny than a docs-only diff;
    the owner made this call explicitly, aware that it flattens the tiering's effect for
    Codex specifically. If review quality on critical-path changes ever looks weaker than
    expected, this is the first thing to reconsider.
  - **Claude** stays on `opus` at every tier; effort is `medium` for critical
    (previously `max`), unchanged `medium`/`low` for standard/low.
  - Both `-c model_reasoning_effort=<level>` (Codex) and `--effort <level>` (Claude) were
    confirmed live for every level used, including that `gpt-6-astra` accepts up to
    `ultra` and Claude's `opus` accepts up to `max` — those ceilings are documented, not
    currently used.
  - **Gemini** runs `gemini-3.8-flash-high` with `--effort high` on critical and standard
    diffs and `gemini-3.8-flash-medium` with `--effort medium` on low ones (confirmed live
    2026-10-20). Flash is the only Gemini model Antigravity offers on the owner's account;
    move critical to a Pro model here if one appears in `agy models`.
- Reviewer setup: `codex` and `claude` authenticate through their own CLIs; `grok` needs
  only `XAI_API_KEY` (environment or `.env`). **`gemini` runs through the Antigravity CLI
  (`agy`)** on the owner's Google login (owner decision, 2026-10-20): install Google
  Antigravity and sign in once; `agy` lives in `~/.gemini/bin` and need not be on PATH.
  The Gemini CLI is no longer used: its Google login stopped working for individual/Pro
  accounts on 2026-06-18, and its API-key path returned 429 (no quota for the pinned Pro
  model) on every review. `agy` takes the prompt on stdin as one stream-json message,
  runs in `--mode plan --sandbox` (confirmed read-only: a run told to write, delete and
  run a command did none of them), and is told commands are disabled, because a denied
  command otherwise ends its turn with an empty answer.
- Known limitation: Codex CLI's sandbox backend is currently disabled on Windows, so
  reviewing as Codex requires `--dangerously-bypass-approvals-and-sandbox` to read the
  repository at all. It is scoped by instructing the reviewer that it is read-only and
  must not modify, stage, commit or push anything; that instruction is not sandbox-enforced
  the way Claude's `--restricted` and Gemini's `agy --mode plan` are. Revisit once
  Codex ships Windows sandboxing.
- **Reviewers run with no MCP servers** (`Get-ReviewerNoMcpArguments`). The owner's
  everyday MCP registrations (REA, claude.ai connectors such as Gmail) would otherwise
  load into every review: extra startup time, an extra way for a reviewer to report
  unavailable, and tools that reach outside the repository. Claude gets
  `--strict-mcp-config`; `agy` has no per-run switch, so Gemini reports unavailable unless
  `agy mcp list` and `agy plugin list` show none configured; and Codex
  `-c mcp_servers.<name>.enabled=false` for each server `codex mcp list --json` reports
  (`-c mcp_servers={}` merges and disables nothing). If that listing cannot be read,
  Codex reports unavailable rather than review with servers that may still load.

## Commands
- `uv sync --locked`; `npm --prefix apps/web ci`
- `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy packages apps/api`
- `uv run pytest --cov=packages --cov=apps/api --cov-report=xml`
- `pwsh -NoProfile -File scripts/cross-review-selftest.ps1`; `uv run python scripts/validate_skills.py`
- `uv run baghunter demo`; `uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`
- `npm --prefix apps/web run dev`; `npm --prefix apps/web run lint`; `npm --prefix apps/web run typecheck`
- `npm --prefix apps/web run build`; `npm --prefix apps/web run test:e2e`
- `pwsh -NoProfile -File scripts/qa.ps1` runs local acceptance gates. No deployment target yet.

## Boundaries and definition of done
- Research and simulation only. No broker orders, subscriptions, spending or automatic deployment.
- Never invent empirical market evidence; fixtures must remain labeled and separate from real data.
- Facts must respect filing acceptance/publication plus processing lag. Never use hindsight labels in predictors.
- Missing returns, costs, delist proceeds and provider entitlements must be explicit; no optimistic fallback.
- Critical regexes are exactly: `^packages/data/`, `^packages/shared/`, `^packages/research/`, `^packages/backtest/`, `^packages/pipeline\.py$`, `^apps/api/`, `^scripts/`, `^\.github/workflows/`.
- Changes to critical paths require tests that exercise their boundaries.
- UI flows require real browser tests.
- No credentials, account numbers or tokens in commits or logs.
- Never claim tests passed unless they ran on the current revision.
- Done means documented startup, passing relevant tests/types/lint, reviewed diff and truthful limitations.
