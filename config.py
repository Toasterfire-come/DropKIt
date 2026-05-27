"""DropKit backend configuration loaded from environment."""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Environment
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")  # development | production

    # Database
    MONGO_URL: str = os.environ["MONGODB_URL"]
    DB_NAME: str = os.environ["DB_NAME"]
    # CORS origins: comma-separated list
    CORS_ORIGINS: str = os.environ.get(
        "CORS_ORIGINS",
        "https://dropkit.me,http://localhost:3000,http://127.0.0.1:3000"
    )

    # Shopify
    SHOPIFY_API_KEY: str = os.environ.get("SHOPIFY_API_KEY", "")
    SHOPIFY_API_SECRET: str = os.environ.get("SHOPIFY_API_SECRET", "")
    SHOPIFY_WEBHOOK_SECRET: str = os.environ.get("SHOPIFY_WEBHOOK_SECRET", "")
    SHOPIFY_STORE_DOMAIN: str = os.environ.get("SHOPIFY_STORE_DOMAIN", "")
    SHOPIFY_ADMIN_ACCESS_TOKEN: str = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "")
    SHOPIFY_API_VERSION: str = os.environ.get("SHOPIFY_API_VERSION", "2025-01")
    SHOPIFY_SCOPES: str = os.environ.get("SHOPIFY_SCOPES", "")
    # Subscription product wiring (set after creating the product + selling plan in Shopify Admin)
    SHOPIFY_SUBSCRIPTION_VARIANT_ID: str = os.environ.get("SHOPIFY_SUBSCRIPTION_VARIANT_ID", "")
    SHOPIFY_SUBSCRIPTION_SELLING_PLAN_ID: str = os.environ.get("SHOPIFY_SUBSCRIPTION_SELLING_PLAN_ID", "")
    SHOPIFY_SUBSCRIPTION_PRODUCT_GID: str = os.environ.get("SHOPIFY_SUBSCRIPTION_PRODUCT_GID", "")
    # Customer Accounts OAuth (Shopify "new customer accounts")
    SHOPIFY_CUSTOMER_OAUTH_CLIENT_ID: str = os.environ.get("SHOPIFY_CUSTOMER_OAUTH_CLIENT_ID", "")
    SHOPIFY_CUSTOMER_OAUTH_CLIENT_SECRET: str = os.environ.get("SHOPIFY_CUSTOMER_OAUTH_CLIENT_SECRET", "")
    SHOPIFY_CUSTOMER_OAUTH_REDIRECT_URI: str = os.environ.get("SHOPIFY_CUSTOMER_OAUTH_REDIRECT_URI", "")
    SHOPIFY_CUSTOMER_SHOP_ID: str = os.environ.get("SHOPIFY_CUSTOMER_SHOP_ID", "")

    # Stripe (via Shopify Payments — used for direct verification only)
    STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    # STRIPE_ENABLED is now determined by the presence of both keys.
    STRIPE_ENABLED: bool = bool(STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET)

    # App
    APP_URL: str = os.environ.get("APP_URL", "")
    ADMIN_API_TOKEN: str = os.environ.get("ADMIN_API_TOKEN", "")
    LAUNCH_MODE: str = os.environ.get("LAUNCH_MODE", "waitlist")  # waitlist | live

    # Auth
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "")
    DEV_EMAIL: str = os.environ.get("DEV_EMAIL", "")
    DEV_PASSWORD: str = os.environ.get("DEV_PASSWORD", "")
    DEV_NAME: str = os.environ.get("DEV_NAME", "DropKit Dev")

    # EasyPost (shipping)
    EASYPOST_API_KEY: str = os.environ.get("EASYPOST_API_KEY", "")

    # Stripe Tax
    # Stripe Tax is only enabled if Stripe is generally enabled and the specific env var is true.
    STRIPE_TAX_ENABLED: bool = os.environ.get("STRIPE_TAX_ENABLED", "false").lower() == "true" and STRIPE_ENABLED

    # Gmail OAuth
    GMAIL_USER: str = os.environ.get("GMAIL_USER", "dropkit.marketing@gmail.com")
    GMAIL_APP_PASSWORD: str = os.environ.get("GMAIL_APP_PASSWORD") # Note: This is an App Password, not a regular Google account password.
    GMAIL_CLIENT_ID: str = os.environ.get("GMAIL_CLIENT_ID")
    GMAIL_CLIENT_SECRET: str = os.environ.get("GMAIL_CLIENT_SECRET")
    GMAIL_REDIRECT_URI: str = os.environ.get("GMAIL_REDIRECT_URI", "") # This should be set in your Google Cloud Console

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
