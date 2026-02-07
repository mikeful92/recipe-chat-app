.PHONY: install dev test lint fmt type ci

install:
	pip install -r requirements-dev.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -q

lint:
	ruff check .

fmt:
	ruff format .

type:
	pyright

ci: lint type test
