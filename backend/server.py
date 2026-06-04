"""DropKit FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import ensure_indexes
from routes_public import router as public_router
from routes_admin import router as admin_router
from routes_webhooks import router as webhooks_router
from routes_auth import router as auth_router
from routes_checkout import router as checkout_router
from routes_dev import router as dev_router
from routes_dev_ops import router as dev_ops_router
from routes_inventory import router as inventory_router
from routes_seo import router as seo_router
from routes_shopify_auth import router as shopify_auth_router
from routes_subscription import router as subscription_router
from routes_gallery import router as gallery_router
from auth import seed_dev_user
from seed_projects import seed_safekeyvault


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    log = logging.getLogger("dropkit")
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


app = FastAPI(title="DropKit API", version="1.0.0", lifespan=lifespan)

# CORS configuration
# If allow_credentials is True, the wildcard '*' for origins is not allowed.
# We must provide a list of explicit origins.
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

# If no explicit origins are provided, default to allowing localhost:3000 for development
# and a wildcard for production if needed (though explicit is better).
if not origins:
    if settings.ENVIRONMENT == "development":
        origins = ["http://localhost:3000"]
    else:
        # In production, it's best to list specific allowed origins.
        # Using a wildcard here as a fallback, but consider refining this.
        origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"service": "DropKit API", "status": "ok"}


@api.get("/health")
async def health():
    return {"status": "ok"}


api.include_router(public_router)
api.include_router(auth_router)
api.include_router(shopify_auth_router)
api.include_router(checkout_router)
api.include_router(dev_router)
api.include_router(dev_ops_router)
api.include_router(inventory_router)
api.include_router(seo_router)
api.include_router(subscription_router)
api.include_router(gallery_router)
api.include_router(admin_router)
api.include_router(webhooks_router)

app.include_router(api)
