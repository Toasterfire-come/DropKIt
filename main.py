"""DropKit FastAPI application entry point."""
from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import seed_dev_user
from config import settings
from db import ensure_indexes
from routes_auth import router as auth_router
from routes_checkout import router as checkout_router
from routes_dev import router as dev_router
from routes_dev_ops import router as dev_ops_router
from routes_inventory import router as inventory_router
from routes_public import router as public_router
from routes_seo import router as seo_router
from routes_shopify_auth import router as shopify_auth_router
from routes_webhooks import router as webhooks_router
from seed_projects import seed_safekeyvault

log = logging.getLogger("dropkit")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic for the FastAPI application."""
    if settings.SHOPIFY_WEBHOOK_SECRET.startswith("PLACEHOLDER"):
        log.warning(
            "SHOPIFY_WEBHOOK_SECRET is a placeholder — webhook HMAC verification is BYPASSED. "
            "Replace with a real secret before production deploy."
        )
    if settings.SHOPIFY_ADMIN_ACCESS_TOKEN.startswith("PLACEHOLDER"):
        log.warning(
            "SHOPIFY_ADMIN_ACCESS_TOKEN is a placeholder — Admin API calls will fail. "
            "Replace with a real token before production deploy."
        )
    await ensure_indexes()
    await seed_dev_user()
    await seed_safekeyvault()
    yield

app = FastAPI(
    title="DropKit API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()] or ["*"],
    allow_origin_regex=r"https://.*\.preview\.emergentagent\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")

@api.get("/")
async def root():
    """Root endpoint for API."""
    return {"service": "DropKit API", "status": "ok"}

@api.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

# Include all routers
api.include_router(public_router)
api.include_router(auth_router)
api.include_router(shopify_auth_router)
api.include_router(checkout_router)
api.include_router(dev_router)
api.include_router(dev_ops_router)
api.include_router(inventory_router)
api.include_router(seo_router)
api.include_router(webhooks_router)

app.include_router(api)

# Add uvicorn reload support if running locally and not in a container
if __name__ == "__main__":
    import uvicorn
    # Check if running in a container environment (e.g., Docker)
    # If not, enable reload for local development
    if os.environ.get("RUNNING_IN_CONTAINER") != "true":
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug", # Use debug for more verbose logging during development
        )
    else:
        # Production or containerized environment: run without reload
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            workers=1, # Adjust workers as needed for production
            log_level="info", # Use info for production logging
        )
