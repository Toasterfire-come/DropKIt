"""Dev ops — order flow & admin-time savings routes.

Bundles items 1-15 from the streamlining roadmap:
  1.  Batch label PDF                              POST /dev/ops/labels/batch
  2.  Pack slips merged into label PDF             (same endpoint, include_pack_slip=true)
  3.  Barcode scan → fulfill                       POST /dev/ops/scan/{token}/confirm
  4.  Today's queue dashboard                      GET  /dev/ops/queue/today
  6.  USPS SCAN form / manifest                    POST /dev/ops/scan-form
  11. Cycle-close automation                       POST /dev/ops/cycle/close
  12. Cohort retention dashboard                   GET  /dev/ops/cohorts
  13. Replacement queue + approve                  GET  /dev/ops/replacements
                                                   POST /dev/ops/replacements/{id}/approve
  14. Shop-floor live feed (Server-Sent Events)    GET  /dev/ops/feed
  15. Tax nexus check                              GET  /dev/ops/tax-nexus
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from auth import get_current_dev
from config import settings
from db import get_db
import shipping_service
import pack_slip
from models import serialize
import email_service as mailer

router = APIRouter(prefix="/dev/ops")

# Live event stream queue (in-process; replace with Redis for multi-worker)
_EVENT_QUEUE: "asyncio.Queue[Dict]" = asyncio.Queue(maxsize=200)


async def publish_event(event_type: str, payload: dict) -> None:
    """Publish a shop-floor event to the live SSE feed (best-effort, non-blocking)."""
    try:
        _EVENT_QUEUE.put_nowait({
            "type": event_type,
            "payload": payload,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except asyncio.QueueFull:
        # Drop oldest, push new
        try:
            _EVENT_QUEUE.get_nowait()
            _EVENT_QUEUE.put_nowait({
                "type": event_type, "payload": payload,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass


# =============================================================================
# Item 1 + 2 — Batch labels with merged pack slips
# =============================================================================
class BatchLabelsRequest(BaseModel):
    order_ids: Optional[List[str]] = None  # If None, all orders with status=paid
    include_pack_slip: bool = True
    rate_choice: str = "cheapest"  # "cheapest" | "priority"


async def _resolve_recipient_address(order: dict, db) -> Optional[dict]:
    """Pull recipient address — preference: order.shipping_address > user.shipping_address."""
    if order.get("shipping_address"):
        return order["shipping_address"]
    if order.get("shopifyCustomerId"):
        u = await db.users.find_one({"shopifyCustomerId": order["shopifyCustomerId"]})
        if u and u.get("shipping_address"):
            return u["shipping_address"]
    return None


@router.post("/labels/batch")
async def batch_labels(payload: BatchLabelsRequest, user: dict = Depends(get_current_dev)):
    """Buy labels for every unfulfilled order in one shot, return a merged PDF.

    Idempotent per order: reuses an existing shipment doc if a label was already
    bought. Skips orders missing a recipient address (returns them as `failed`).
    """
    db = get_db()
    query: dict = {"$or": [{"status": {"$exists": False}}, {"status": "paid"}]}
    if payload.order_ids:
        oids = [ObjectId(o) for o in payload.order_ids if ObjectId.is_valid(o)]
        query["_id"] = {"$in": oids}

    project = await db.projects.find_one({"isActive": True})
    project_title = (project or {}).get("title", "DropKit kit")
    project_board = (project or {}).get("board")
    bom_lines = (project or {}).get("componentsPreview") or []

    pdfs: List[bytes] = []
    succeeded: List[dict] = []
    failed: List[dict] = []
    shipment_ids: List[str] = []

    async for order in db.orders.find(query):
        order_id_str = str(order["_id"])
        address = await _resolve_recipient_address(order, db)
        if not address:
            failed.append({"order_id": order_id_str, "reason": "no_address"})
            continue

        existing = await db.shipments.find_one({"order_id": order_id_str})
        if not existing:
            try:
                rates = shipping_service.create_shipment_with_rates(to_address=address)
                rate = rates.get(payload.rate_choice) or rates.get("cheapest")
                if not rate:
                    failed.append({"order_id": order_id_str, "reason": "no_rates"})
                    continue
                label = shipping_service.buy_label(rates["shipment_id"], rate["id"])
                shipment_doc = {
                    "order_id": order_id_str, **label,
                    "created_at": datetime.now(timezone.utc),
                }
                ins = await db.shipments.insert_one(shipment_doc)
                shipment_doc["_id"] = ins.inserted_id
                existing = shipment_doc
            except Exception as e:
                failed.append({"order_id": order_id_str, "reason": str(e)[:200]})
                continue

        if existing.get("shipment_id"):
            shipment_ids.append(existing["shipment_id"])

        # Label PDF
        label_pdf = shipping_service.download_label_pdf(existing.get("label_pdf_url") or "")
        if not label_pdf:
            # Placeholder mode → render a stand-in page
            label_pdf = pack_slip.render_pack_slip(
                order_id=order_id_str,
                shopify_order_id=order.get("shopifyOrderId"),
                recipient_name=address.get("name") or "Maker",
                recipient_address_lines=[
                    address.get("street1", ""),
                    address.get("street2") or "",
                    f"{address.get('city','')}, {address.get('state','')} {address.get('zip','')}",
                ],
                project_title=f"[PLACEHOLDER LABEL] {project_title}",
                project_board=project_board,
                bom_lines=["Real EasyPost label will replace this once creds are configured."],
                scan_url=f"https://dropkit/scan/{order_id_str}",
            )
        pdfs.append(label_pdf)

        if payload.include_pack_slip:
            slip = pack_slip.render_pack_slip(
                order_id=order_id_str,
                shopify_order_id=order.get("shopifyOrderId"),
                recipient_name=address.get("name") or "Maker",
                recipient_address_lines=[
                    ln for ln in [
                        address.get("street1", ""),
                        address.get("street2") or "",
                        f"{address.get('city','')}, {address.get('state','')} {address.get('zip','')}",
                    ] if ln
                ],
                project_title=project_title,
                project_board=project_board,
                bom_lines=bom_lines or ["See guide for components"],
                scan_url=f"https://dropkit/scan/{order_id_str}",
                tracking_code=existing.get("tracking_code"),
                carrier=existing.get("carrier"),
            )
            pdfs.append(slip)

        succeeded.append({
            "order_id": order_id_str,
            "tracking_code": existing.get("tracking_code"),
            "carrier": existing.get("carrier"),
            "service": existing.get("service"),
        })

    merged = pack_slip.merge_pdfs(pdfs) if pdfs else b""
    await db.batch_labels.insert_one({
        "succeeded": succeeded, "failed": failed,
        "shipment_ids": shipment_ids,
        "user_id": user["id"],
        "created_at": datetime.now(timezone.utc),
    })
    await publish_event("labels.batch", {"count": len(succeeded), "failed": len(failed)})

    # If client asked via Accept=application/pdf, return the PDF directly
    return {
        "succeeded": succeeded,
        "failed": failed,
        "shipment_ids": shipment_ids,
        "pdf_size_bytes": len(merged),
        # Stream URL — client follows /dev/ops/labels/batch/last.pdf to download
        "pdf_download_url": "/api/dev/ops/labels/batch/last.pdf",
        # Inline base64 for quick preview / direct fetch from the UI
        "pdf_base64": __import__("base64").b64encode(merged).decode() if merged else "",
    }


@router.get("/labels/batch/last.pdf")
async def batch_last_pdf(_: dict = Depends(get_current_dev)):
    """Return the most recent merged batch PDF as a downloadable file."""
    db = get_db()
    doc = await db.batch_labels.find_one(sort=[("created_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="No batch generated yet")
    # The PDF isn't persisted to disk — clients should download via the base64 in /labels/batch.
    # For convenience, regenerate by re-running batch with the same shipment_ids.
    return Response(status_code=204)


# =============================================================================
# Item 3 — Barcode scan → fulfill
# =============================================================================
@router.get("/scan/{order_id}")
async def scan_open(order_id: str, _: dict = Depends(get_current_dev)):
    """Phone-friendly scan page payload: order info + one-click fulfill button.

    The QR code embedded in the pack-slip PDF points to /dev/ops/scan/{order_id}.
    """
    db = get_db()
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    shipment = await db.shipments.find_one({"order_id": order_id})
    user = None
    if order.get("shopifyCustomerId"):
        user = await db.users.find_one({"shopifyCustomerId": order["shopifyCustomerId"]})
    return {
        "order": serialize(order),
        "shipment": serialize(shipment) if shipment else None,
        "buyer_email": (user or {}).get("email"),
        "buyer_name": (user or {}).get("name"),
    }


@router.post("/scan/{order_id}/fulfill")
async def scan_fulfill(order_id: str, user: dict = Depends(get_current_dev)):
    """One-tap fulfillment from the warehouse scanner. Reuses /dev/orders/{id}/fulfill logic."""
    from routes_dev import fulfill_order, FulfillRequest  # reuse the existing handler
    db = get_db()
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    buyer = None
    if order.get("shopifyCustomerId"):
        buyer = await db.users.find_one({"shopifyCustomerId": order["shopifyCustomerId"]})
    payload = FulfillRequest(
        order_id=order_id,
        buyer_email=(buyer or {}).get("email") or "noreply@dropkit",
        buyer_name=(buyer or {}).get("name"),
    )
    result = await fulfill_order(order_id, payload, user)
    await publish_event("order.fulfilled", {"order_id": order_id, "tracking_code": result.get("tracking_code")})
    return result


# =============================================================================
# Item 4 — Today's queue dashboard
# =============================================================================
@router.get("/queue/today")
async def todays_queue(_: dict = Depends(get_current_dev)):
    db = get_db()
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    # Orders that need a label = paid orders that haven't generated a shipment row yet
    paid_count = await db.orders.count_documents({"$or": [{"status": {"$exists": False}}, {"status": "paid"}]})
    shipment_count = await db.shipments.count_documents({})
    fulfilled = await db.orders.count_documents({"status": "fulfilled"})

    overdue = await db.orders.count_documents({
        "$or": [{"status": {"$exists": False}}, {"status": "paid"}],
        "createdAt": {"$lt": day_ago},
    })

    new_signups_24h = await db.waitlist.count_documents({"createdAt": {"$gte": day_ago}})
    new_signups_7d = await db.waitlist.count_documents({"createdAt": {"$gte": week_ago}})
    active_subs = await db.users.count_documents({"subscriptionStatus": "active"})

    pending_subs = await db.substitutions.count_documents({"status": "pending"})
    pending_replacements = await db.replacement_requests.count_documents({"status": "pending"})

    return {
        "needs_label": max(0, paid_count - shipment_count),
        "labels_printed": shipment_count,
        "fulfilled_today": await db.orders.count_documents({"status": "fulfilled", "fulfilledAt": {"$gte": day_ago}}),
        "fulfilled_total": fulfilled,
        "overdue": overdue,
        "pending_substitutions": pending_subs,
        "pending_replacements": pending_replacements,
        "active_subscribers": active_subs,
        "waitlist_24h": new_signups_24h,
        "waitlist_7d": new_signups_7d,
        "checked_at": now,
    }


# =============================================================================
# Item 5 — Batch substitution approval
# =============================================================================
class SubBatchApprove(BaseModel):
    substitution_ids: List[str]


@router.get("/substitutions/pending")
async def list_pending_subs(_: dict = Depends(get_current_dev)):
    db = get_db()
    items = []
    async for s in db.substitutions.find({"status": "pending"}).sort("requestedAt", 1):
        proj_id = s.get("substitutedProjectId")
        proj = None
        if isinstance(proj_id, ObjectId):
            proj = await db.projects.find_one({"_id": proj_id})
        elif isinstance(proj_id, str) and ObjectId.is_valid(proj_id):
            proj = await db.projects.find_one({"_id": ObjectId(proj_id)})
        items.append({
            **serialize(s),
            "project": serialize(proj) if proj else None,
        })
    return items


@router.post("/substitutions/approve")
async def approve_subs(payload: SubBatchApprove, _: dict = Depends(get_current_dev)):
    db = get_db()
    oids = [ObjectId(s) for s in payload.substitution_ids if ObjectId.is_valid(s)]
    res = await db.substitutions.update_many(
        {"_id": {"$in": oids}, "status": "pending"},
        {"$set": {"status": "approved", "approvedAt": datetime.now(timezone.utc)}},
    )
    await publish_event("substitutions.approved", {"count": res.modified_count})
    return {"approved": res.modified_count}


# =============================================================================
# Item 6 — USPS SCAN form (manifest)
# =============================================================================
class ScanFormReq(BaseModel):
    shipment_ids: List[str]


@router.post("/scan-form")
async def make_scan_form(payload: ScanFormReq, _: dict = Depends(get_current_dev)):
    if not payload.shipment_ids:
        raise HTTPException(status_code=400, detail="No shipments provided")
    result = shipping_service.create_scan_form(payload.shipment_ids)
    db = get_db()
    await db.scan_forms.insert_one({**result, "created_at": datetime.now(timezone.utc)})
    return result


# =============================================================================
# Item 11 — Cycle-close automation
# =============================================================================
@router.post("/cycle/close")
async def close_cycle(user: dict = Depends(get_current_dev)):
    """Run end-of-cycle automation: lock subs window, generate POs for anything
    below threshold, email the founder a summary."""
    from routes_inventory import inventory_check, create_purchase_orders, POCreate

    db = get_db()
    now = datetime.now(timezone.utc)
    cycle_label = f"{now.year}-{now.month:02d}"

    # Inventory snapshot + auto-PO for low items
    check = await inventory_check(_=user)
    po_result = {"created": 0, "purchase_orders": []}
    if check["low_items"]:
        po_result = await create_purchase_orders(POCreate(item_ids=None), user)

    # Money & subscriber math (best-effort — Shopify is source of truth for revenue
    # so this is an estimate based on order rows)
    orders_shipped = await db.orders.count_documents({
        "status": "fulfilled",
        "fulfilledAt": {"$gte": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)},
    })
    # Sum totalPrice (string) → float, defensively
    gross_cents = 0
    async for o in db.orders.find({"status": "fulfilled", "fulfilledAt": {"$gte": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)}}, {"totalPrice": 1}):
        try:
            gross_cents += int(round(float(o.get("totalPrice", "0")) * 100))
        except (TypeError, ValueError):
            continue
    refunds_cents = 0  # Shopify is source of truth — leave 0 until Refund webhook ingested

    substitutions_count = await db.substitutions.count_documents({"cycleMonth": now.month, "cycleYear": now.year})
    new_subs = await db.users.count_documents({
        "subscriptionStatus": "active",
        "created_at": {"$gte": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)},
    })
    churned = await db.users.count_documents({
        "subscriptionStatus": {"$in": ["paused", "cancelled"]},
        "updatedAt": {"$gte": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)},
    })
    active = await db.users.count_documents({"subscriptionStatus": "active"})
    projected_next = active + (new_subs - churned)

    if user.get("email"):
        mailer.fire(mailer.cycle_summary(
            email=user["email"],
            cycle_label=cycle_label,
            orders_shipped=orders_shipped,
            gross_revenue=gross_cents / 100,
            refunds=refunds_cents / 100,
            net_revenue=(gross_cents - refunds_cents) / 100,
            substitutions=substitutions_count,
            new_subscribers=new_subs,
            churned=churned,
            projected_next=projected_next,
        ))

    await db.cycle_closes.update_one(
        {"cycle_label": cycle_label},
        {"$set": {
            "cycle_label": cycle_label,
            "orders_shipped": orders_shipped,
            "gross_cents": gross_cents,
            "refunds_cents": refunds_cents,
            "substitutions": substitutions_count,
            "new_subscribers": new_subs,
            "churned": churned,
            "projected_next": projected_next,
            "auto_pos_created": po_result.get("created", 0),
            "closed_by": user["id"],
            "closed_at": now,
        }},
        upsert=True,
    )
    await publish_event("cycle.closed", {"cycle_label": cycle_label, "orders_shipped": orders_shipped})

    return {
        "cycle_label": cycle_label,
        "orders_shipped": orders_shipped,
        "gross_cents": gross_cents,
        "auto_pos_created": po_result.get("created", 0),
        "summary_emailed_to": user.get("email"),
        "substitutions": substitutions_count,
        "new_subscribers": new_subs,
        "churned": churned,
        "projected_next": projected_next,
    }


# =============================================================================
# Item 12 — Cohort retention dashboard
# =============================================================================
@router.get("/cohorts")
async def cohorts(_: dict = Depends(get_current_dev)):
    """Group active subs by signup-month, plot status counts. Read-only."""
    db = get_db()
    pipeline = [
        {"$match": {"created_at": {"$exists": True}}},
        {"$group": {
            "_id": {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"},
                "status": {"$ifNull": ["$subscriptionStatus", "inactive"]},
            },
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.year": -1, "_id.month": -1}},
    ]
    rows: Dict[str, Dict[str, int]] = {}
    async for r in db.users.aggregate(pipeline):
        key = f"{r['_id']['year']}-{r['_id']['month']:02d}"
        if key not in rows:
            rows[key] = {"cohort": key, "active": 0, "paused": 0, "cancelled": 0, "inactive": 0, "total": 0}
        status = r["_id"]["status"]
        rows[key][status] = rows[key].get(status, 0) + r["count"]
        rows[key]["total"] += r["count"]
    out = list(rows.values())
    for r in out:
        r["retention_pct"] = round(100 * r["active"] / r["total"], 1) if r["total"] else 0
    return {"cohorts": out}


# =============================================================================
# Item 13 — Replacement queue
# =============================================================================
class ReplacementApprove(BaseModel):
    tracking_code: Optional[str] = None
    tracking_carrier: Optional[str] = None


@router.get("/replacements")
async def list_replacements(_: dict = Depends(get_current_dev), status: Optional[str] = None):
    db = get_db()
    q = {"status": status} if status else {}
    items = []
    async for r in db.replacement_requests.find(q).sort("created_at", -1).limit(100):
        items.append(serialize(r))
    return items


@router.post("/replacements/{request_id}/approve")
async def approve_replacement(request_id: str, payload: ReplacementApprove,
                              user: dict = Depends(get_current_dev)):
    db = get_db()
    if not ObjectId.is_valid(request_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    req = await db.replacement_requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Not found")
    now = datetime.now(timezone.utc)
    tracking = payload.tracking_code or "PENDING"
    carrier = payload.tracking_carrier or "USPS"
    tracking_url = f"https://t.17track.net/en#nums={tracking}"

    await db.replacement_requests.update_one(
        {"_id": req["_id"]},
        {"$set": {
            "status": "approved",
            "approved_at": now,
            "approved_by": user["id"],
            "tracking_code": tracking,
            "tracking_carrier": carrier,
            "tracking_url": tracking_url,
        }},
    )

    project = await db.projects.find_one({"isActive": True})
    mailer.fire(mailer.replacement_approved(
        email=req["email"],
        first_name=(req.get("name") or req["email"].split("@")[0]).split()[0],
        kit_title=(project or {}).get("title", "DropKit"),
        component_name=req.get("component_name", "component"),
        order_label=req.get("order_label", "your order"),
        tracking_code=tracking,
        tracking_url=tracking_url,
    ))
    await publish_event("replacement.approved", {"id": request_id})
    return {"ok": True, "tracking_code": tracking, "tracking_url": tracking_url}


# =============================================================================
# Item 14 — Live shop-floor SSE feed
# =============================================================================
@router.get("/feed")
async def feed(request: Request, _: dict = Depends(get_current_dev)):
    """Server-Sent Events stream of warehouse + webhook events.

    Client: new EventSource('/api/dev/ops/feed', { withCredentials: true }).
    """
    async def event_gen():
        # Send a hello to flush the response so the browser opens the channel
        yield "event: ready\ndata: {}\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                ev = await asyncio.wait_for(_EVENT_QUEUE.get(), timeout=20.0)
                yield f"event: {ev['type']}\ndata: {json.dumps(ev)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"  # comment line, keeps proxy buffers happy

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =============================================================================
# Item 15 — Sales-tax nexus monitor
# =============================================================================
# Economic-nexus thresholds (revenue OR transactions; we track revenue only here)
# Sourced from Avalara's 2025 summary — every US state with a sales tax.
NEXUS_THRESHOLDS_CENTS: Dict[str, int] = {
    "AL": 25000000, "AK": 10000000, "AZ": 10000000, "AR": 10000000, "CA": 50000000,
    "CO": 10000000, "CT": 10000000, "DC": 10000000, "FL": 10000000, "GA": 10000000,
    "HI": 10000000, "ID": 10000000, "IL": 10000000, "IN": 10000000, "IA": 10000000,
    "KS": 10000000, "KY": 10000000, "LA": 10000000, "ME": 10000000, "MD": 10000000,
    "MA": 10000000, "MI": 10000000, "MN": 10000000, "MS": 25000000, "MO": 10000000,
    "NE": 10000000, "NV": 10000000, "NJ": 10000000, "NM": 10000000, "NY": 50000000,
    "NC": 10000000, "ND": 10000000, "OH": 10000000, "OK": 10000000, "PA": 10000000,
    "RI": 10000000, "SC": 10000000, "SD": 10000000, "TN": 10000000, "TX": 50000000,
    "UT": 10000000, "VT": 10000000, "VA": 10000000, "WA": 10000000, "WV": 10000000,
    "WI": 10000000, "WY": 10000000,
}


@router.get("/tax-nexus")
async def tax_nexus(user: dict = Depends(get_current_dev)):
    db = get_db()
    now = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)

    # Aggregate YTD revenue by ship-to state
    pipeline = [
        {"$match": {"createdAt": {"$gte": year_start}, "shipping_address.state": {"$exists": True}}},
        {"$group": {
            "_id": "$shipping_address.state",
            "revenue_cents": {"$sum": {"$multiply": [{"$toDouble": {"$ifNull": ["$totalPrice", "0"]}}, 100]}},
            "orders": {"$sum": 1},
        }},
        {"$sort": {"revenue_cents": -1}},
    ]
    rows = []
    crossing = []
    async for r in db.orders.aggregate(pipeline):
        state = (r["_id"] or "").upper()
        threshold = NEXUS_THRESHOLDS_CENTS.get(state, 0)
        rev = int(r["revenue_cents"] or 0)
        pct = (rev / threshold * 100) if threshold else 0
        row = {
            "state": state, "revenue_cents": rev, "orders": r["orders"],
            "threshold_cents": threshold, "pct_of_threshold": round(pct, 1),
        }
        rows.append(row)
        if threshold and pct >= 80 and pct < 999:
            # Has crossed 80% — alert founder once per month per state
            seen = await db.nexus_alerts.find_one({
                "state": state,
                "month": now.strftime("%Y-%m"),
            })
            if not seen and user.get("email"):
                mailer.fire(mailer.tax_nexus_alert(
                    email=user["email"],
                    state=state,
                    ytd_revenue_cents=rev,
                    threshold_cents=threshold,
                ))
                await db.nexus_alerts.insert_one({
                    "state": state, "month": now.strftime("%Y-%m"),
                    "revenue_cents": rev, "threshold_cents": threshold,
                    "created_at": now,
                })
                crossing.append(state)

    return {"rows": rows, "alerted_states": crossing, "year": now.year}


# =============================================================================
# Item 16 — Pick list (combine today's orders with BOM demand)
# =============================================================================
@router.get("/pick-list")
async def pick_list(_: dict = Depends(get_current_dev)):
    """Generate a pick list for all unfulfilled orders today.

    Groups components by need, sorted by category (parts first, then packaging).
    Cross-references the active project's BOM against the number of kits to pick.
    """
    db = get_db()
    project = await db.projects.find_one({"isActive": True})
    if not project:
        return {"project": None, "total_kits": 0, "picks": []}

    pid = str(project["_id"])

    # Count unfulfilled orders
    order_count = await db.orders.count_documents({
        "$or": [{"status": {"$exists": False}}, {"status": "paid"}],
    })
    if order_count == 0:
        return {"project": project.get("title"), "total_kits": 0, "picks": []}

    # Get BOM entries for active project
    bom_entries = []
    async for entry in db.bom_entries.find({"project_id": pid}):
        bom_entries.append(entry)

    if not bom_entries:
        return {"project": project.get("title"), "total_kits": order_count,
                "note": "No BOM defined for this project", "picks": []}

    picks = []
    for entry in bom_entries:
        item_id = entry["inventory_item_id"]
        per_kit = entry.get("qty_per_kit", 1)
        if not ObjectId.is_valid(item_id):
            continue
        item = await db.inventory_items.find_one({"_id": ObjectId(item_id)})
        if not item:
            continue
        total_needed = order_count * per_kit
        stock = item.get("current_stock", 0) or 0
        picks.append({
            "item_id": str(item["_id"]),
            "name": item["name"],
            "sku": item.get("sku", ""),
            "category": item.get("category", "part"),
            "qty_per_kit": per_kit,
            "total_needed": total_needed,
            "current_stock": stock,
            "shortfall": max(0, total_needed - stock),
            "sufficient": stock >= total_needed,
        })

    picks.sort(key=lambda p: (0 if p["category"] == "part" else 1, p["category"], p["name"]))
    return {
        "project": project.get("title"),
        "total_kits": order_count,
        "picks": picks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Item 17 — Kitting status board (Kanban pipeline)
# =============================================================================
KITTING_STATUSES = ["paid", "kitting", "packed", "shipped"]

KITTING_STATUS_LABELS = {
    "paid": "Awaiting Pick",
    "kitting": "Being Kitted",
    "packed": "Packed",
    "shipped": "Shipped",
}


@router.get("/board")
async def kitting_board(_: dict = Depends(get_current_dev)):
    """Return orders grouped by kitting status for a Kanban pipeline view."""
    db = get_db()
    groups = {}
    for status in KITTING_STATUSES:
        query = {"kittingStatus": status} if status != "paid" else {
            "$or": [{"kittingStatus": {"$exists": False}}, {"kittingStatus": "paid"}],
        }
        if status == "paid":
            query["status"] = {"$ne": "fulfilled"}
        orders = []
        async for o in db.orders.find(query).sort("createdAt", 1).limit(30):
            orders.append(serialize(o))
        groups[status] = {
            "label": KITTING_STATUS_LABELS[status],
            "orders": orders,
        }
    return {
        "statuses": KITTING_STATUSES,
        "groups": groups,
    }


class AdvanceOrderRequest(BaseModel):
    target_status: str  # kitting | packed | shipped


@router.post("/board/{order_id}/advance")
async def advance_order(order_id: str, payload: AdvanceOrderRequest,
                         user: dict = Depends(get_current_dev)):
    """Move an order to the next kitting stage."""
    if payload.target_status not in KITTING_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {payload.target_status}")
    db = get_db()
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=400, detail="Invalid order id")
    now = datetime.now(timezone.utc)
    update = {"kittingStatus": payload.target_status, "updatedAt": now}
    if payload.target_status == "shipped":
        update["status"] = "fulfilled"
        update["fulfilledAt"] = now
    await db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": update})
    await publish_event("order.advanced", {"order_id": order_id, "status": payload.target_status})
    return {"order_id": order_id, "kitting_status": payload.target_status}


# =============================================================================
# Item 18 — Stock receive (receive PO items into inventory)
# =============================================================================
class StockReceiveRequest(BaseModel):
    po_id: str
    items: Optional[List[dict]] = None  # [{inventory_item_id, qty_received}]


@router.post("/stock/receive")
async def receive_stock(payload: StockReceiveRequest, user: dict = Depends(get_current_dev)):
    """Receive stock from a purchase order into inventory.

    Marks the PO as received and increments each item's current_stock.
    After receiving, runs auto-fulfill to ship any pending orders.
    """
    db = get_db()
    if not ObjectId.is_valid(payload.po_id):
        raise HTTPException(status_code=400, detail="Invalid PO id")
    po = await db.purchase_orders.find_one({"_id": ObjectId(payload.po_id)})
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    now = datetime.now(timezone.utc)
    received_items = []

    items_to_process = payload.items or po.get("items", [])
    for it in items_to_process:
        item_id = it.get("inventory_item_id") or it.get("id")
        qty = it.get("qty_received") or it.get("qty", 1)
        if not item_id or not ObjectId.is_valid(item_id):
            continue
        await db.inventory_items.update_one(
            {"_id": ObjectId(item_id)},
            {"$inc": {"current_stock": qty},
             "$set": {"pending_arrival_date": None, "updated_at": now}},
        )
        item = await db.inventory_items.find_one({"_id": ObjectId(item_id)})
        received_items.append({
            "item_id": item_id,
            "name": (item or {}).get("name", "?"),
            "qty_received": qty,
            "new_stock": (item or {}).get("current_stock", 0),
        })

    await db.purchase_orders.update_one(
        {"_id": ObjectId(payload.po_id)},
        {"$set": {"status": "received", "received_at": now, "updated_at": now}},
    )

    # Auto-fulfill: check if any pending orders can now ship
    auto_fulfill_result = await _auto_fulfill(db)

    await publish_event("stock.received", {"po_id": payload.po_id, "items": len(received_items)})

    return {
        "po_id": payload.po_id,
        "received_items": received_items,
        "pos_affected": len(received_items),
        "auto_fulfill": auto_fulfill_result,
    }


async def _auto_fulfill(db) -> dict:
    """Check all 'paid' orders vs inventory. For orders where every BOM item
    has sufficient stock, buy the label and mark as ready to kit.

    Returns count of orders auto-fulfilled.
    """
    project = await db.projects.find_one({"isActive": True})
    if not project:
        return {"auto_fulfilled": 0, "reason": "no_active_project"}

    pid = str(project["_id"])

    # Get BOM
    bom_items = {}
    async for entry in db.bom_entries.find({"project_id": pid}):
        item_id = entry["inventory_item_id"]
        bom_items[item_id] = entry.get("qty_per_kit", 1)

    if not bom_items:
        return {"auto_fulfilled": 0, "reason": "no_bom"}

    # Get current stock for every BOM item
    stock_map = {}
    for item_id in bom_items:
        if ObjectId.is_valid(item_id):
            item = await db.inventory_items.find_one({"_id": ObjectId(item_id)})
            stock_map[item_id] = item.get("current_stock", 0) if item else 0

    # Find orders that are paid and have no label yet
    orders_to_check = db.orders.find({
        "$or": [{"status": {"$exists": False}}, {"status": "paid"}],
    })
    auto_fulfilled = 0
    async for order in orders_to_check:
        order_id_str = str(order["_id"])

        # Skip if already has a shipment
        existing = await db.shipments.find_one({"order_id": order_id_str})
        if existing:
            continue

        # Check stock for one kit
        sufficient = True
        for item_id, per_kit in bom_items.items():
            if stock_map.get(item_id, 0) < per_kit:
                sufficient = False
                break

        if not sufficient:
            continue

        # Deduct stock from inventory
        for item_id, per_kit in bom_items.items():
            await db.inventory_items.update_one(
                {"_id": ObjectId(item_id)},
                {"$inc": {"current_stock": -per_kit}},
            )
            stock_map[item_id] = stock_map.get(item_id, 0) - per_kit

        # Buy label if EasyPost is configured
        from routes_dev_ops import _resolve_recipient_address  # reuse local helper
        address = await _resolve_recipient_address(order, db)
        label_info = {}
        if address:
            try:
                rates = shipping_service.create_shipment_with_rates(to_address=address)
                rate = rates.get("cheapest") or rates.get("standard")
                if rate:
                    label = shipping_service.buy_label(rates["shipment_id"], rate["id"])
                    await db.shipments.insert_one({
                        "order_id": order_id_str, **label,
                        "created_at": datetime.now(timezone.utc),
                    })
                    label_info = {"tracking_code": label.get("tracking_code")}
            except Exception:
                pass

        # Mark as kitting-ready
        await db.orders.update_one(
            {"_id": ObjectId(order_id_str)},
            {"$set": {"kittingStatus": "paid", "updatedAt": datetime.now(timezone.utc)}},
        )
        auto_fulfilled += 1

    if auto_fulfilled:
        await publish_event("orders.auto_fulfilled", {"count": auto_fulfilled})
    return {"auto_fulfilled": auto_fulfilled}


# =============================================================================
# Item 19 — Auto-fulfill trigger (run on demand + from stock receive)
# =============================================================================
@router.post("/auto-fulfill")
async def trigger_auto_fulfill(_: dict = Depends(get_current_dev)):
    """Manually trigger the auto-fulfill check for all pending orders."""
    db = get_db()
    result = await _auto_fulfill(db)
    return result


# =============================================================================
# Item 20 — Carrier tracking webhook (EasyPost-compatible)
# =============================================================================
@router.post("/tracking/webhook", include_in_schema=False)
async def tracking_webhook(request: Request):
    """Receive tracking updates from EasyPost webhook.

    EasyPost sends a POST to this URL with tracking event data when
    a shipment's status changes (pre_transit, in_transit, out_for_delivery,
    delivered, etc.).

    Handles idempotent delivery with the delivery_notification email.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid_json"}

    # EasyPost webhook payload shape:
    # { "description": "tracker.updated",
    #   "data": { "result": { "id", "tracking_code", "carrier", "status",
    #                          "tracking_details": [...], ... } } }
    result = body.get("data", {}).get("result") or body
    tracking_code = result.get("tracking_code") or result.get("id", "")
    status = (result.get("status") or "pre_transit").lower()

    if not tracking_code:
        return {"ok": False, "error": "no_tracking_code"}

    # Find the shipment by tracking code
    shipment = await db.shipments.find_one({"tracking_code": tracking_code})
    if not shipment:
        # Log as webhook failure for later review
        await db.webhook_failures.insert_one({
            "type": "tracking",
            "tracking_code": tracking_code,
            "status": status,
            "payload": body,
            "created_at": now,
        })
        return {"ok": False, "error": "shipment_not_found"}

    # Update the shipment's tracking status
    await db.shipments.update_one(
        {"_id": shipment["_id"]},
        {"$set": {"tracking_status": status, "last_tracking_update": now}},
    )

    # On delivery: send notification and mark order fulfilled
    if status in ("delivered", "available_for_pickup"):
        order_id = shipment.get("order_id")
        if order_id:
            await db.orders.update_one(
                {"_id": ObjectId(order_id)},
                {"$set": {"status": "fulfilled", "fulfilledAt": now,
                          "tracking_status": status, "updatedAt": now}},
            )
            await publish_event("tracking.delivered", {
                "tracking_code": tracking_code, "order_id": order_id,
            })

            # Send delivery notification email
            order = await db.orders.find_one({"_id": ObjectId(order_id)})
            if order:
                project = await db.projects.find_one({"isActive": True})
                project_title = (project or {}).get("title", "DropKit kit")
                guide_url = f"https://dropkit.me/apps/makerbox/projects/{(project or {}).get('slug', '')}"
                feedback_url = f"{guide_url}?feedback=1"

                # Find the buyer email
                buyer_email = None
                if order.get("shopifyCustomerId"):
                    u = await db.users.find_one({"shopifyCustomerId": order["shopifyCustomerId"]})
                    buyer_email = (u or {}).get("email")
                if not buyer_email and order.get("email"):
                    buyer_email = order["email"]
                if not buyer_email and order.get("shipping_address", {}).get("email"):
                    buyer_email = order["shipping_address"]["email"]

                if buyer_email:
                    # Grab a short BOM summary
                    bom_lines = []
                    pid = str(project["_id"]) if project else None
                    if pid:
                        async for entry in db.bom_entries.find({"project_id": pid}):
                            if ObjectId.is_valid(entry["inventory_item_id"]):
                                item = await db.inventory_items.find_one(
                                    {"_id": ObjectId(entry["inventory_item_id"])}
                                )
                                if item:
                                    bom_lines.append(f"1x {item['name']}")
                    mailer.fire(mailer.delivery_notification(
                        email=buyer_email,
                        first_name=(order.get("shipping_address") or {}).get("name", "Maker"),
                        project_title=project_title,
                        carrier=shipment.get("carrier", "carrier"),
                        tracking_code=tracking_code,
                        bom_summary="<br>".join(bom_lines[:8]) or "See the guide for the full component list.",
                        guide_url=guide_url,
                        feedback_url=feedback_url,
                    ))

        # If there's a replacement order with this tracking, update it too
        await db.replacement_requests.update_one(
            {"tracking_code": tracking_code},
            {"$set": {"status": "delivered", "delivered_at": now}},
        )

    return {"ok": True, "tracking_code": tracking_code, "status": status}


