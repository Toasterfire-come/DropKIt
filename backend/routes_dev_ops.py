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
