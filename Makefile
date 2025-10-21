.PHONY: help setup up down logs clean install-shared test

help:
	@echo "CAVIA Development Commands"
	@echo ""
	@echo "  make setup          - Initial project setup"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make logs           - Show logs"
	@echo "  make clean          - Clean up data and containers"
	@echo "  make install-shared - Install shared package in dev mode"
	@echo "  make test           - Run tests"
	@echo "  make init-db        - Initialize database"
	@echo ""

setup:
	@echo "Setting up CAVIA..."
	cp -n .env.example .env || true
	@echo "Installing shared package..."
	cd shared/python && pip install -e .
	@echo "Setup complete! Edit .env if needed, then run 'make up'"

up:
	@echo "Starting services..."
	docker-compose up -d
	@echo "Services started! Check status with 'docker-compose ps'"

down:
	@echo "Stopping services..."
	docker-compose down

logs:
	docker-compose logs -f

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	rm -rf data/cvs-raw/* data/cvs-processed/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleaned!"

install-shared:
	@echo "Installing shared package in dev mode..."
	cd shared/python && pip install -e ".[dev]"

test:
	@echo "Running tests..."
	pytest tests/ -v --cov=cavia_common --cov-report=html

init-db:
	@echo "Initializing database..."
	docker-compose exec postgres psql -U cavia -d cavia -f /docker-entrypoint-initdb.d/init-db.sql
