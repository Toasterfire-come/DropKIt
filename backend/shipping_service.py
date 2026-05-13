"""EasyPost shipping client.

Production-grade rate shopping + label generation with placeholder-aware fallback.
When EASYPOST_API_KEY starts with PLACEHOLDER, all methods return synthesized
mock data so the UI can be exercised end-to-end without real credentials.
"""
from typing import List, Dict, Optional
import easypost

from config import settings


def _is_placeholder() -> bool:
    # Check if EasyPost API key is missing or a placeholder
    return not settings.EASYPOST_API_KEY or settings.EASYPOST_API_KEY.startswith("PLACEHOLDER")


def _client() -> Optional[easypost.EasyPostClient]:
    """Returns an EasyPost client if configured, otherwise None."""
    if _is_placeholder():
        return None
    return easypost.EasyPostClient(settings.EASYPOST_API_KEY)


def _from_address() -> dict:
    return {
        "name": settings.SHIPPING_FROM_NAME,
        "company": settings.SHIPPING_FROM_COMPANY,
        "street1": settings.SHIPPING_FROM_STREET1,
        "city": settings.SHIPPING_FROM_CITY,
        "state": settings.SHIPPING_FROM_STATE,
        "zip": settings.SHIPPING_FROM_ZIP,
        "country": "US",
        "phone": settings.SHIPPING_FROM_PHONE,
        "email": settings.SHIPPING_FROM_EMAIL,
    }


def _default_parcel() -> dict:
    return {
        "length": settings.DEFAULT_PARCEL_LENGTH,
        "width": settings.DEFAULT_PARCEL_WIDTH,
        "height": settings.DEFAULT_PARCEL_HEIGHT,
        "weight": settings.DEFAULT_PARCEL_WEIGHT,
    }


def create_shipment_with_rates(to_address: dict, parcel: Optional[dict] = None) -> Dict:
    """Create a shipment and return cheapest + priority rates from the same carrier."""
    if _is_placeholder():
        # Synthesized rates so UI can be exercised in dev
        return {
            "shipment_id": "shp_placeholder_dev",
            "rates": [
                {"id": "rate_usps_first", "carrier": "USPS", "service": "First", "rate": 5.20, "currency": "USD", "delivery_days": 4},
                {"id": "rate_usps_priority", "carrier": "USPS", "service": "Priority", "rate": 9.45, "currency": "USD", "delivery_days": 2},
                {"id": "rate_usps_express", "carrier": "USPS", "service": "Express", "rate": 28.10, "currency": "USD", "delivery_days": 1},
            ],
            "cheapest": {"id": "rate_usps_first", "carrier": "USPS", "service": "First", "rate": 5.20, "currency": "USD", "delivery_days": 4},
            "priority": {"id": "rate_usps_priority", "carrier": "USPS", "service": "Priority", "rate": 9.45, "currency": "USD", "delivery_days": 2},
            "placeholder": True,
        }

    cli = _client()
    if not cli: # Should not happen if _is_placeholder is False, but good for safety
        return {"shipment_id": None, "rates": [], "cheapest": None, "priority": None, "placeholder": True, "error": "EasyPost client not initialized"}

    try:
        shipment = cli.shipment.create(
            from_address=_from_address(),
            to_address=to_address,
            parcel=parcel or _default_parcel(),
        )
        rates = [
            {
                "id": r.id, "carrier": r.carrier, "service": r.service,
                "rate": float(r.rate), "currency": r.currency,
                "delivery_days": getattr(r, "est_delivery_days", None) or getattr(r, "delivery_days", None),
            }
            for r in shipment.rates
        ]
        if not rates:
            return {"shipment_id": shipment.id, "rates": [], "cheapest": None, "priority": None, "placeholder": False}

        # Cheapest overall
        cheapest = min(rates, key=lambda r: r["rate"])
        same_carrier = [r for r in rates if r["carrier"] == cheapest["carrier"]]
        faster_same_carrier = [r for r in same_carrier if r["rate"] > cheapest["rate"]]
        priority = min(faster_same_carrier, key=lambda r: r["rate"]) if faster_same_carrier else cheapest

        return {
            "shipment_id": shipment.id,
            "rates": rates,
            "cheapest": cheapest,
            "priority": priority,
            "placeholder": False,
        }
    except Exception as e:
        # Log the error for debugging
        print(f"Error creating EasyPost shipment: {e}")
        return {"shipment_id": None, "rates": [], "cheapest": None, "priority": None, "placeholder": False, "error": str(e)}


def buy_label(shipment_id: str, rate_id: str) -> Dict:
    """Purchase a label and return URLs for PDF / ZPL / QR."""
    if _is_placeholder():
        return {
            "shipment_id": shipment_id,
            "rate_id": rate_id,
            "tracking_code": "PLACEHOLDER1Z00000000000000",
            "label_pdf_url": "https://example.com/labels/placeholder.pdf",
            "label_zpl_url": "https://example.com/labels/placeholder.zpl",
            "label_qr_url": "https://example.com/labels/placeholder.qr.png",
            "carrier": "USPS",
            "service": "Priority",
            "placeholder": True,
        }

    cli = _client()
    if not cli:
        return {"shipment_id": shipment_id, "rate_id": rate_id, "placeholder": True, "error": "EasyPost client not initialized"}

    try:
        shipment = cli.shipment.buy(id=shipment_id, rate={"id": rate_id})
        label = shipment.postage_label
        base = label.label_url if label else None
        # Format conversions (EasyPost supports `convert` for ZPL/PNG; QR via generate_form)
        return {
            "shipment_id": shipment.id,
            "rate_id": rate_id,
            "tracking_code": shipment.tracking_code,
            "label_pdf_url": base,
            "label_zpl_url": (base + "?file_format=zpl") if base else None,
            "label_qr_url": (base + "?file_format=png") if base else None,
            "carrier": shipment.selected_rate.carrier if shipment.selected_rate else None,
            "service": shipment.selected_rate.service if shipment.selected_rate else None,
            "placeholder": False,
        }
    except Exception as e:
        print(f"Error buying EasyPost label: {e}")
        return {"shipment_id": shipment_id, "rate_id": rate_id, "placeholder": False, "error": str(e)}


