---
name: baghunter-change-workflow
description: Implement, verify, review, and hand off code or documentation changes in the BagHunter repository. Use for BagHunter development work that should follow its branch, testing, status, cross-model review, and guarded-merge workflow; do not use for general investing research or ordinary questions about the project.
---

# BagHunter change workflow

Read `AGENTS.md`, `docs/PLAN.md`, and the current handoff at the top of `STATUS.md` before changing behavior. Treat the user's current instruction as authoritative within the safety boundaries in `AGENTS.md`.

Use a focused `feat/`, `fix/`, or `docs/` branch. Inspect the worktree before editing and preserve unrelated changes. When multiple agents work concurrently, declare file ownership using the repository's current coordination mechanism before editing shared files.

Keep policy and risk calculations deterministic. Do not let an AI-generated assertion become trusted evidence, approve an order, weaken a risk gate, or introduce broker transmission. Changes to risk behavior need boundary or property tests; UI flows need a real browser test.

Run checks that cover the changed behavior, then the repository-required lint, types, and tests when the change is ready. Do not claim a check passed unless it ran on the current revision. For harness changes, run:

```powershell
pwsh -NoProfile -File scripts/cross-review-selftest.ps1
uv run python scripts/validate_skills.py
```

Update the current handoff in `STATUS.md` with the exact revision or worktree state tested, commands run, results, limitations, and next action. Keep historical narrative below the handoff; do not make an agent reconstruct current state from the archive.

AI-authored commits must carry the appropriate `Co-Authored-By` trailer. When delivery is in scope, open a PR, wait for CI on the final head, run `scripts/cross-review.ps1 -Number <PR>`, address or rebut every blocking finding, and use `scripts/merge-pr.ps1 -Number <PR>` so the reviewed SHA and successful CI are enforced.
