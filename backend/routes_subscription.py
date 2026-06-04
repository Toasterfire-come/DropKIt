"""Subscription management routes — pause, resume, cancel, update shipping.

Wired to Stripe Billing when configured; falls back to local MongoDB state
for development / waitlist mode.

Routes expect the user to be authenticated (any role).
"""
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from config import settings
from db import get_db
from models import serialize

router = APIRouter(prefix="/subscription")


class SubscriptionInfo(BaseModel):
    status: str
    plan: str
    next_billing_date: Optional[str] = None
    shipping_address: Optional[dict] = None
    stripe_connected: bool = False


class AddressUpdate(BaseModel):
    street1: str
    street2: Optional[str] = None
    city: str
    state: str
    zip: str
    phone: Optional[str] = None


@router.get("")
async def get_subscription(user: dict = Depends(get_current_user)):
    """Return the current user's subscription status and details."""
    db = get_db()
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "status": u.get("subscriptionStatus", "inactive"),
        "plan": "Monthly Hardware Box",
        "price_cents": 4000,
        "next_billing_date": u.get("nextBillingDate"),
        "shipping_address": u.get("shipping_address"),
        "stripe_connected": bool(settings.STRIPE_SECRET_KEY and not settings.STRIPE_SECRET_KEY.startswith("PLACEHOLDER")),
        "stripe_customer_id": u.get("stripeCustomerId"),
    }


@router.post("/pause")
async def pause_subscription(user: dict = Depends(get_current_user)):
    """Pause the user's subscription. Calls Stripe if configured, else local."""
    db = get_db()
    u = await db.users.find_one({"_id": ObjectId(user["id"])})

    if not u or u.get("subscriptionStatus") not in ("active",):
        raise HTTPException(status_code=400, detail="Subscription is not active")

    stripe_customer = u.get("stripeCustomerId")
    if stripe_customer and settings.STRIPE_SECRET_KEY and not settings.STRIPE_SECRET_KEY.startswith("PLACEHOLDER"):
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            # Find the subscription and pause it
            subs = stripe.Subscription.list(customer=stripe_customer, limit=1, status="active")
            if subs.data:
                stripe.Subscription.modify(subs.data[0].id, pause_collection={"behavior": "void"})
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Stripe pause failed: {e}")

    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"subscriptionStatus": "paused", "updatedAt": datetime.now(timezone.utc)}},
    )
    return {"status": "paused"}


@router.post("/resume")
async def resume_subscription(user: dict = Depends(get_current_user)):
    """Resume a paused subscription."""
    db = get_db()
    u = await db.users.find_one({"_id": ObjectId(user["id"])})

    if not u or u.get("subscriptionStatus") not in ("paused", "inactive"):
        raise HTTPException(status_code=400, detail="Subscription is not paused")

    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"subscriptionStatus": "active", "updatedAt": datetime.now(timezone.utc)}},
    )
    return {"status": "active"}


@router.post("/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    """Cancel the subscription at period end."""
    db = get_db()
    u = await db.users.find_one({"_id": ObjectId(user["id"])})

    if not u or u.get("subscriptionStatus") not in ("active", "paused"):
        raise HTTPException(status_code=400, detail="Subscription is not active or paused")

    stripe_customer = u.get("stripeCustomerId")
    if stripe_customer and settings.STRIPE_SECRET_KEY and not settings.STRIPE_SECRET_KEY.startswith("PLACEHOLDER"):
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            subs = stripe.Subscription.list(customer=stripe_customer, limit=1, status="active")
            if subs.data:
                stripe.Subscription.modify(subs.data[0].id, cancel_at_period_end=True)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Stripe cancel failed: {e}")

    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"subscriptionStatus": "cancelled", "updatedAt": datetime.now(timezone.utc)}},
    )
    return {"status": "cancelled"}


@router.put("/address")
async def update_shipping_address(payload: AddressUpdate, user: dict = Depends(get_current_user)):
    """Update the shipping address on the user's account and subscription."""
    db = get_db()
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    addr = payload.model_dump()
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"shipping_address": addr, "updatedAt": datetime.now(timezone.utc)}},
    )
    return {"shipping_address": addr}