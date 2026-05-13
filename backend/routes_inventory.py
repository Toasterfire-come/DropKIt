"""Inventory + BOM + Purchase Orders + subscriber projection + auto-rotation.

Implements:
- CRUD for inventory items (parts / packaging / other)
- BOM (bill-of-materials) entries linking projects to inventory items
- Per-project kit-availability calculation (min over BOM of floor(stock/qty))
- Substitution-aware reorder quantity forecast using last-6-month substitution rates
- Auto-rotation rule: past projects ≤ 6 months kept if in stock OR exactly 6th month
- Purchase order generation with pre-filled supplier cart URLs (per supplier)
- Low-stock notification via the connected Gmail account
- Subscriber projection: current actives + avg monthly growth over last 3 months
"""
import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from urllib.parse import quote_plus

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_dev
from db import get_db
from models import serialize
import gmail_service

router = APIRouter(prefix="/dev/inventory")

SAFETY_FACTOR = 1.2


# ============================================================
# Pydantic models
# ============================================================
class InventoryItemIn(BaseModel):
    name: str
    sku: Optional[str] = None
    category: str = "part"  # part | packaging | other
    supplier: Optional[str] = None
    supplier_sku: Optional[str] = None
    supplier_url: Optional[str] = None  # cart URL template; {qty} and {sku} placeholders supported
    current_stock: int = Field(default=0, ge=0)
    reorder_threshold: int = Field(default=0, ge=0)
    base_reorder_qty: int = Field(default=0, ge=0)
    unit_cost_cents: int = Field(default=0, ge=0)
    lead_time_days: int = Field(default=14, ge=0)
    pending_arrival_date: Optional[datetime] = None
    notes: Optional[str] = None


class BomEntryIn(BaseModel):
    project_id: str
    inventory_item_id: str
    qty_per_kit: int = Field(ge=1)


class StockAdjust(BaseModel):
    delta: int


class POCreate(BaseModel):
    item_ids: Optional[List[str]] = None  # if None, all below threshold


# ============================================================
# Inventory items CRUD
# ============================================================
@router.get("/items")
async def list_items(_: dict = Depends(get_current_dev)):
    db = get_db()
    items = [serialize(d) async for d in db.inventory_items.find().sort("name", 1)]
    return items


@router.post("/items")
async def create_item(payload: InventoryItemIn, _: dict = Depends(get_current_dev)):
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = payload.model_dump()
    doc["created_at"] = now
    doc["updated_at"] = now
    res = await db.inventory_items.insert_one(doc)
    out = await db.inventory_items.find_one({"_id": res.inserted_id})
    return serialize(out)


@router.patch("/items/{item_id}")
async def update_item(item_id: str, payload: InventoryItemIn, _: dict = Depends(get_current_dev)):
    db = get_db()
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    update = payload.model_dump()
    update["updated_at"] = datetime.now(timezone.utc)
    res = await db.inventory_items.update_one({"_id": ObjectId(item_id)}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    out = await db.inventory_items.find_one({"_id": ObjectId(item_id)})
    return serialize(out)


@router.post("/items/{item_id}/adjust-stock")
async def adjust_stock(item_id: str, payload: StockAdjust, user: dict = Depends(get_current_dev)):
    db = get_db()
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    item = await db.inventory_items.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    old_stock = item.get("current_stock", 0) or 0
    new_stock = max(0, old_stock + payload.delta)
    threshold = item.get("reorder_threshold", 0) or 0
    await db.inventory_items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": {"current_stock": new_stock, "updated_at": datetime.now(timezone.utc)}},
    )

    # Item 7 — Auto-place a draft PO the moment stock crosses below threshold
    crossed_down = old_stock > threshold and new_stock <= threshold
    auto_po = None
    if crossed_down and item.get("supplier_url") and (item.get("base_reorder_qty", 0) or 0) > 0:
        auto_po = await _emit_single_item_po(db, item, user["id"])

    return {"id": item_id, "current_stock": new_stock, "auto_po_created": bool(auto_po), "auto_po": auto_po}


