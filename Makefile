# Multi-Agent Orchestration Platform Makefile

.PHONY: help install install-dev install-test clean test test-unit test-integration test-e2e test-contract lint format type-check docs build docker-build docker-run deploy dev-setup pre-commit ci

# Default target
help: ## Show this help message
	@echo "Multi-Agent Orchestration Platform"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"

install-test: ## Install test dependencies
	pip install -e ".[test]"

install-all: ## Install all dependencies
	pip install -e ".[all]"

# Cleaning
clean: ## Clean build artifacts and cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	rm -rf build/ dist/ htmlcov/ .coverage .coverage.*

# Testing
test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/unit/

test-integration: ## Run integration tests only
	pytest tests/integration/

test-e2e: ## Run end-to-end tests only
	pytest tests/e2e/

test-contract: ## Run contract tests only
	pytest tests/contract/

test-cov: ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term-missing

test-fast: ## Run tests in parallel (requires pytest-xdist)
	pytest -n auto

# Code Quality
lint: ## Run linting checks
	flake8 src/ tests/

format: ## Format code with black
	black src/ tests/

format-check: ## Check code formatting without making changes
	black --check --diff src/ tests/

type-check: ## Run type checking with mypy
	mypy src/

# Documentation
docs: ## Build documentation
	sphinx-build -b html docs/ docs/_build/html

docs-serve: ## Build and serve documentation locally
	sphinx-build -b html docs/ docs/_build/html
	cd docs/_build/html && python -m http.server 8000

# Building
build: ## Build distribution packages
	python -m build

build-sdist: ## Build source distribution
	python -m build --sdist

build-wheel: ## Build wheel distribution
	python -m build --wheel

# Docker
docker-build: ## Build Docker image
	docker build -t multi-agent-orchestration .

docker-run: ## Run Docker container
	docker run -p 8000:8000 -p 3000:3000 multi-agent-orchestration

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	docker-compose down

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

# Development
dev-setup: ## Set up development environment
	pre-commit install
	pre-commit run --all-files

dev-server: ## Start development server
	uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

dev-cli: ## Run CLI in development mode
	python -m src.cli.main --help

# Pre-commit
pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

# CI/CD
ci: ## Run full CI pipeline locally
	make clean
	make install-all
	make lint
	make type-check
	make test-cov
	make build

# Deployment
deploy-dev: ## Deploy to development environment
	@echo "Deploying to development environment..."
	# Add your deployment commands here

deploy-staging: ## Deploy to staging environment
	@echo "Deploying to staging environment..."
	# Add your deployment commands here

deploy-prod: ## Deploy to production environment
	@echo "Deploying to production environment..."
	# Add your deployment commands here

# Database/Storage (if applicable)
db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	# Add your migration commands here

db-reset: ## Reset database (dangerous!)
	@echo "Resetting database..."
	# Add your database reset commands here

# Utilities
shell: ## Start Python shell with project context
	python -c "import sys; sys.path.insert(0, '.'); from src.cli.main import app; app()"

version: ## Show current version
	@python -c "import toml; print(toml.load('pyproject.toml')['project']['version'])"

deps-update: ## Update dependencies
	pip-compile --upgrade pyproject.toml
	pip-compile --upgrade --extra dev pyproject.toml
	pip-compile --upgrade --extra test pyproject.toml

deps-sync: ## Sync dependencies with lock files
	pip-sync pyproject.toml requirements-dev.txt requirements-test.txt

# Health checks
health: ## Run health checks
	curl -f http://localhost:8000/health || echo "API not running"
	curl -f http://localhost:3000/health || echo "MCP server not running"

# Logs
logs: ## Show application logs
	docker-compose logs -f app

logs-api: ## Show API logs
	docker-compose logs -f api

logs-mcp: ## Show MCP server logs
	docker-compose logs -f mcp

# Backup/Restore
backup: ## Create backup of application data
	@echo "Creating backup..."
	# Add backup commands here

restore: ## Restore from backup
	@echo "Restoring from backup..."
	# Add restore commands here

# Security
security-scan: ## Run security vulnerability scan
	safety check
	bandit -r src/

# Performance
perf-test: ## Run performance tests
	@echo "Running performance tests..."
	# Add performance testing commands here

# Monitoring
metrics: ## Show application metrics
	@echo "Application metrics:"
	curl -s http://localhost:8000/metrics || echo "Metrics endpoint not available"

# Troubleshooting
doctor: ## Run diagnostics to check system health
	@echo "Running system diagnostics..."
	@echo "Python version: $$(python --version)"
	@echo "Pip version: $$(pip --version)"
	@echo "Docker version: $$(docker --version 2>/dev/null || echo 'Docker not installed')"
	@echo "Docker Compose version: $$(docker-compose --version 2>/dev/null || echo 'Docker Compose not installed')"
	@echo "Checking dependencies..."
	@python -c "import sys; deps = ['fastapi', 'typer', 'pydantic', 'anthropic']; [print(f'{dep}: OK') if __import__(dep) else print(f'{dep}: MISSING') for dep in deps]"