def get_tracking(tracking_code: str, carrier: Optional[str] = None) -> Dict:
    if _is_placeholder():
        return {
            "tracking_code": tracking_code,
            "carrier": carrier or "USPS",
            "status": "pre_transit",
            "tracking_details": [],
            "placeholder": True,
        }
    cli = _client()
    if not cli:
        return {"tracking_code": tracking_code, "carrier": carrier or "USPS", "status": "error", "tracking_details": [], "placeholder": True, "error": "EasyPost client not initialized"}

    try:
        t = cli.tracker.create(tracking_code=tracking_code, carrier=carrier) if carrier else cli.tracker.create(tracking_code=tracking_code)
        return {
            "tracking_code": t.tracking_code,
            "carrier": t.carrier,
            "status": t.status,
            "tracking_details": [
                {"status": e.status, "message": e.message, "timestamp": str(e.datetime), "location": getattr(e, "location", None)}
                for e in (t.tracking_details or [])
            ],
            "placeholder": False,
        }
    except Exception as e:
        print(f"Error getting EasyPost tracking: {e}")
        return {"tracking_code": tracking_code, "carrier": carrier or "USPS", "status": "error", "tracking_details": [], "placeholder": False, "error": str(e)}


def verify_address(address: dict) -> Dict:
    """Run EasyPost address verification. Returns the canonical form + delta + issues.

    In placeholder mode, treats anything with a 5-digit zip as valid. In real mode,
    uses `verify_strict` so deliverability is enforced before label purchase.
    """
    if _is_placeholder():
        zip_ok = isinstance(address.get("zip"), str) and len(address["zip"].split("-")[0]) == 5
        return {
            "valid": zip_ok,
            "canonical": address,
            "issues": [] if zip_ok else [{"code": "E.HOUSE.NUMBER", "message": "ZIP must be 5 digits"}],
            "placeholder": True,
        }
    cli = _client()
    if not cli:
        return {"valid": False, "canonical": address, "issues": [{"code": "CLIENT_ERROR", "message": "EasyPost client not initialized"}], "placeholder": True}

    try:
        addr = cli.address.create_and_verify(
            street1=address.get("street1", ""),
            street2=address.get("street2"),
            city=address.get("city", ""),
            state=address.get("state", ""),
            zip=address.get("zip", ""),
            country=address.get("country", "US"),
            name=address.get("name"),
            phone=address.get("phone"),
            email=address.get("email"),
            verify_strict=["delivery"],
        )
        canonical = {
            "name": getattr(addr, "name", address.get("name")),
            "street1": addr.street1,
            "street2": getattr(addr, "street2", None),
            "city": addr.city,
            "state": addr.state,
            "zip": addr.zip,
            "country": addr.country,
            "phone": getattr(addr, "phone", address.get("phone")),
        }
        vfn = (getattr(addr, "verifications", None) or {}).get("delivery") or {}
        issues = [{"code": e.get("code"), "message": e.get("message")} for e in (vfn.get("errors") or [])]
        return {
            "valid": bool(vfn.get("success")),
            "canonical": canonical,
            "issues": issues,
            "easypost_address_id": addr.id,
            "placeholder": False,
        }
    except Exception as e:
        print(f"Error verifying EasyPost address: {e}")
        return {"valid": False, "canonical": address, "issues": [{"code": "VERIFICATION_ERROR", "message": str(e)}], "placeholder": False}


def create_scan_form(shipment_ids: List[str]) -> Dict:
    """USPS SCAN form / manifest — single barcode acknowledging all packages.

    Saves ~1 minute per package at carrier pickup. Returns a downloadable PDF URL.
    """
    if _is_placeholder():
        return {
            "id": "sf_placeholder",
            "form_url": "https://example.com/scanforms/placeholder.pdf",
            "tracking_codes": [f"PLACEHOLDER_TRACK_{i+1}" for i, _ in enumerate(shipment_ids)],
            "placeholder": True,
        }
    cli = _client()
    if not cli:
        return {"id": None, "form_url": None, "tracking_codes": [], "placeholder": True, "error": "EasyPost client not initialized"}

    try:
        sf = cli.scan_form.create(shipments=[{"id": sid} for sid in shipment_ids])
        return {
            "id": sf.id,
            "form_url": getattr(sf, "form_url", None) or getattr(sf, "form_file_type", None),
            "tracking_codes": list(getattr(sf, "tracking_codes", []) or []),
            "placeholder": False,
        }
    except Exception as e:
        print(f"Error creating EasyPost scan form: {e}")
        return {"id": None, "form_url": None, "tracking_codes": [], "placeholder": False, "error": str(e)}


def download_label_pdf(label_pdf_url: str) -> Optional[bytes]:
    """Fetch an EasyPost label PDF into memory (for merging into batch PDFs)."""
    if not label_pdf_url:
        return None
    # If it's a placeholder URL, we can't actually download it.
    if label_pdf_url.startswith("https://example.com/"):
        return None
    try:
        import httpx
        r = httpx.get(label_pdf_url, timeout=20.0, follow_redirects=True)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"Error downloading EasyPost label PDF: {e}")
        return None
