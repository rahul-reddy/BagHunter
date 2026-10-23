$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force artifacts/test_results | Out-Null
function Check([string]$Label, [scriptblock]$Command) {
    Write-Host "Checking $Label"
    & $Command 2>&1 | Tee-Object "artifacts/test_results/$Label.txt"
    if ($LASTEXITCODE -ne 0) { throw "$Label failed ($LASTEXITCODE)" }
}
Check 'install-python' { uv sync --locked }
Check 'install-web' { npm --prefix apps/web ci --no-fund }
Check 'harness' { pwsh -NoProfile -File scripts/cross-review-selftest.ps1 }
Check 'skills' { uv run python scripts/validate_skills.py }
Check 'lint' { uv run ruff check . }
Check 'format' { uv run ruff format --check . }
Check 'types' { uv run mypy packages apps/api }
Check 'unit-integration-pit' { uv run pytest --cov=packages --cov=apps/api --cov-report=xml --junitxml=artifacts/test_results/pytest.xml }
Check 'demo' { uv run baghunter demo }
Check 'web-lint' { npm --prefix apps/web run lint }
Check 'web-types' { npm --prefix apps/web run typecheck }
Check 'web-build' { npm --prefix apps/web run build }
Check 'browser' { npm --prefix apps/web run test:e2e }
Write-Host 'Local acceptance checks passed. CI and independent PR review are separate gates.'
