"""Checkout / quote — flat-rate standard + rate-shopped express.

Standard: $9 flat (set cost)
Express:  Live EasyPost rate + $2 packaging fee
"""
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from config import settings
from db import get_db
from shipping_service import (
    create_shipment_with_rates,
    verify_address,
    FLAT_RATE_STANDARD_CENTS,
)
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

    # Verify address before proceeding
    verified = verify_address(addr_dict)
    if not verified.get("valid"):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "address_undeliverable",
                "issues": verified.get("issues", []),
                "canonical": verified.get("canonical"),
            },
        )
    addr_dict = verified.get("canonical") or addr_dict

    # ── Get rates: standard is flat $9, express is live rate + $2 ──
    rates = create_shipment_with_rates(to_address=addr_dict)
    standard = rates["standard"]
    express  = rates["express"]

    standard_shipping_cents = FLAT_RATE_STANDARD_CENTS
    express_shipping_cents  = int(round(express["rate"] * 100))

    tax_standard = calculate_tax(SUBSCRIPTION_PRICE_CENTS, standard_shipping_cents, addr_dict)
    tax_express  = calculate_tax(SUBSCRIPTION_PRICE_CENTS, express_shipping_cents, addr_dict)

    # Persist the quote
    db = get_db()
    quote_doc = {
        "email": payload.email,
        "address": addr_dict,
        "shipment_id": rates["shipment_id"],
        "standard": standard,
        "express": express,
        "subscription_cents": SUBSCRIPTION_PRICE_CENTS,
        "standard_shipping_cents": standard_shipping_cents,
        "express_shipping_cents": express_shipping_cents,
        "tax_standard_cents": tax_standard["tax_cents"],
        "tax_express_cents": tax_express["tax_cents"],
        "placeholder_shipping": rates.get("placeholder", False),
        "placeholder_tax": tax_standard.get("placeholder", False),
        "created_at": datetime.now(timezone.utc),
    }
    res = await db.checkout_quotes.insert_one(quote_doc)

    return {
        "quote_id": str(res.inserted_id),
        "email": payload.email,
        "subscription_cents": SUBSCRIPTION_PRICE_CENTS,
        "shipping": {
            "standard": {"rate": standard, "shipping_cents": standard_shipping_cents, "tax_cents": tax_standard["tax_cents"], "total_cents": SUBSCRIPTION_PRICE_CENTS + standard_shipping_cents + tax_standard["tax_cents"]},
            "express":  {"rate": express,  "shipping_cents": express_shipping_cents,  "tax_cents": tax_express["tax_cents"],  "total_cents": SUBSCRIPTION_PRICE_CENTS + express_shipping_cents + tax_express["tax_cents"]},
        },
        "placeholder_shipping": rates.get("placeholder", False),
        "placeholder_tax": tax_standard.get("placeholder", False),
    }


class CheckoutStartRequest(BaseModel):
    quote_id: str
    shipping_choice: str  # "standard" | "express"


@router.post("/start")
async def start_checkout(payload: CheckoutStartRequest):
    """Hand off to Shopify Checkout with the subscription + shipping info.

    Shows the shipping option the user selected so it's transparent before
    they hit Shopify.
    """
    from bson import ObjectId
    from shopify_client import build_subscription_cart_url, shopify_is_configured

    db = get_db()
    if not ObjectId.is_valid(payload.quote_id):
        raise HTTPException(status_code=400, detail="Invalid quote id")
    quote_doc = await db.checkout_quotes.find_one({"_id": ObjectId(payload.quote_id)})
    if not quote_doc:
        raise HTTPException(status_code=404, detail="Quote not found")

    if payload.shipping_choice not in ("standard", "express"):
        raise HTTPException(status_code=400, detail="shipping_choice must be 'standard' or 'express'")

    rate = quote_doc.get(payload.shipping_choice)
    if not rate:
        raise HTTPException(status_code=400, detail="Shipping option not found in quote")
    shipping_cents = quote_doc.get(f"{payload.shipping_choice}_shipping_cents", FLAT_RATE_STANDARD_CENTS)

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
        # Dev fallback
        params = {
            "email": email,
            "properties[shipping_service]": rate["service"],
            "properties[shipping_carrier]": rate["carrier"],
            "properties[shipping_rate_cents]": str(shipping_cents),
            "properties[shipping_choice]": payload.shipping_choice,
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
            "shipping_choice": payload.shipping_choice,
            "discount_code_applied": discount_code,
        }},
    )

    return {
        "redirect_url": redirect_url,
        "placeholder_shopify": placeholder,
        "discount_code_applied": discount_code,
        "shipping_choice": payload.shipping_choice,
        "shipping_label": f"{rate['carrier']} {rate['service']} — ${shipping_cents / 100:.2f}",
    }
