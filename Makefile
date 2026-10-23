.PHONY: bootstrap ingest-demo study-demo backtest-demo api web test test-pit lint typecheck build test-e2e qa
bootstrap:
	uv sync --locked
	npm --prefix apps/web ci
ingest-demo study-demo backtest-demo:
	uv run baghunter $@
api:
	uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
web:
	npm --prefix apps/web run dev
test:
	uv run pytest
test-pit:
	uv run pytest -k 'pit or future or amendment or symbol or incomplete or split'
lint:
	uv run ruff check .
	uv run ruff format --check .
	npm --prefix apps/web run lint
typecheck:
	uv run mypy packages apps/api
	npm --prefix apps/web run typecheck
build:
	npm --prefix apps/web run build
test-e2e:
	npm --prefix apps/web run test:e2e
qa:
	pwsh -NoProfile -File scripts/qa.ps1
