# Makefile for Appointment Booking System

.PHONY: help install dev test clean setup migrate seed docker-build docker-up docker-down

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

dev:  ## Run development server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:  ## Run tests
	pytest -v

test-cov:  ## Run tests with coverage
	pytest --cov=app tests/

clean:  ## Clean cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

setup:  ## Setup project (install + migrate + seed)
	make install
	make migrate
	make seed

migrate:  ## Run database migrations
	python scripts/create_tables.py

seed:  ## Seed database with sample data
	python scripts/seed_data.py

celery-worker:  ## Start Celery worker
	celery -A app.core.scheduler worker --loglevel=info

celery-beat:  ## Start Celery beat scheduler
	celery -A app.core.scheduler beat --loglevel=info

redis:  ## Start Redis server
	redis-server

docker-build:  ## Build Docker images
	docker-compose build

docker-up:  ## Start services with Docker
	docker-compose up -d

docker-down:  ## Stop Docker services
	docker-compose down

docker-logs:  ## View Docker logs
	docker-compose logs -f

docker-clean:  ## Clean Docker resources
	docker-compose down -v
	docker system prune -f

format:  ## Format code with black
	black app/ tests/ scripts/

lint:  ## Lint code with flake8
	flake8 app/ tests/ scripts/

check:  ## Run all checks (format, lint, test)
	make format
	make lint
	make test