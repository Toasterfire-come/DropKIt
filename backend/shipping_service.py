"""EasyPost shipping client — flat-rate standard + rate-shopped express.

Standard shipping: $9.00 flat (set cost)
Express shipping:   EasyPost rate-shopped rate + $2 additional packaging fee

When EASYPOST_API_KEY starts with PLACEHOLDER, all methods return synthesized
mock data so the UI can be exercised end-to-end without real credentials.
"""
from typing import List, Dict, Optional
import easypost

from config import settings

# ── Constants ──
FLAT_RATE_STANDARD_CENTS = 900   # $9.00 set cost
EXPRESS_PACKAGING_FEE_CENTS = 200  # $2.00 additional packaging


def _is_placeholder() -> bool:
    return not settings.EASYPOST_API_KEY or settings.EASYPOST_API_KEY.startswith("PLACEHOLDER")


def _client() -> Optional[easypost.EasyPostClient]:
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
    """Return standard flat rate + express (EasyPost cheapest + $2 packaging)."""
    standard_rate = {
        "id": "flat_standard", "carrier": "DropKit", "service": "Standard",
        "rate": 9.00, "currency": "USD", "delivery_days": 5,
    }

    # Try to get a real express rate from EasyPost
    express_rate = None
    placeholder = _is_placeholder()

    if not placeholder:
        cli = _client()
        if cli:
            try:
                shipment = cli.shipment.create(
                    from_address=_from_address(),
                    to_address=to_address,
                    parcel=parcel or _default_parcel(),
                )
                ep_rates = [
                    {"id": r.id, "carrier": r.carrier, "service": r.service,
                     "rate": float(r.rate), "currency": r.currency,
                     "delivery_days": getattr(r, "est_delivery_days", None) or getattr(r, "delivery_days", None)}
                    for r in shipment.rates
                ]
                if ep_rates:
                    # Pick the fastest available (express/priority)
                    express_candidates = [r for r in ep_rates if any(kw in r["service"].lower() for kw in ["express", "priority", "next"])]
                    if express_candidates:
                        fastest = min(express_candidates, key=lambda r: r["rate"])
                    else:
                        fastest = min(ep_rates, key=lambda r: r["delivery_days"] or 99)
                    packaging_fee = EXPRESS_PACKAGING_FEE_CENTS / 100
                    express_rate = {
                        "id": fastest["id"],
                        "carrier": fastest["carrier"],
                        "service": f"Express ({fastest['service']})",
                        "rate": fastest["rate"] + packaging_fee,
                        "base_rate": fastest["rate"],
                        "packaging_fee": packaging_fee,
                        "currency": "USD",
                        "delivery_days": fastest["delivery_days"],
                    }
            except Exception as e:
                print(f"Error getting EasyPost rates for express: {e}")

    # Fallback if no real rate available
    if not express_rate:
        express_rate = {
            "id": "flat_express_fallback", "carrier": "DropKit", "service": "Express",
            "rate": 15.00, "currency": "USD", "delivery_days": 2,
            "base_rate": 13.00, "packaging_fee": 2.00,
        }

    return {
        "shipment_id": "flat_rate_standard",
        "rates": [standard_rate, express_rate],
        "standard": standard_rate,
        "express": express_rate,
        "placeholder": placeholder,
    }


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
            "carrier": "DropKit",
            "service": "Standard" if "standard" in rate_id else "Express",
            "placeholder": True,
        }

    cli = _client()
    if not cli:
        return {"shipment_id": shipment_id, "rate_id": rate_id, "placeholder": True, "error": "EasyPost client not initialized"}

    try:
        shipment = cli.shipment.buy(id=shipment_id, rate={"id": rate_id})
        label = shipment.postage_label
        base = label.label_url if label else None
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
            "carrier": carrier or "DropKit",
            "status": "pre_transit",
            "tracking_details": [],
            "placeholder": True,
        }
    cli = _client()
    if not cli:
        return {"tracking_code": tracking_code, "carrier": carrier or "DropKit", "status": "error", "tracking_details": [], "placeholder": True, "error": "EasyPost client not initialized"}

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
        return {"tracking_code": tracking_code, "carrier": carrier or "DropKit", "status": "error", "tracking_details": [], "placeholder": False, "error": str(e)}


def verify_address(address: dict) -> Dict:
    """Run EasyPost address verification. Returns the canonical form + delta + issues."""
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
    """USPS SCAN form / manifest — single barcode acknowledging all packages."""
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
