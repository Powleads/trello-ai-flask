.PHONY: install dev test setup process watch clean lint format type-check

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest black isort mypy flake8

# Development
dev:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

dev-with-logs:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# Testing
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-coverage:
	pytest tests/ --cov=src --cov-report=html

# Setup and Configuration
setup:
	python src/cli.py setup

setup-google:
	python scripts/setup_google_auth.py

test-services:
	python src/cli.py test --service all

# CLI Operations
process:
	@if [ -z "$(FILE)" ]; then echo "Usage: make process FILE=path/to/transcript.txt"; exit 1; fi
	python src/cli.py process --file $(FILE)

process-example:
	python src/cli.py process --file examples/sample_transcript.txt

watch:
	@if [ -z "$(FOLDER)" ]; then echo "Usage: make watch FOLDER=path/to/folder"; exit 1; fi
	python src/cli.py watch --folder $(FOLDER)

watch-transcripts:
	python src/cli.py watch --folder ./transcripts

batch-process:
	@if [ -z "$(INPUT)" ] || [ -z "$(OUTPUT)" ]; then echo "Usage: make batch-process INPUT=input_dir OUTPUT=output_dir"; exit 1; fi
	python src/cli.py batch-process --input-dir $(INPUT) --output-dir $(OUTPUT)

# Code Quality
lint:
	flake8 src/ --max-line-length=100 --ignore=E203,W503

format:
	black src/ --line-length=100
	isort src/

format-check:
	black src/ --check --line-length=100
	isort src/ --check-only

type-check:
	mypy src/ --ignore-missing-imports

quality: format lint type-check

# Docker Operations
docker-build:
	docker build -t meeting-automation .

docker-run:
	docker run -p 8000:8000 --env-file .env meeting-automation

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

docker-compose-logs:
	docker-compose logs -f

# Database Operations
db-init:
	python scripts/init_database.py

db-migrate:
	alembic upgrade head

db-reset:
	python scripts/reset_database.py

# Monitoring and Logs
logs:
	tail -f logs/meeting_automation.log

logs-error:
	tail -f logs/error.log

monitor:
	python scripts/monitor_system.py

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

clean-downloads:
	rm -rf downloads/*
	rm -rf temp/*

clean-logs:
	rm -rf logs/*.log

clean-all: clean clean-downloads clean-logs

# Backup and Restore
backup:
	python scripts/backup_data.py

restore:
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Usage: make restore BACKUP_FILE=backup.tar.gz"; exit 1; fi
	python scripts/restore_data.py $(BACKUP_FILE)

# Production Deployment
deploy-staging:
	python scripts/deploy.py --environment staging

deploy-prod:
	python scripts/deploy.py --environment production

# Health Checks
health-check:
	python scripts/health_check.py

integration-test:
	python scripts/test_integration.py

# Performance Testing
load-test:
	python scripts/load_test.py

benchmark:
	python scripts/benchmark.py

# Documentation
docs:
	python scripts/generate_docs.py

docs-serve:
	mkdocs serve

# Security
security-scan:
	bandit -r src/

vulnerability-check:
	safety check

# Environment Management
env-check:
	python scripts/check_environment.py

env-setup:
	cp .env.example .env
	@echo "Please edit .env file with your API credentials"

# Quick Commands
quick-test: format lint test

quick-deploy: quality test deploy-staging

full-setup: install env-setup setup test-services

# Help
help:
	@echo "Available commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install          - Install dependencies"
	@echo "  install-dev      - Install with development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  dev              - Start development server"
	@echo "  test             - Run all tests"
	@echo "  setup            - Run interactive setup"
	@echo ""
	@echo "CLI Operations:"
	@echo "  process FILE=... - Process single transcript"
	@echo "  watch FOLDER=... - Monitor folder for new files"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             - Check code style"
	@echo "  format           - Format code"
	@echo "  type-check       - Run type checking"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     - Build Docker image"
	@echo "  docker-compose-up - Start with Docker Compose"
	@echo ""
	@echo "Utilities:"
	@echo "  clean            - Clean temporary files"
	@echo "  health-check     - Check system health"
	@echo "  help             - Show this help"