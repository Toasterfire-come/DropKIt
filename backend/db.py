"""MongoDB connection (Motor)."""
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL)
    return _client


def get_db():
    return get_client()[settings.DB_NAME]


async def ensure_indexes():
    db = get_db()
    # shopifyCustomerId: unique only when it's an actual string (partial filter
    # avoids the well-known sparse-index footgun where explicit nulls collide)
    await db.users.create_index(
        "shopifyCustomerId", unique=True,
        partialFilterExpression={"shopifyCustomerId": {"$type": "string"}},
    )
    await db.users.create_index("email", unique=True, sparse=True)
    await db.projects.create_index("slug", unique=True)
    await db.projects.create_index([("cycleYear", -1), ("cycleMonth", -1)])
    await db.projects.create_index("isActive")
    await db.vote_cycles.create_index([("cycleYear", -1), ("cycleMonth", -1)], unique=True)
    await db.votes.create_index([("userId", 1), ("voteCycleId", 1)], unique=True)
    await db.substitutions.create_index([("userId", 1), ("cycleMonth", 1), ("cycleYear", 1)])
    await db.gifts.create_index("code", unique=True)
    await db.waitlist.create_index("email", unique=True)
    await db.waitlist.create_index(
        "referralCode", unique=True,
        partialFilterExpression={"referralCode": {"$type": "string"}},
    )
    await db.waitlist.create_index("referredByCode")
    await db.login_attempts.create_index("identifier")
    await db.app_settings.create_index("key", unique=True)
    # Idempotency + ops indexes (items 1-15)
    await db.email_log.create_index("unique_id", unique=True, sparse=True)
    await db.email_log.create_index([("created_at", -1)])
    await db.replacement_requests.create_index([("status", 1), ("created_at", -1)])
    await db.webhook_failures.create_index([("created_at", -1)])
    await db.batch_labels.create_index([("created_at", -1)])
    await db.nexus_alerts.create_index([("state", 1), ("month", 1)], unique=True)
    await db.cycle_closes.create_index([("cycle_label", 1)], unique=True)
