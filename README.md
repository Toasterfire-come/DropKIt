# DropKit

A modern e-commerce platform for electronics components and kits.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### One-Command Startup

```bash
make dev
```

This will:
- Install all dependencies
- Build and start all services (MongoDB, Backend, Frontend, Cloudflare Tunnel)
- Set up the complete development environment

### Available Commands

```bash
make help          # Show all available commands
make dev           # Start development environment
make build         # Build all Docker images
make up            # Start all services
make down          # Stop all services
make logs          # Show logs from all services
make clean         # Clean up containers and volumes
make install       # Install dependencies
make shopify-check # Test Shopify connection
```

## Architecture

- **Frontend**: React app with Tailwind CSS and Radix UI components
- **Backend**: FastAPI with MongoDB
- **Database**: MongoDB
- **Tunnel**: Cloudflare Tunnel for secure public access

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the environment variables in `.env` with your actual values

3. For Cloudflare Tunnel, place your credentials in `cloudflared/credentials.json`

## Development

### Local Development (without Docker)

Frontend:
```bash
cd frontend
npm install
npm start
```

Backend:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Testing Shopify Integration

```bash
make shopify-check
```

## Deployment

The application is configured for deployment with:
- Domain: `dropkit.me`
- Frontend served at root
- API endpoints at `/api/*`
- Cloudflare Tunnel for secure access

## Health Monitoring

Health check endpoints are available when `ENABLE_HEALTH_CHECK=true`:
- `/health` - Application health status
- Development webpack compilation status
