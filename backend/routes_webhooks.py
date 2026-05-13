"""Shopify webhook handler — HMAC-verified, topic-dispatched.

Topics handled per the MVP spec:
  - orders/paid                       → create Order in MongoDB, unlock voting
  - orders/cancelled                  → mark order cancelled
  - customers/create                  → upsert User in MongoDB
  - subscription_contracts/create     → store contract id on User
  - subscription_contracts/update     → sync status (active/paused/cancelled)
  - subscription_billing_cycles/skip  → mark cycle skipped, lock voting
"""
import secrets
import string
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request

from db import get_db
from config import settings
from shopify_client import verify_shopify_webhook, get_webhook_topic, get_webhook_shop_domain, shopify, shopify_is_configured
import email_service as mailer

router = APIRouter()
log = logging.getLogger("dropkit.webhooks")


def _cycle_key(dt: datetime) -> str:
    return f"{dt.year}-{dt.month:02d}"


def _gen_gift_code() -> str:
    chunk = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    year = datetime.now(timezone.utc).year
    return f"MAKER-{chunk}-{year}"


def _gen_reward_code(prefix: str = "MAKERMONTH") -> str:
    chunk = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"{prefix}-{chunk}"


# Reward configuration (one full month off subscription)
REFERRAL_THRESHOLD_PAID = 5
REWARD_AMOUNT_CENTS = 4000      # $40.00 = one month
REWARD_VALID_DAYS = 60


async def _grant_free_month_if_earned(db, referrer_doc: dict):
    """If the referrer hit 5 paid refs, is themselves active, and hasn't yet
    been rewarded — create a Shopify discount code and fire a Klaviyo event."""
    if referrer_doc.get("rewardGranted"):
        return
    if (referrer_doc.get("paidReferralCount") or 0) < REFERRAL_THRESHOLD_PAID:
        return

    user = await db.users.find_one({"email": referrer_doc.get("email")})
    if not user or user.get("subscriptionStatus") != "active":
        return  # referrer must themselves be paying

    code = _gen_reward_code()
    now = datetime.now(timezone.utc)
    ends_at = now + timedelta(days=REWARD_VALID_DAYS)
    shopify_result = None
    shopify_ok = True
    if shopify_is_configured():
        try:
            shopify_result = await shopify.create_referral_discount_code(
                code=code,
                amount_cents=REWARD_AMOUNT_CENTS,
                customer_gid=user.get("shopifyCustomerId"),
                product_gid=None,  # apply to any product; tighten by passing the subscription product GID via env if needed
                usage_limit=1,
                starts_at_iso=now.isoformat(),
                ends_at_iso=ends_at.isoformat(),
            )
            # Shopify returns userErrors in the response — treat non-empty as failure
            user_errors = (
                (shopify_result or {})
                .get("discountCodeBasicCreate", {})
                .get("userErrors", [])
            )
            if user_errors:
                log.error("Shopify discount userErrors for %s: %s", referrer_doc.get("email"), user_errors)
                shopify_ok = False
        except Exception:
            log.exception("Shopify discount creation failed for referrer %s", referrer_doc.get("email"))
            shopify_ok = False

    if shopify_is_configured() and not shopify_ok:
        # Don't mark the reward as granted — let the next webhook retry it.
        # Avoid spamming retries by writing a backoff timestamp.
        await db.waitlist.update_one(
            {"_id": referrer_doc["_id"]},
            {"$set": {"rewardGrantPendingSince": now}},
        )
        return

    await db.waitlist.update_one(
        {"_id": referrer_doc["_id"]},
        {"$set": {
            "rewardGranted": True,
            "rewardCode": code,
            "rewardGrantedAt": now,
            "rewardExpiresAt": ends_at,
            "rewardShopifyResult": shopify_result,
        }},
    )

    mailer.fire(mailer.free_month_earned(
        email=referrer_doc["email"],
        first_name=(referrer_doc.get("name", "").split(" ", 1)[0] or ""),
        referral_code=referrer_doc.get("referralCode", ""),
        discount_code=code,
        discount_amount_cents=REWARD_AMOUNT_CENTS,
        discount_expires_at=ends_at.isoformat(),
    ))
    log.info("Granted free-month reward to %s (code=%s)", referrer_doc["email"], code)


