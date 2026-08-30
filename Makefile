.PHONY: install-dev test lint run-dev docker-up docker-down

install-dev:
	pip install -e shared/
	pip install -r services/orchestrator/requirements.txt
	cd apps/frontend && npm install

run-dev:
	docker compose up -d postgres redis
	cd services/orchestrator && uvicorn app.main:app --reload --port 8000

test:
	pytest tests/

docker-up:
	docker compose up --build

docker-down:
	docker compose down
