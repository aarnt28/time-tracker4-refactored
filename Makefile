.PHONY: dev up down fmt lint type test seed migrate rev

PY ?= python

dev:
$(PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8089

fmt:
ruff check --fix . && ruff format . && black .

lint:
ruff check .

audit:
bandit -c pyproject.toml -r app

type:
mypy app

test:
pytest -q

up:
docker compose up -d --build

down:
docker compose down -v

migrate:
alembic upgrade head

rev:
alembic revision --autogenerate -m "update"

seed:
$(PY) -m app.db.seed
