.PHONY: dev test lint format docker-build docker-run compose-up compose-down

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ --cov=app --cov-report=term-missing -q

lint:
	ruff check app/ tests/

format:
	ruff format app/ tests/

docker-build:
	docker build -t planner-agent:latest .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env planner-agent:latest

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down