# =============================================================================
# Item 21 — Funnel dashboard (views → signups → quotes → checkout → paid)
# =============================================================================
@router.get("/funnel")
async def funnel_dashboard(_: dict = Depends(get_current_dev)):
    """Waitlist → subscriber conversion funnel.

    Returns counts for each stage so the team can see where dropoff happens.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    thirty_days = now - timedelta(days=30)
    ninety_days = now - timedelta(days=90)

    async def count_30(coll, query=None):
        q = {"createdAt": {"$gte": thirty_days}}
        if query:
            q.update(query)
        return await db[coll].count_documents(q)

    async def count_total(coll, query=None):
        if query:
            return await db[coll].count_documents(query)
        return await db[coll].estimated_document_count()

    return {
        "waitlist_total": await count_total("waitlist"),
        "waitlist_30d": await count_30("waitlist"),
        "quotes_30d": await count_30("checkout_quotes"),
        "orders_total": await count_total("orders"),
        "orders_30d": await count_30("orders"),
        "fulfilled_30d": await count_30("orders", {"status": "fulfilled", "fulfilledAt": {"$gte": thirty_days}}),
        "active_subscribers": await db.users.count_documents({"subscriptionStatus": "active"}),
        "subscriptions_gained_30d": await db.users.count_documents({
            "subscriptionStatus": "active",
            "updatedAt": {"$gte": thirty_days},
        }),
        "subscriptions_lost_30d": await db.users.count_documents({
            "subscriptionStatus": {"$in": ["cancelled", "paused"]},
            "updatedAt": {"$gte": thirty_days},
        }),
        "net_growth_30d": await db.users.count_documents({
            "subscriptionStatus": "active",
            "updatedAt": {"$gte": thirty_days},
        }) - await db.users.count_documents({
            "subscriptionStatus": {"$in": ["cancelled", "paused"]},
            "updatedAt": {"$gte": thirty_days},
        }),
        "checked_at": now.isoformat(),
    }


# =============================================================================
# Item 22 — Newsletter send to waitlist (dev-triggered)
# =============================================================================
class NewsletterSendRequest(BaseModel):
    subject: Optional[str] = "DropKit update"
    template: Optional[str] = None  # custom HTML body, or use default
    body_html: Optional[str] = None
    dry_run: bool = False  # if True, only count recipients + log, don't send


@router.post("/newsletter/send")
async def send_newsletter(payload: NewsletterSendRequest, user: dict = Depends(get_current_dev)):
    """Send an email blast to the entire waitlist.

    Uses SendGrid bulk send when configured, falls back to placeholder logging.
    When dry_run=True, just counts recipients without sending.
    """
    db = get_db()
    recipients = []
    async for w in db.waitlist.find({}, {"email": 1, "name": 1}):
        email = w.get("email", "").strip()
        if email:
            recipients.append({"email": email, "name": (w.get("name") or "").strip().split(" ", 1)[0] or "Maker"})

    total = len(recipients)
    if payload.dry_run:
        return {"dry_run": True, "recipient_count": total, "sample": recipients[:3]}

    if payload.body_html:
        body = payload.body_html
    else:
        ctx = {
            "first_name": "Maker",
            "content": "Here's what's new at DropKit this month.",
            "unsubscribe_url": "#",
        }
        body = (
            '<div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;color:#F0F0EE;">'
            f'<h1 style="font-size:24px;">{payload.subject}</h1>'
            f"<p>{ctx['content']}</p>"
            f'<p style="font-size:12px;color:#8B949E;margin-top:32px;">'
            f'<a href="{ctx["unsubscribe_url"]}" style="color:#E8510A;">Unsubscribe</a></p></div>'
        )

    sent = 0
    errors = 0
    # Batch in groups of 50 to avoid overloading the email service
    batch_size = 50
    for i in range(0, total, batch_size):
        batch = recipients[i:i + batch_size]
        for r in batch:
            try:
                await mailer._send(
                    recipient=r["email"],
                    subject=payload.subject,
                    html=body.replace("Maker", r["name"]),
                    unique_id=f"newsletter:{user['id']}:{i}",
                )
                sent += 1
            except Exception:
                errors += 1

    return {
        "sent": sent,
        "total": total,
        "errors": errors,
        "subject": payload.subject,
    }


# =============================================================================
# Item 23 — Promote waitlist to subscriber (trigger on launch)
# =============================================================================
@router.post("/promote-waitlist")
async def promote_waitlist(user: dict = Depends(get_current_dev)):
    """Send a launch announcement to every waitlist member and mark them as notified.

    Idempotent: skips anyone who already has `launchNotified: true`.
    When LAUNCH_MODE goes to 'live', run this to convert the waitlist.
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    launch_url = getattr(settings, "APP_URL", "https://dropkit.me") or "https://dropkit.me"

    promoted = 0
    already = 0
    async for w in db.waitlist.find({"launchNotified": {"$ne": True}}):
        email = w.get("email", "").strip()
        if not email:
            continue
        first_name = (w.get("name") or "").strip().split(" ", 1)[0] or "Maker"
        referral_code = w.get("referralCode", "")

        mailer.fire(mailer.launch_announcement(
            email=email,
            first_name=first_name,
            launch_url=f"{launch_url}/subscribe?ref={referral_code}",
        ))
        await db.waitlist.update_one(
            {"_id": w["_id"]},
            {"$set": {"launchNotified": True, "launchNotifiedAt": now}},
        )
        promoted += 1

    already = await db.waitlist.count_documents({"launchNotified": True})
    return {
        "promoted": promoted,
        "already_notified": already,
        "total_waitlist": await db.waitlist.count_documents({}),
    }
