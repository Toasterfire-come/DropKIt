"""Stripe Tax calculation.

Real Stripe Tax API call when STRIPE_SECRET_KEY is non-placeholder and
STRIPE_TAX_ENABLED=true; otherwise returns 0 tax so flow is preserved.
"""
from typing import Dict
import stripe

from config import settings


def _is_placeholder() -> bool:
    return (
        not settings.STRIPE_SECRET_KEY
        or settings.STRIPE_SECRET_KEY.startswith("PLACEHOLDER")
        or not settings.STRIPE_TAX_ENABLED
    )


def calculate_tax(line_amount_cents: int, shipping_cents: int, address: dict) -> Dict:
    """Return {tax_cents, total_cents, calculation_id?}."""
    if _is_placeholder():
        return {
            "tax_cents": 0,
            "subtotal_cents": line_amount_cents,
            "shipping_cents": shipping_cents,
            "total_cents": line_amount_cents + shipping_cents,
            "calculation_id": None,
            "placeholder": True,
        }

    stripe.api_key = settings.STRIPE_SECRET_KEY
    calc = stripe.tax.Calculation.create(
        currency="usd",
        line_items=[{"amount": line_amount_cents, "reference": "DropKit Monthly Subscription"}],
        shipping_cost={"amount": shipping_cents} if shipping_cents > 0 else None,
        customer_details={
            "address": {
                "line1": address.get("street1", ""),
                "line2": address.get("street2", ""),
                "city": address.get("city", ""),
                "state": address.get("state", ""),
                "postal_code": address.get("zip", ""),
                "country": address.get("country", "US"),
            },
            "address_source": "shipping",
        },
    )
    tax_cents = getattr(calc, "tax_amount_exclusive", 0) or 0
    return {
        "tax_cents": tax_cents,
        "subtotal_cents": line_amount_cents,
        "shipping_cents": shipping_cents,
        "total_cents": line_amount_cents + shipping_cents + tax_cents,
        "calculation_id": calc.id,
        "placeholder": False,
    }
