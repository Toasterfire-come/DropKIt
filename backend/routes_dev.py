"""Dev-only routes — orders, shipping labels, gmail blast.

All require role=dev via get_current_dev dependency.
"""
import secrets
from datetime import datetime, timezone
from typing import Optional
import os # Import os module

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from auth import get_current_dev
from db import get_db
import shipping_service
import gmail_service
from models import serialize
import email_service as mailer

router = APIRouter(prefix="/dev")


# ============================================================
# Orders — list + detail (sourced from Shopify webhook ingest)
# ============================================================
@router.get("/orders")
async def list_orders(_: dict = Depends(get_current_dev), limit: int = 50):
    db = get_db()
    items = []
    async for doc in db.orders.find().sort("createdAt", -1).limit(limit):
        items.append(serialize(doc))
    return items


@router.get("/orders/{order_id}")
async def order_detail(order_id: str, _: dict = Depends(get_current_dev)):
    db = get_db()
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Hydrate user (for address) + current project (for item-in-box)
    user = None
    if order.get("shopifyCustomerId"):
        user = await db.users.find_one({"shopifyCustomerId": order["shopifyCustomerId"]})
    project = await db.projects.find_one({"isActive": True})

    # Existing shipment record (if a label was already generated)
    shipment = await db.shipments.find_one({"order_id": str(order["_id"])})

    return {
        "order": serialize(order),
        "user": serialize(user) if user else None,
        "current_project": serialize(project) if project else None,
        "shipment": serialize(shipment) if shipment else None,
    }


# ============================================================
# Shipping — quote + buy label per order
# ============================================================
class ShipQuoteRequest(BaseModel):
    order_id: str
    address: dict  # { name, street1, street2?, city, state, zip, country, phone? }


@router.post("/shipping/quote")
async def shipping_quote(payload: ShipQuoteRequest, _: dict = Depends(get_current_dev)):
    res = shipping_service.create_shipment_with_rates(to_address=payload.address)
    if not res.get("cheapest"):
        raise HTTPException(status_code=400, detail="No rates returned")
    return res


class BuyLabelRequest(BaseModel):
    order_id: str
    shipment_id: str
    rate_id: str


@router.post("/shipping/labels")
async def buy_label(payload: BuyLabelRequest, _: dict = Depends(get_current_dev)):
    db = get_db()
    if not ObjectId.is_valid(payload.order_id):
        raise HTTPException(status_code=400, detail="Invalid order id")

    result = shipping_service.buy_label(payload.shipment_id, payload.rate_id)
    doc = {
        "order_id": payload.order_id,
        "shipment_id": payload.shipment_id,
        "rate_id": payload.rate_id,
        **result,
        "created_at": datetime.now(timezone.utc),
    }
    res = await db.shipments.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    return doc


# ============================================================
# Gmail OAuth — connect, status, disconnect
# ============================================================
@router.post("/gmail/connect")
async def gmail_connect(user: dict = Depends(get_current_dev)):
    state = secrets.token_urlsafe(24)
    db = get_db()
    await db.oauth_states.insert_one({
        "state": state, "user_id": user["id"], "created_at": datetime.now(timezone.utc),
    })
    # Use GMAIL_REDIRECT_URI from settings for the callback URL
    return {"auth_url": gmail_service.build_auth_url(state, settings.GMAIL_REDIRECT_URI)}


