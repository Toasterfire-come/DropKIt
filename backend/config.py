"""DropKit backend configuration loaded from environment."""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Environment
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")  # development | production

    # Database — safe defaults so config never crashes on missing .env keys
    MONGO_URL: str = os.environ.get("MONGODB_URL", "mongodb://localhost:***@dropkit.local")
    DB_NAME: str = os.environ.get("DB_NAME", "dropkit_dev")

    # CORS origins: comma-separated list
    CORS_ORIGINS: str = os.environ.get(
        "CORS_ORIGINS",
        "https://drop-kit.app,https://dropkit.me,http://localhost:3000,http://127.0.0.1:3000"
    )

    # Shopify
    SHOPIFY_API_KEY: str = os.environ.get("SHOPIFY_API_KEY", "")
    SHOPIFY_API_SECRET: str = os.environ.get("SHOPIFY_API_SECRET", "")
    SHOPIFY_WEBHOOK_SECRET: str = os.environ.get("SHOPIFY_WEBHOOK_SECRET", "")
    SHOPIFY_STORE_DOMAIN: str = os.environ.get("SHOPIFY_STORE_DOMAIN", "")
    SHOPIFY_ADMIN_ACCESS_TOKEN: str = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "")
    SHOPIFY_API_VERSION: str = os.environ.get("SHOPIFY_API_VERSION", "2025-01")
    SHOPIFY_SCOPES: str = os.environ.get("SHOPIFY_SCOPES", "")
    SHOPIFY_SUBSCRIPTION_VARIANT_ID: str = os.environ.get("SHOPIFY_SUBSCRIPTION_VARIANT_ID", "")
    SHOPIFY_SUBSCRIPTION_SELLING_PLAN_ID: str = os.environ.get("SHOPIFY_SUBSCRIPTION_SELLING_PLAN_ID", "")
    SHOPIFY_SUBSCRIPTION_PRODUCT_GID: str = os.environ.get("SHOPIFY_SUBSCRIPTION_PRODUCT_GID", "")
    SHOPIFY_CUSTOMER_OAUTH_CLIENT_ID: str = os.environ.get("SHOPIFY_CUSTOMER_OAUTH_CLIENT_ID", "")
    SHOPIFY_CUSTOMER_OAUTH_CLIENT_SECRET: str = os.environ.get("SHOPIFY_CUSTOMER_OAUTH_CLIENT_SECRET", "")
    SHOPIFY_CUSTOMER_OAUTH_REDIRECT_URI: str = os.environ.get("SHOPIFY_CUSTOMER_OAUTH_REDIRECT_URI", "")
    SHOPIFY_CUSTOMER_SHOP_ID: str = os.environ.get("SHOPIFY_CUSTOMER_SHOP_ID", "")

    # Stripe
    STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_ENABLED: bool = bool(
        os.environ.get("STRIPE_SECRET_KEY") and os.environ.get("STRIPE_WEBHOOK_SECRET")
    )

    # App
    APP_URL: str = os.environ.get("APP_URL", "")
    ADMIN_API_TOKEN: str = os.environ.get("ADMIN_API_TOKEN", "")
    LAUNCH_MODE: str = os.environ.get("LAUNCH_MODE", "waitlist")  # waitlist | live

    # Auth
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "") or "dev-insecure-jwt-secret-do-not-use-in-production"
    DEV_EMAIL: str = os.environ.get("DEV_EMAIL", "dev@dropkit.local")
    DEV_PASSWORD: str = os.environ.get("DEV_PASSWORD", "devpassword123")
    DEV_NAME: str = os.environ.get("DEV_NAME", "DropKit Dev")

    # EasyPost (shipping)
    EASYPOST_API_KEY: str = os.environ.get("EASYPOST_API_KEY", "")

    # SendGrid (email — preferred over Gmail SMTP when set)
    SENDGRID_API_KEY: str = os.environ.get("SENDGRID_API_KEY", "")

    # Stripe Tax
    STRIPE_TAX_ENABLED: bool = (
        os.environ.get("STRIPE_TAX_ENABLED", "false").lower() == "true"
        and bool(os.environ.get("STRIPE_SECRET_KEY"))
    )

    # Gmail OAuth
    GMAIL_USER: str = os.environ.get("GMAIL_USER", "")
    GMAIL_APP_PASSWORD: str = os.environ.get("GMAIL_APP_PASSWORD", "")
    GMAIL_CLIENT_ID: str = os.environ.get("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.environ.get("GMAIL_CLIENT_SECRET", "")
    GMAIL_REDIRECT_URI: str = os.environ.get("GMAIL_REDIRECT_URI", "")

    # Shipping origin (DropKit warehouse)
    SHIPPING_FROM_NAME: str = os.environ.get("SHIPPING_FROM_NAME", "DropKit Fulfillment")
    SHIPPING_FROM_COMPANY: str = os.environ.get("SHIPPING_FROM_COMPANY", "DropKit")
    SHIPPING_FROM_EMAIL: str = os.environ.get("SHIPPING_FROM_EMAIL", "")
    SHIPPING_FROM_PHONE: str = os.environ.get("SHIPPING_FROM_PHONE", "")
    SHIPPING_FROM_STREET1: str = os.environ.get("SHIPPING_FROM_STREET1", "")
    SHIPPING_FROM_CITY: str = os.environ.get("SHIPPING_FROM_CITY", "")
    SHIPPING_FROM_STATE: str = os.environ.get("SHIPPING_FROM_STATE", "")
    SHIPPING_FROM_ZIP: str = os.environ.get("SHIPPING_FROM_ZIP", "")

    # Default parcel dims (inches, ounces)
    DEFAULT_PARCEL_LENGTH: float = float(os.environ.get("DEFAULT_PARCEL_LENGTH", "9"))
    DEFAULT_PARCEL_WIDTH: float = float(os.environ.get("DEFAULT_PARCEL_WIDTH", "6"))
    DEFAULT_PARCEL_HEIGHT: float = float(os.environ.get("DEFAULT_PARCEL_HEIGHT", "3"))
    DEFAULT_PARCEL_WEIGHT: float = float(os.environ.get("DEFAULT_PARCEL_WEIGHT", "12"))

    # ── Runtime guard ──────────────────────────────────────────
    def guard(self) -> None:
        """Called once at startup in production to verify critical env vars.
        In waitlist mode, missing keys are tolerated — most services fall back
        to placeholder/mock mode automatically."""
        if self.LAUNCH_MODE != "live":
            return
        required = {
            "MONGODB_URL": self.MONGO_URL,
            "DB_NAME": self.DB_NAME,
            "JWT_SECRET": self.JWT_SECRET,
        }
        missing = [k for k, v in required.items() if not v or v.startswith("PLACEHOLDER")]
        if missing:
            import sys
            print(f"FATAL: Production mode requires these env vars: {', '.join(missing)}")
            sys.exit(1)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()