@router.post("/webhooks/shopify")
async def handle_shopify_webhook(request: Request):
    """Top-level handler: verify HMAC, dispatch by topic, dead-letter on failure.

    Always returns 200 unless HMAC fails — anything else after that point goes
    into `webhook_failures` for retry so Shopify doesn't poison-pill us.
    """
    try:
        body = await verify_shopify_webhook(request)
    except HTTPException:
        raise  # 401 propagates — Shopify retries with the right secret next time
    topic = get_webhook_topic(request)
    try:
        return await _dispatch_webhook(topic, body)
    except Exception as e:
        log.exception("Webhook dispatch failed: %s", topic)
        db = get_db()
        await db.webhook_failures.insert_one({
            "topic": topic,
            "body": body,
            "shop": get_webhook_shop_domain(request),
            "error": str(e)[:1000],
            "retry_count": 0,
            "created_at": datetime.now(timezone.utc),
        })
        # 200 acks Shopify; ops cron retries from the DLQ collection.
        return {"received": True, "topic": topic, "deferred": True}


async def _dispatch_webhook(topic: str, body: dict) -> dict:
    db = get_db()
    now = datetime.now(timezone.utc)

    if topic == "customers/create":
        customer_gid = body.get("admin_graphql_api_id") or f"gid://shopify/Customer/{body.get('id')}"
        await db.users.update_one(
            {"shopifyCustomerId": customer_gid},
            {"$setOnInsert": {
                "shopifyCustomerId": customer_gid,
                "email": body.get("email"),
                "subscriptionStatus": "inactive",
                "voteEligibleCycles": [],
                "createdAt": now,
            }, "$set": {"updatedAt": now}},
            upsert=True,
        )

    elif topic == "orders/paid":
        customer = body.get("customer") or {}
        customer_gid = customer.get("admin_graphql_api_id") or f"gid://shopify/Customer/{customer.get('id')}"
        order_id = str(body.get("id"))
        cycle_key = _cycle_key(now)

        # Detect gift purchase by line items / properties
        is_gift = False
        recipient_email = None
        duration_months = 1
        for li in body.get("line_items", []):
            props = {p.get("name"): p.get("value") for p in (li.get("properties") or [])}
            if "gift_recipient_email" in props:
                is_gift = True
                recipient_email = props.get("gift_recipient_email")
                try:
                    duration_months = int(props.get("gift_duration_months", "1"))
                except ValueError:
                    duration_months = 1
                break

        if is_gift and recipient_email:
            code = _gen_gift_code()
            buyer_email = customer.get("email")
            await db.gifts.insert_one({
                "code": code,
                "buyerShopifyOrderId": order_id,
                "buyerEmail": buyer_email,
                "recipientEmail": recipient_email,
                "durationMonths": duration_months,
                "status": "pending",
                "recipientShopifyCustomerId": None,
                "redeemedAt": None,
                "createdAt": now,
            })
            await db.events.insert_one({
                "type": "gift.created",
                "orderId": order_id,
                "code": code,
                "recipientEmail": recipient_email,
                "createdAt": now,
            })
            # Klaviyo: buyer gets a "thank you / receipt" event,
            # recipient gets the gift code with redeem URL.
            redeem_url_base = settings.APP_URL.rstrip("/") if settings.APP_URL else ""
            redeem_url = f"{redeem_url_base}/r/redeem?code={code}" if redeem_url_base else f"/r/redeem?code={code}"
            if buyer_email:
                first_name = (customer.get("first_name") or "").strip()
                mailer.fire(mailer.gift_purchased(
                    buyer_email=buyer_email,
                    buyer_first_name=first_name or None,
                    recipient_email=recipient_email,
                    duration_months=duration_months,
                    order_id=order_id,
                ))
            mailer.fire(mailer.gift_code_issued(
                recipient_email=recipient_email,
                code=code,
                duration_months=duration_months,
                redeem_url=redeem_url,
            ))
        else:
            # Standard subscription order — mark cycle eligible
            await db.orders.update_one(
                {"shopifyOrderId": order_id},
                {"$setOnInsert": {
                    "shopifyOrderId": order_id,
                    "shopifyCustomerId": customer_gid,
                    "totalPrice": body.get("total_price"),
                    "createdAt": now,
                }},
                upsert=True,
            )
            existing_user = await db.users.find_one({"shopifyCustomerId": customer_gid})
            await db.users.update_one(
                {"shopifyCustomerId": customer_gid},
                {
                    "$setOnInsert": {
                        "shopifyCustomerId": customer_gid,
                        "email": (customer.get("email") if customer else None),
                        "createdAt": now,
                    },
                    "$set": {"subscriptionStatus": "active", "updatedAt": now},
                    "$addToSet": {"voteEligibleCycles": cycle_key},
                },
                upsert=True,
            )

            # Klaviyo: subscription welcome — fire only on first activation
            buyer_email = (customer.get("email") if customer else None)
            was_active = existing_user and existing_user.get("subscriptionStatus") == "active"
            if buyer_email and not was_active:
                first_name = (customer.get("first_name") or "").strip()
                # Find the active project title (if any) for personalisation
                active_proj = await db.projects.find_one({"isActive": True})
                mailer.fire(mailer.subscription_welcome(
                    email=buyer_email,
                    first_name=first_name or buyer_email.split("@")[0],
                    order_id=order_id,
                    first_kit_title=(active_proj or {}).get("title"),
                ))

            # ---------- Referral credit (one-time per referee) ----------
            if buyer_email:
                wl = await db.waitlist.find_one({"email": buyer_email})
                if wl and wl.get("referredByCode") and not wl.get("paidCredited"):
                    referrer = await db.waitlist.find_one(
                        {"referralCode": wl["referredByCode"]}
                    )
                    if referrer:
                        await db.waitlist.update_one(
                            {"_id": referrer["_id"]},
                            {"$inc": {"paidReferralCount": 1}},
                        )
                        await db.waitlist.update_one(
                            {"_id": wl["_id"]},
                            {"$set": {"paidCredited": True, "paidAt": now}},
                        )
                        # Re-read referrer with incremented counter, then evaluate reward
                        referrer = await db.waitlist.find_one({"_id": referrer["_id"]})
                        await _grant_free_month_if_earned(db, referrer)

    elif topic == "orders/cancelled":
        await db.orders.update_one(
            {"shopifyOrderId": str(body.get("id"))},
            {"$set": {"status": "cancelled", "updatedAt": now}},
        )

    elif topic == "subscription_contracts/create":
        contract_id = body.get("admin_graphql_api_id") or body.get("id")
        customer = body.get("customer") or {}
        customer_gid = customer.get("admin_graphql_api_id") or f"gid://shopify/Customer/{customer.get('id')}"
        await db.users.update_one(
            {"shopifyCustomerId": customer_gid},
            {"$set": {
                "shopifySubscriptionContractId": str(contract_id),
                "subscriptionStatus": "active",
                "updatedAt": now,
            }},
            upsert=True,
        )

    elif topic == "subscription_contracts/update":
        contract_id = str(body.get("admin_graphql_api_id") or body.get("id"))
        status = (body.get("status") or "").lower()
        # ACTIVE/PAUSED/CANCELLED → active/paused/cancelled
        mapped = {"active": "active", "paused": "paused", "cancelled": "cancelled"}.get(status, status)
        await db.users.update_one(
            {"shopifySubscriptionContractId": contract_id},
            {"$set": {"subscriptionStatus": mapped, "updatedAt": now}},
        )

    elif topic == "subscription_billing_cycles/skip":
        contract_id = str(body.get("subscription_contract_id") or body.get("contract_id") or "")
        # Mark next cycle skipped — remove from voteEligibleCycles
        cycle_key = _cycle_key(now)
        await db.users.update_one(
            {"shopifySubscriptionContractId": contract_id},
            {"$pull": {"voteEligibleCycles": cycle_key}, "$set": {"updatedAt": now}},
        )
        await db.events.insert_one({
            "type": "cycle.skipped",
            "contractId": contract_id,
            "cycleKey": cycle_key,
            "createdAt": now,
        })

    # 200 OK signals Shopify the webhook was consumed; non-2xx triggers retry.
    return {"received": True, "topic": topic}