@router.get("/gmail/callback")
async def gmail_callback(request: Request):
    """Public callback — verifies state against pending oauth_states."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    db = get_db()
    entry = await db.oauth_states.find_one({"state": state})
    if not entry:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    try:
        # Pass GMAIL_REDIRECT_URI from settings to the exchange function
        result = await gmail_service.exchange_code(code, entry["user_id"], settings.GMAIL_REDIRECT_URI)
    finally:
        await db.oauth_states.delete_one({"_id": entry["_id"]})

    # Redirect the founder back to /dev with a success indicator
    from fastapi.responses import RedirectResponse
    from config import settings as S
    return RedirectResponse(
        url=f"{S.APP_URL or ''}/dev?gmail=connected&email={result.get('connected_email','')}",
        status_code=302,
    )


@router.get("/gmail/status")
async def gmail_status(user: dict = Depends(get_current_dev)):
    doc = await gmail_service.get_connected(user["id"])
    if not doc or not doc.get("connected"):
        return {"connected": False, "email": doc.get("email", "")}
    return {
        "connected": True,
        "email": doc.get("email"),
        "expires_at": doc.get("expires_at"),
    }


@router.post("/gmail/disconnect")
async def gmail_disconnect(user: dict = Depends(get_current_dev)):
    ok = await gmail_service.disconnect(user["id"])
    return {"disconnected": ok}


# ============================================================
# Email blast — to waitlist
# ============================================================
class BlastRequest(BaseModel):
    subject: str
    html: str
    audience: str = "waitlist"  # waitlist | users
    test_to: Optional[EmailStr] = None  # if set, send only to this address as a test


@router.post("/email/blast")
async def email_blast(payload: BlastRequest, user: dict = Depends(get_current_dev)):
    db = get_db()
    if payload.test_to:
        recipients = [str(payload.test_to)]
    elif payload.audience == "waitlist":
        recipients = [d["email"] async for d in db.waitlist.find({}, {"email": 1})]
    else: # audience == "users"
        recipients = [d["email"] async for d in db.users.find({"email": {"$exists": True}}, {"email": 1})]

    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients to send to")

    # Use GMAIL_USER from settings as the sender
    sender = settings.GMAIL_USER
    if not sender:
        raise HTTPException(status_code=400, detail="GMAIL_USER not configured")

    try:
        result = await gmail_service.send_blast(
            user_id=user["id"], sender=sender,
            subject=payload.subject, html=payload.html, recipients=recipients,
        )
    except (RuntimeError, ValueError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.email_blasts.insert_one({
        "user_id": user["id"], "audience": payload.audience,
        "subject": payload.subject, "html": payload.html,
        "total": result.get("sent", 0),
        "skipped": result.get("skipped", 0),
        "placeholder": result.get("placeholder", False),
        "created_at": datetime.now(timezone.utc),
    })
    return result


@router.get("/email/blasts")
async def list_blasts(_: dict = Depends(get_current_dev)):
    db = get_db()
    items = []
    async for doc in db.email_blasts.find().sort("created_at", -1).limit(25):
        items.append(serialize(doc))
    return items


# ============================================================
# Fulfill — one-click: mark fulfilled + push Shopify fulfillment + email buyer
# ============================================================
class FulfillRequest(BaseModel):
    order_id: str
    buyer_email: EmailStr
    buyer_name: Optional[str] = None


@router.post("/orders/{order_id}/fulfill")
async def fulfill_order(order_id: str, payload: FulfillRequest, user: dict = Depends(get_current_dev)):
    """One-click fulfillment: requires that a label has already been purchased
    for the order. Sends a tracking email via the connected Gmail account and
    pushes the fulfillment to Shopify (gracefully no-ops on placeholder creds).
    """
    from config import settings as S
    from shopify_client import shopify

    db = get_db()
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid order id")
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    shipment = await db.shipments.find_one({"order_id": order_id})
    if not shipment:
        raise HTTPException(status_code=400, detail="No shipping label yet — buy one first")

    tracking_code = shipment.get("tracking_code") or "—"
    carrier = shipment.get("carrier") or "USPS"
    service = shipment.get("service") or ""
    tracking_url = f"https://t.17track.net/en#nums={tracking_code}"

    # 1) Push fulfillment to Shopify (skips on placeholder creds)
    shopify_result = None
    shopify_skipped_reason = None
    if order.get("shopifyOrderId") and not S.SHOPIFY_ADMIN_ACCESS_TOKEN.startswith("PLACEHOLDER"):
        try:
            shopify_result = await shopify.create_fulfillment(
                order_id=order["shopifyOrderId"],
                tracking_company=carrier,
                tracking_number=tracking_code,
                tracking_url=tracking_url,
            )
            ue = ((shopify_result or {}).get("fulfillmentCreate") or {}).get("userErrors") or []
            if ue:
                shopify_skipped_reason = "; ".join(f"{e.get('message')}" for e in ue)
        except Exception as e:
            shopify_result = {"error": str(e)}
            shopify_skipped_reason = str(e)
    else:
        shopify_skipped_reason = "placeholder_or_no_shopify_order_id"

    # 2) Send tracking email via connected Gmail
    name = payload.buyer_name or payload.buyer_email.split("@")[0]
    html = f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;margin:0 auto;padding:24px;color:#1a1a1a;">
      <h1 style="font-size:28px;margin:0 0 16px;letter-spacing:-0.5px;">Your DropKit is on the way 📦</h1>
      <p>Hey {name},</p>
      <p>Your kit is heading out. Tracking details below — most parcels arrive in 3–5 business days.</p>
      <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;padding:16px;margin:20px 0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:14px;">
        <div><strong>Carrier:</strong> {carrier} {service}</div>
        <div><strong>Tracking #:</strong> {tracking_code}</div>
        <div style="margin-top:8px;"><a href="{tracking_url}" style="color:#E8510A;">Track this shipment →</a></div>
      </div>
      <p>Build something great with it. As always, all source code &amp; schematics live on <a href="https://github.com/Toasterfire-come/DropKit-Projects" style="color:#E8510A;">GitHub</a>.</p>
      <p style="margin-top:32px;color:#57606a;font-size:13px;">— The DropKit team</p>
    </div>
    """
    email_result = {"skipped": True, "reason": "not_attempted"}
    try:
        # Use GMAIL_USER from settings as the sender
        sender = settings.GMAIL_USER
        if not sender:
            raise ValueError("GMAIL_USER not configured")
        email_result = await gmail_service.send_blast(
            user_id=user["id"], sender=sender,
            subject="Your DropKit is on the way",
            html=html, recipients=[str(payload.buyer_email)],
        )
    except (RuntimeError, ValueError, Exception) as e:
        email_result = {"error": str(e)}

    # 3) Mark order fulfilled in MongoDB
    now = datetime.now(timezone.utc)
    await db.orders.update_one(
        {"_id": order["_id"]},
        {"$set": {
            "status": "fulfilled",
            "fulfilledAt": now,
            "fulfilledBy": user["id"],
            "tracking_code": tracking_code,
            "tracking_url": tracking_url,
            "shopify_fulfillment": shopify_result,
            "updatedAt": now,
        }},
    )

    return {
        "ok": True,
        "order_id": order_id,
        "tracking_code": tracking_code,
        "tracking_url": tracking_url,
        "email": email_result,
        "shopify": shopify_result,
        "shopify_skipped": shopify_result is None,
        "shopify_skipped_reason": shopify_skipped_reason,
    }
