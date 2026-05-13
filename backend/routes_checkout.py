"""Checkout / quote — compute shipping rates + tax for the subscribe flow."""
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from config import settings
from db import get_db
from shipping_service import create_shipment_with_rates
import shipping_service
from tax_service import calculate_tax

router = APIRouter(prefix="/checkout")


class ShippingAddress(BaseModel):
    name: Optional[str] = None
    street1: str
    street2: Optional[str] = None
    city: str
    state: str
    zip: str
    country: str = "US"
    phone: Optional[str] = None


class QuoteRequest(BaseModel):
    email: EmailStr
    address: ShippingAddress


SUBSCRIPTION_PRICE_CENTS = 4000  # $40


@router.post("/quote")
async def quote(payload: QuoteRequest):
    addr_dict = payload.address.model_dump()
    addr_dict["name"] = payload.address.name or payload.email.split("@")[0]
    addr_dict["phone"] = payload.address.phone or settings.SHIPPING_FROM_PHONE

    # Item 8 — verify address before pulling rates (catches typos that cause $13 reships)
    verified = shipping_service.verify_address(addr_dict)
    if not verified.get("valid"):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "address_undeliverable",
                "issues": verified.get("issues", []),
                "canonical": verified.get("canonical"),
            },
        )
    # Use the canonical (corrected) address for rating + persistence
    addr_dict = verified.get("canonical") or addr_dict

    rates = create_shipment_with_rates(to_address=addr_dict)
    if not rates.get("cheapest"):
        raise HTTPException(status_code=400, detail="No shipping rates available for that address")

    cheapest_cents = int(round(rates["cheapest"]["rate"] * 100))
    priority_cents = int(round(rates["priority"]["rate"] * 100))

    tax_cheapest = calculate_tax(SUBSCRIPTION_PRICE_CENTS, cheapest_cents, addr_dict)
    tax_priority = calculate_tax(SUBSCRIPTION_PRICE_CENTS, priority_cents, addr_dict)

    # Persist the quote for analytics + later checkout linking
    db = get_db()
    quote_doc = {
        "email": payload.email,
        "address": addr_dict,
        "shipment_id": rates["shipment_id"],
        "cheapest": rates["cheapest"],
        "priority": rates["priority"],
        "subscription_cents": SUBSCRIPTION_PRICE_CENTS,
        "tax_cheapest_cents": tax_cheapest["tax_cents"],
        "tax_priority_cents": tax_priority["tax_cents"],
        "placeholder_shipping": rates.get("placeholder", False),
        "placeholder_tax": tax_cheapest.get("placeholder", False),
        "created_at": datetime.now(timezone.utc),
    }
    res = await db.checkout_quotes.insert_one(quote_doc)

    return {
        "quote_id": str(res.inserted_id),
        "email": payload.email,
        "subscription_cents": SUBSCRIPTION_PRICE_CENTS,
        "options": {
            "cheapest": {
                "rate": rates["cheapest"],
                "shipping_cents": cheapest_cents,
                "tax_cents": tax_cheapest["tax_cents"],
                "total_cents": SUBSCRIPTION_PRICE_CENTS + cheapest_cents + tax_cheapest["tax_cents"],
            },
            "priority": {
                "rate": rates["priority"],
                "shipping_cents": priority_cents,
                "tax_cents": tax_priority["tax_cents"],
                "total_cents": SUBSCRIPTION_PRICE_CENTS + priority_cents + tax_priority["tax_cents"],
            },
        },
        "placeholder_shipping": rates.get("placeholder", False),
        "placeholder_tax": tax_cheapest.get("placeholder", False),
    }


class CheckoutStartRequest(BaseModel):
    quote_id: str
    rate_choice: str  # "cheapest" | "priority"


@router.post("/start")
async def start_checkout(payload: CheckoutStartRequest):
    """Hand off to Shopify Checkout with the subscription line item pre-loaded.

    When Shopify is properly configured (via env), this returns a cart-permalink
    that loads the subscription product with the right selling plan, customer
    email, and any active referral discount code, then redirects to Shopify
    Checkout. With placeholder creds, it falls back to the product page URL.
    """
    from bson import ObjectId
    from shopify_client import build_subscription_cart_url, shopify_is_configured

    db = get_db()
    if not ObjectId.is_valid(payload.quote_id):
        raise HTTPException(status_code=400, detail="Invalid quote id")
    quote_doc = await db.checkout_quotes.find_one({"_id": ObjectId(payload.quote_id)})
    if not quote_doc:
        raise HTTPException(status_code=404, detail="Quote not found")

    rate = quote_doc.get(payload.rate_choice)
    if not rate:
        raise HTTPException(status_code=400, detail="Invalid rate choice")

    email = quote_doc["email"]
    discount_code = None

    # If buyer is on the waitlist and earned a free month, auto-apply
    wl = await db.waitlist.find_one({"email": email})
    if wl and wl.get("rewardGranted") and not wl.get("rewardApplied"):
        discount_code = wl.get("rewardCode")

    variant_id = getattr(settings, "SHOPIFY_SUBSCRIPTION_VARIANT_ID", "") or ""
    selling_plan_id = getattr(settings, "SHOPIFY_SUBSCRIPTION_SELLING_PLAN_ID", "") or ""

    if shopify_is_configured() and variant_id:
        redirect_url = build_subscription_cart_url(
            variant_id=variant_id,
            selling_plan_id=selling_plan_id or None,
            quantity=1,
            email=email,
            discount_code=discount_code,
        )
        placeholder = False
    else:
        # Dev fallback: same Shopify product page URL as before
        params = {
            "email": email,
            "properties[shipping_service]": rate["service"],
            "properties[shipping_carrier]": rate["carrier"],
            "properties[shipping_rate_cents]": str(int(round(rate["rate"] * 100))),
            "properties[quote_id]": payload.quote_id,
        }
        if discount_code:
            params["discount"] = discount_code
        redirect_url = (
            f"https://{settings.SHOPIFY_STORE_DOMAIN}"
            f"/products/monthly-maker-box?{urlencode(params)}"
        )
        placeholder = True

    await db.checkout_quotes.update_one(
        {"_id": quote_doc["_id"]},
        {"$set": {
            "checkout_started_at": datetime.now(timezone.utc),
            "rate_choice": payload.rate_choice,
            "discount_code_applied": discount_code,
        }},
    )

    return {
        "redirect_url": redirect_url,
        "placeholder_shopify": placeholder,
        "discount_code_applied": discount_code,
    }
