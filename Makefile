.PHONY: help dev prod build up down logs clean install shopify-check security-scan audit backup restore

# Default target
help:
	@echo "DropKit Development Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment"
	@echo "  make install      - Install dependencies"
	@echo "  make shopify-check - Test Shopify connection"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start production environment"
	@echo "  make build        - Build all Docker images"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo ""
	@echo "Security:"
	@echo "  make security-scan - Run security vulnerability scans"
	@echo "  make audit        - Run security audit"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs         - Show logs from all services"
	@echo "  make health       - Check service health"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean        - Clean up containers and volumes"
	@echo "  make backup       - Backup MongoDB data"
	@echo "  make restore      - Restore MongoDB data"
	@echo ""

# Development environment
dev: install security-check
	@echo "Starting DropKit development environment..."
	@if [ ! -f .env ]; then \
		echo "⚠️  Creating .env from .env.example"; \
		cp .env.example .env; \
		echo "❗ SECURITY WARNING: Update .env with secure passwords before production!"; \
	fi
	docker-compose up --build

# Production environment
prod: security-check
	@echo "Starting DropKit production environment..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Create it from .env.example and configure secure values."; \
		exit 1; \
	fi
	@$(MAKE) audit
	docker-compose up -d --build

# Security check before startup
security-check:
	@echo "🔒 Running security checks..."
	@if [ -f .env ] && grep -q "CHANGE_THIS" .env; then \
		echo "❌ SECURITY RISK: Default passwords found in .env file!"; \
		echo "   Update all CHANGE_THIS values with secure credentials."; \
		exit 1; \
	fi
	@if [ -f .env ] && grep -q "your-" .env; then \
		echo "⚠️  WARNING: Placeholder values found in .env file"; \
		echo "   Make sure to replace 'your-*' values with actual credentials"; \
	fi

# Build all images
build:
	@echo "Building Docker images..."
	docker-compose build --no-cache

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

# Check service health
health:
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "Backend health:"
	@curl -f http://localhost:8000/health 2>/dev/null && echo "✅ Backend healthy" || echo "❌ Backend unhealthy"
	@echo "Frontend health:"
	@curl -f http://localhost:3000/health 2>/dev/null && echo "✅ Frontend healthy" || echo "❌ Frontend unhealthy"

# Clean up
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v --remove-orphans
	docker system prune -f

# Install dependencies
install:
	@echo "Installing frontend dependencies..."
	cd frontend && npm ci --audit
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt --upgrade

# Test Shopify connection
shopify-check:
	@echo "Testing Shopify connection..."
	cd backend && python scripts/test_shopify.py

# Security scan
security-scan:
	@echo "🔒 Running security scans..."
	@echo "Scanning Docker images for vulnerabilities..."
	@command -v trivy >/dev/null 2>&1 || { echo "Installing Trivy..."; curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin; }
	@trivy image --severity HIGH,CRITICAL dropkit-backend:latest || true
	@trivy image --severity HIGH,CRITICAL dropkit-frontend:latest || true
	@echo "Scanning dependencies..."
	@cd frontend && npm audit --audit-level high || true
	@cd backend && pip-audit || pip install pip-audit && pip-audit || true

# Security audit
audit:
	@echo "🔍 Running security audit..."
	@echo "Checking file permissions..."
	@find . -name "*.env*" -exec ls -la {} \; | grep -v "rw-------" && echo "⚠️  Environment files should have 600 permissions" || echo "✅ Environment file permissions OK"
	@echo "Checking for secrets in code..."
	@grep -r "password\|secret\|key" --include="*.py" --include="*.js" --include="*.jsx" . | grep -v "# " | head -5 || echo "✅ No obvious secrets in code"
	@echo "Checking Docker security..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy config . || echo "⚠️  Install Trivy for Docker security scanning"

# Backup MongoDB
backup:
	@echo "Creating MongoDB backup..."
	@mkdir -p ./backups
	@docker-compose exec -T mongodb mongodump --authenticationDatabase admin -u admin -p password --out /tmp/backup
	@docker cp dropkit-mongo:/tmp/backup ./backups/mongodb-$(shell date +%Y%m%d-%H%M%S)
	@echo "✅ Backup completed in ./backups/"

# Restore MongoDB
restore:
	@echo "Available backups:"
	@ls -la ./backups/ 2>/dev/null || echo "No backups found"
	@echo "To restore, run: docker-compose exec mongodb mongorestore --authenticationDatabase admin -u admin -p password /path/to/backup"
