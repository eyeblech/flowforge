.PHONY: help install dev test lint clean run-example serve docker-build docker-up

help:
	@echo "FlowForge Development Commands:"
	@echo "  make install      - Install package dependencies"
	@echo "  make dev          - Install in editable mode with development dependencies"
	@echo "  make test         - Run test suite with pytest"
	@echo "  make run-example  - Run sample system health watchdog pipeline"
	@echo "  make serve        - Start web studio and webhook server on localhost:8000"
	@echo "  make docker-build - Build Docker container image"
	@echo "  make docker-up    - Run Docker Compose stack"
	@echo "  make clean        - Clean temporary build artifacts and caches"

install:
	pip install .

dev:
	pip install -e .[dev]

test:
	pytest -v tests/

run-example:
	flowforge run examples/02_system_health_watchdog.yaml

serve:
	flowforge serve --workflows-dir ./examples --port 8000

docker-build:
	docker build -t flowforge:latest .

docker-up:
	docker compose up -d

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache/ __pycache__ **/__pycache__
