"""Stripe Tax calculation.

Real Stripe Tax API call when STRIPE_SECRET_KEY is non-placeholder and
STRIPE_TAX_ENABLED=true; otherwise returns 0 tax so flow is preserved.
"""
from typing import Dict
import stripe
import httpx # Import httpx for potential network errors

from config import settings


def _is_placeholder() -> bool:
    # Check if Stripe secret key is missing or a placeholder, or if Stripe Tax is explicitly disabled.
    return (
        not settings.STRIPE_SECRET_KEY
        or settings.STRIPE_SECRET_KEY.startswith("PLACEHOLDER")
        or not settings.STRIPE_TAX_ENABLED
    )


def calculate_tax(line_amount_cents: int, shipping_cents: int, address: dict) -> Dict:
    """Return {tax_cents, total_cents, calculation_id?}."""
    if _is_placeholder():
        # Return placeholder data if Stripe Tax is not enabled or configured.
        return {
            "tax_cents": 0,
            "subtotal_cents": line_amount_cents,
            "shipping_cents": shipping_cents,
            "total_cents": line_amount_cents + shipping_cents,
            "calculation_id": None,
            "placeholder": True,
        }

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
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
    except stripe.error.StripeError as e:
        # Handle Stripe-specific errors gracefully
        print(f"Stripe Tax calculation error: {e}")
        # Return placeholder data in case of Stripe API errors
        return {
            "tax_cents": 0,
            "subtotal_cents": line_amount_cents,
            "shipping_cents": shipping_cents,
            "total_cents": line_amount_cents + shipping_cents,
            "calculation_id": None,
            "placeholder": True,
            "error": f"Stripe Tax API error: {e}",
        }
    except httpx.RequestError as e:
        # Handle network-related errors
        print(f"Network error during Stripe Tax calculation: {e}")
        return {
            "tax_cents": 0,
            "subtotal_cents": line_amount_cents,
            "shipping_cents": shipping_cents,
            "total_cents": line_amount_cents + shipping_cents,
            "calculation_id": None,
            "placeholder": True,
            "error": f"Network error: {e}",
        }
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred during Stripe Tax calculation: {e}")
        return {
            "tax_cents": 0,
            "subtotal_cents": line_amount_cents,
            "shipping_cents": shipping_cents,
            "total_cents": line_amount_cents + shipping_cents,
            "calculation_id": None,
            "placeholder": True,
            "error": f"An unexpected error occurred: {e}",
        }