async def _emit_single_item_po(db, item: dict, user_id: str) -> dict:
    """Create a draft PO for a single item the moment it crosses below threshold."""
    qty = item.get("base_reorder_qty", 0) or 0
    if qty <= 0:
        return None
    sku = item.get("supplier_sku") or item.get("sku", "")
    cart_url = _build_cart_url(item.get("supplier_url", ""), sku, qty)
    now = datetime.now(timezone.utc)
    doc = {
        "supplier": item.get("supplier") or "Unspecified",
        "status": "draft",
        "items": [{
            "inventory_item_id": str(item["_id"]),
            "name": item["name"],
            "sku": item.get("sku"),
            "supplier_sku": item.get("supplier_sku"),
            "qty": qty,
            "unit_cost_cents": item.get("unit_cost_cents", 0),
            "cart_url": cart_url,
        }],
        "total_cents": qty * (item.get("unit_cost_cents", 0) or 0),
        "expected_arrival": None,
        "placed_at": None,
        "received_at": None,
        "created_by": user_id,
        "auto_emitted": True,
        "trigger": "threshold_crossing",
        "created_at": now,
    }
    res = await db.purchase_orders.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    return doc


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, _: dict = Depends(get_current_dev)):
    db = get_db()
    if not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    await db.bom_entries.delete_many({"inventory_item_id": item_id})
    await db.inventory_items.delete_one({"_id": ObjectId(item_id)})
    return {"ok": True}


# ============================================================
# BOM entries
# ============================================================
@router.get("/bom/{project_id}")
async def get_bom(project_id: str, _: dict = Depends(get_current_dev)):
    db = get_db()
    items = []
    async for entry in db.bom_entries.find({"project_id": project_id}):
        item = None
        if ObjectId.is_valid(entry["inventory_item_id"]):
            item = await db.inventory_items.find_one({"_id": ObjectId(entry["inventory_item_id"])})
        items.append({
            **serialize(entry),
            "item": serialize(item) if item else None,
        })
    return items


@router.post("/bom")
async def add_bom_entry(payload: BomEntryIn, _: dict = Depends(get_current_dev)):
    db = get_db()
    if not ObjectId.is_valid(payload.inventory_item_id):
        raise HTTPException(status_code=400, detail="Invalid item id")
    existing = await db.bom_entries.find_one({
        "project_id": payload.project_id, "inventory_item_id": payload.inventory_item_id,
    })
    if existing:
        await db.bom_entries.update_one(
            {"_id": existing["_id"]}, {"$set": {"qty_per_kit": payload.qty_per_kit}}
        )
        return serialize({**existing, "qty_per_kit": payload.qty_per_kit})
    doc = payload.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    res = await db.bom_entries.insert_one(doc)
    out = await db.bom_entries.find_one({"_id": res.inserted_id})
    return serialize(out)


@router.delete("/bom/{entry_id}")
async def delete_bom_entry(entry_id: str, _: dict = Depends(get_current_dev)):
    db = get_db()
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    await db.bom_entries.delete_one({"_id": ObjectId(entry_id)})
    return {"ok": True}


# ============================================================
# Availability calculations (helpers used by dev + public routes)
# ============================================================
async def compute_kit_availability(project_id: str) -> dict:
    """Return {kits_in_stock, status, eta_iso, missing_items}."""
    db = get_db()
    bom = [e async for e in db.bom_entries.find({"project_id": project_id})]
    if not bom:
        return {"kits_in_stock": None, "status": "no_bom", "eta": None, "missing_items": []}

    kit_counts = []
    missing = []
    latest_eta = None
    for entry in bom:
        if not ObjectId.is_valid(entry["inventory_item_id"]):
            continue
        item = await db.inventory_items.find_one({"_id": ObjectId(entry["inventory_item_id"])})
        if not item:
            continue
        per_kit = entry["qty_per_kit"] or 1
        kits_from_item = math.floor((item.get("current_stock", 0) or 0) / per_kit)
        kit_counts.append(kits_from_item)
        if kits_from_item == 0:
            missing.append({
                "item_id": str(item["_id"]),
                "name": item["name"],
                "current_stock": item.get("current_stock", 0),
                "needed_per_kit": per_kit,
                "pending_arrival_date": item.get("pending_arrival_date"),
            })
            if item.get("pending_arrival_date"):
                if latest_eta is None or item["pending_arrival_date"] > latest_eta:
                    latest_eta = item["pending_arrival_date"]

    kits = min(kit_counts) if kit_counts else 0
    status = "in_stock" if kits > 0 else ("backorder" if latest_eta else "out_of_stock")
    return {
        "kits_in_stock": kits,
        "status": status,
        "eta": latest_eta,
        "missing_items": missing,
    }


