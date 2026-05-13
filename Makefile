.PHONY: help dev build up down logs clean install shopify-check

# Default target
help:
	@echo "DropKit Development Commands:"
	@echo ""
	@echo "  make dev          - Start development environment"
	@echo "  make build        - Build all Docker images"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Show logs from all services"
	@echo "  make clean        - Clean up containers and volumes"
	@echo "  make install      - Install dependencies"
	@echo "  make shopify-check - Test Shopify connection"
	@echo ""

# Development environment
dev: install
	@echo "Starting DropKit development environment..."
	docker-compose up --build

# Build all images
build:
	@echo "Building Docker images..."
	docker-compose build

# Start services
up:
	@echo "Starting services..."
	docker-compose up -d

# Stop services
down:
	@echo "Stopping services..."
	docker-compose down

# Show logs
logs:
	docker-compose logs -f

# Clean up
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v --remove-orphans
	docker system prune -f

# Install dependencies
install:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt

# Test Shopify connection
shopify-check:
	@echo "Testing Shopify connection..."
	cd backend && python scripts/test_shopify.py