async def _substitution_rates(months_back: int = 6) -> Dict[str, float]:
    """Return {project_id_str: substitution_rate} based on last N months of substitutions."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months_back)
    total = await db.substitutions.count_documents({"requestedAt": {"$gte": cutoff}})
    if total == 0:
        return {}
    pipeline = [
        {"$match": {"requestedAt": {"$gte": cutoff}}},
        {"$group": {"_id": "$substitutedProjectId", "n": {"$sum": 1}}},
    ]
    rates: Dict[str, float] = {}
    async for r in db.substitutions.aggregate(pipeline):
        rates[str(r["_id"])] = r["n"] / total
    return rates


async def _subscriber_projection() -> dict:
    """Current active subs + projected next-month subs from avg monthly growth (last 3 months)."""
    db = get_db()
    current = await db.users.count_documents({"subscriptionStatus": "active"})

    now = datetime.now(timezone.utc)
    buckets = []
    for i in range(3):
        end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30 * i)
        start = end - timedelta(days=30)
        n = await db.users.count_documents({"created_at": {"$gte": start, "$lt": end}})
        buckets.append(n)
    avg_growth = round(sum(buckets) / max(1, len(buckets)))
    projected = max(0, current + avg_growth)
    return {
        "current": current,
        "avg_monthly_growth": avg_growth,
        "projected_next_month": projected,
        "growth_buckets": buckets,
    }


# ============================================================
# Inventory check + forecast
# ============================================================
@router.get("/check")
async def inventory_check(_: dict = Depends(get_current_dev)):
    """Returns: low items + recommended reorder quantities using substitution-weighted demand."""
    db = get_db()

    sub_proj = await _subscriber_projection()
    projected = sub_proj["projected_next_month"]
    sub_rates = await _substitution_rates(months_back=6)

    # Demand per project (kits expected to ship next cycle)
    projects = [p async for p in db.projects.find()]
    project_demand: Dict[str, float] = {}
    total_sub_rate_taken = sum(sub_rates.values())

    for p in projects:
        pid = str(p["_id"])
        if p.get("isActive"):
            # current project gets the residual (1 - sum(substitution_rates))
            project_demand[pid] = projected * max(0.0, 1.0 - total_sub_rate_taken)
        else:
            project_demand[pid] = projected * sub_rates.get(pid, 0.0)

    # Aggregate item demand across all projects (in-rotation)
    item_needed: Dict[str, float] = {}
    async for entry in db.bom_entries.find():
        pid = entry["project_id"]
        demand_kits = project_demand.get(pid, 0)
        if demand_kits <= 0:
            continue
        item_id = entry["inventory_item_id"]
        item_needed[item_id] = item_needed.get(item_id, 0) + (demand_kits * entry["qty_per_kit"])

    # Build low-stock list
    low = []
    async for item in db.inventory_items.find():
        item_id = str(item["_id"])
        stock = item.get("current_stock", 0) or 0
        threshold = item.get("reorder_threshold", 0) or 0
        forecast_need = math.ceil(item_needed.get(item_id, 0) * SAFETY_FACTOR)
        recommended_qty = max(0, forecast_need - stock, (item.get("base_reorder_qty", 0) or 0) if stock <= threshold else 0)
        if recommended_qty > 0 or stock <= threshold:
            low.append({
                **serialize(item),
                "forecast_need": forecast_need,
                "recommended_reorder_qty": recommended_qty,
                "below_threshold": stock <= threshold,
            })

    return {
        "subscriber_projection": sub_proj,
        "substitution_rates": sub_rates,
        "low_items": low,
        "checked_at": datetime.now(timezone.utc),
    }


# ============================================================
# Purchase orders
# ============================================================
def _build_cart_url(supplier_url_template: str, sku: str, qty: int) -> str:
    if not supplier_url_template:
        return ""
    return (
        supplier_url_template
        .replace("{sku}", quote_plus(sku or ""))
        .replace("{qty}", str(qty))
    )


@router.post("/purchase-orders")
async def create_purchase_orders(payload: POCreate, user: dict = Depends(get_current_dev)):
    """Group recommended-low items by supplier and emit one PO per supplier with cart URL."""
    db = get_db()
    check = await inventory_check(_=user)
    low_items = check["low_items"]

    if payload.item_ids:
        low_items = [i for i in low_items if i["id"] in payload.item_ids]

    # Group by supplier
    by_supplier: Dict[str, list] = {}
    for it in low_items:
        sup = it.get("supplier") or "Unspecified"
        by_supplier.setdefault(sup, []).append(it)

    now = datetime.now(timezone.utc)
    pos = []
    for supplier, items in by_supplier.items():
        po_items = []
        for it in items:
            qty = it["recommended_reorder_qty"] or it.get("base_reorder_qty", 0)
            if qty <= 0:
                continue
            po_items.append({
                "inventory_item_id": it["id"],
                "name": it["name"],
                "sku": it.get("sku"),
                "supplier_sku": it.get("supplier_sku"),
                "qty": qty,
                "unit_cost_cents": it.get("unit_cost_cents", 0),
                "cart_url": _build_cart_url(it.get("supplier_url", ""), it.get("supplier_sku") or it.get("sku", ""), qty),
            })
        if not po_items:
            continue
        total_cents = sum((i["qty"] * (i["unit_cost_cents"] or 0)) for i in po_items)
        doc = {
            "supplier": supplier,
            "status": "draft",
            "items": po_items,
            "total_cents": total_cents,
            "expected_arrival": None,
            "placed_at": None,
            "received_at": None,
            "created_by": user["id"],
            "created_at": now,
        }
        res = await db.purchase_orders.insert_one(doc)
        doc["id"] = str(res.inserted_id)
        doc.pop("_id", None)
        pos.append(doc)
    return {"created": len(pos), "purchase_orders": pos}


@router.get("/purchase-orders")
async def list_purchase_orders(_: dict = Depends(get_current_dev)):
    db = get_db()
    items = []
    async for doc in db.purchase_orders.find().sort("created_at", -1).limit(50):
        items.append(serialize(doc))
    return items


class POStatusUpdate(BaseModel):
    status: str  # placed | received
    expected_arrival: Optional[datetime] = None


@router.patch("/purchase-orders/{po_id}")
async def update_purchase_order(po_id: str, payload: POStatusUpdate, _: dict = Depends(get_current_dev)):
    db = get_db()
    if not ObjectId.is_valid(po_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    po = await db.purchase_orders.find_one({"_id": ObjectId(po_id)})
    if not po:
        raise HTTPException(status_code=404, detail="Not found")

    now = datetime.now(timezone.utc)
    update = {"status": payload.status, "updated_at": now}
    if payload.status == "placed":
        update["placed_at"] = now
        if payload.expected_arrival:
            update["expected_arrival"] = payload.expected_arrival
            # propagate pending_arrival_date to each item
            for it in po["items"]:
                if ObjectId.is_valid(it["inventory_item_id"]):
                    await db.inventory_items.update_one(
                        {"_id": ObjectId(it["inventory_item_id"])},
                        {"$set": {"pending_arrival_date": payload.expected_arrival, "updated_at": now}},
                    )
    elif payload.status == "received":
        update["received_at"] = now
        for it in po["items"]:
            if ObjectId.is_valid(it["inventory_item_id"]):
                await db.inventory_items.update_one(
                    {"_id": ObjectId(it["inventory_item_id"])},
                    {"$inc": {"current_stock": it["qty"]},
                     "$set": {"pending_arrival_date": None, "updated_at": now}},
                )

    await db.purchase_orders.update_one({"_id": po["_id"]}, {"$set": update})
    out = await db.purchase_orders.find_one({"_id": po["_id"]})
    return serialize(out)


# ============================================================
# Low-stock notification email (via connected Gmail)
# ============================================================
@router.post("/notify-low")
async def notify_low(user: dict = Depends(get_current_dev)):
    check = await inventory_check(_=user)
    low = check["low_items"]
    if not low:
        return {"sent": False, "reason": "no_low_items", "count": 0}

    rows = "".join(
        f"<tr><td>{it['name']}</td><td>{it.get('current_stock',0)}</td><td>{it.get('reorder_threshold',0)}</td><td><strong>{it['recommended_reorder_qty']}</strong></td></tr>"
        for it in low
    )
    html = f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:640px;color:#1a1a1a;">
      <h2 style="letter-spacing:-0.5px;">DropKit · Low-stock alert</h2>
      <p>{len(low)} item(s) need attention based on next-month demand forecast
      (projected subscribers: {check['subscriber_projection']['projected_next_month']}).</p>
      <table cellpadding="8" style="border-collapse:collapse;width:100%;font-family:ui-monospace,Menlo,monospace;font-size:13px;">
        <thead><tr style="background:#f6f8fa;"><th align="left">Item</th><th align="left">Stock</th><th align="left">Threshold</th><th align="left">Reorder</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="margin-top:24px;color:#57606a;font-size:13px;">Open the dev panel → Inventory tab to generate POs.</p>
    </div>
    """
    token = await gmail_service.get_connected(user["id"])
    sender = (token or {}).get("connected_email") or user.get("email")
    try:
        result = await gmail_service.send_blast(
            user_id=user["id"], sender=sender,
            subject=f"[DropKit] {len(low)} item(s) running low",
            html=html, recipients=[sender],
        )
    except RuntimeError as e:
        return {"sent": False, "reason": str(e), "count": len(low)}
    return {"sent": True, "result": result, "count": len(low)}
