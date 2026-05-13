"""Admin endpoints — protected by either a static admin token OR a dev JWT cookie.

Either credential works:
  • `X-Admin-Token` header matching `ADMIN_API_TOKEN` env (for cron / curl / scripts), OR
  • Logged-in dev user (role=dev) via JWT cookie (for the /dev UI panel).
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from auth import decode_token
from config import settings
from db import get_db
from models import ProjectCreate, serialize
import email_service as mailer

router = APIRouter(prefix="/admin")


async def require_admin(request: Request, x_admin_token: str = Header(default="")):
    """Pass if either: static admin token matches, OR caller is an authenticated dev."""
    if settings.ADMIN_API_TOKEN and x_admin_token == settings.ADMIN_API_TOKEN:
        return
    # Fallback: dev JWT cookie
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = decode_token(token)
            if payload.get("role") == "dev":
                return
        except HTTPException:
            pass
    raise HTTPException(status_code=401, detail="Admin auth required")


@router.post("/projects", dependencies=[])
async def create_project(payload: ProjectCreate, _admin: None = Depends(require_admin)):
    db = get_db()

    existing = await db.projects.find_one({"slug": payload.slug})
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")

    if payload.isActive:
        await db.projects.update_many({"isActive": True}, {"$set": {"isActive": False}})

    doc = payload.model_dump()
    doc["createdAt"] = datetime.now(timezone.utc)
    res = await db.projects.insert_one(doc)
    out = await db.projects.find_one({"_id": res.inserted_id})
    return serialize(out)


@router.patch("/projects/{project_id}/activate")
async def activate_project(project_id: str, _admin: None = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    await db.projects.update_many({"isActive": True}, {"$set": {"isActive": False}})
    res = await db.projects.update_one(
        {"_id": ObjectId(project_id)}, {"$set": {"isActive": True}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, _admin: None = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    await db.projects.delete_one({"_id": ObjectId(project_id)})
    return {"ok": True}


@router.post("/vote-cycles")
async def create_vote_cycle(
    payload: dict, _admin: None = Depends(require_admin)
):
    db = get_db()
    required = {"cycleMonth", "cycleYear", "candidateProjectIds", "votingOpenAt", "votingCloseAt"}
    missing = required - set(payload.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing: {missing}")

    payload["candidateProjectIds"] = [
        ObjectId(c) if ObjectId.is_valid(c) else c for c in payload["candidateProjectIds"]
    ]
    payload["votingOpenAt"] = datetime.fromisoformat(payload["votingOpenAt"].replace("Z", "+00:00"))
    payload["votingCloseAt"] = datetime.fromisoformat(payload["votingCloseAt"].replace("Z", "+00:00"))
    payload["winnerId"] = None

    res = await db.vote_cycles.insert_one(payload)
    return {"ok": True, "id": str(res.inserted_id)}


@router.get("/waitlist/count")
async def waitlist_count(_admin: None = Depends(require_admin)):
    db = get_db()
    return {"count": await db.waitlist.count_documents({})}


@router.get("/substitutions")
async def list_substitutions(_admin: None = Depends(require_admin)):
    db = get_db()
    items = []
    async for d in db.substitutions.find().sort("requestedAt", -1).limit(100):
        items.append(serialize(d))
    return items


# ============================================================
# Email broadcasts — manual triggers for lifecycle emails
# ============================================================
async def _iter_active_subs(db):
    async for u in db.users.find({"subscriptionStatus": "active"}):
        yield u


@router.post("/broadcasts/vote-opened")
async def broadcast_vote_opened(payload: dict, _admin: None = Depends(require_admin)):
    """Fire 'Vote Opened' Klaviyo event to every active subscriber.

    payload: { cycleId: <vote_cycles _id> }
    """
    db = get_db()
    cycle_id = payload.get("cycleId")
    if not cycle_id or not ObjectId.is_valid(cycle_id):
        raise HTTPException(status_code=400, detail="cycleId required")
    cycle = await db.vote_cycles.find_one({"_id": ObjectId(cycle_id)})
    if not cycle:
        raise HTTPException(status_code=404, detail="Vote cycle not found")

    # Hydrate candidates for the email body
    cand_ids = [c if isinstance(c, ObjectId) else ObjectId(c) for c in cycle.get("candidateProjectIds", []) if (isinstance(c, ObjectId) or ObjectId.is_valid(c))]
    candidates = []
    async for p in db.projects.find({"_id": {"$in": cand_ids}}):
        candidates.append({"title": p.get("title"), "board": p.get("board"), "difficulty": p.get("difficulty")})

    cycle_label = f"{cycle['cycleYear']}-{cycle['cycleMonth']:02d}"
    closes_at = cycle["votingCloseAt"].isoformat() if cycle.get("votingCloseAt") else ""
    vote_url = f"{(settings.APP_URL or '').rstrip('/')}/apps/makerbox/vote"

    sent = 0
    async for u in _iter_active_subs(db):
        if not u.get("email"):
            continue
        first = (u.get("name") or "").split(" ", 1)[0] if u.get("name") else u["email"].split("@")[0]
        mailer.fire(mailer.vote_opened(
            email=u["email"],
            first_name=first,
            cycle_label=cycle_label,
            candidates=candidates,
            vote_url=vote_url,
            closes_at=closes_at,
        ))
        sent += 1
    return {"ok": True, "queued": sent}


@router.post("/broadcasts/vote-results")
async def broadcast_vote_results(payload: dict, _admin: None = Depends(require_admin)):
    """Fire 'Vote Results' to every active subscriber after a winner is set.

    payload: { cycleId: <vote_cycles _id> }
    """
    db = get_db()
    cycle_id = payload.get("cycleId")
    if not cycle_id or not ObjectId.is_valid(cycle_id):
        raise HTTPException(status_code=400, detail="cycleId required")
    cycle = await db.vote_cycles.find_one({"_id": ObjectId(cycle_id)})
    if not cycle or not cycle.get("winnerId"):
        raise HTTPException(status_code=400, detail="Vote cycle has no winner")

    winner = await db.projects.find_one({"_id": cycle["winnerId"] if isinstance(cycle["winnerId"], ObjectId) else ObjectId(cycle["winnerId"])})
    total_votes = await db.votes.count_documents({"voteCycleId": cycle["_id"]})
    cycle_label = f"{cycle['cycleYear']}-{cycle['cycleMonth']:02d}"
    winner_url = f"{(settings.APP_URL or '').rstrip('/')}/apps/makerbox/projects/{(winner or {}).get('slug', '')}"

    sent = 0
    async for u in _iter_active_subs(db):
        if not u.get("email"):
            continue
        first = (u.get("name") or "").split(" ", 1)[0] if u.get("name") else u["email"].split("@")[0]
        mailer.fire(mailer.vote_results(
            email=u["email"],
            first_name=first,
            cycle_label=cycle_label,
            winner_title=(winner or {}).get("title", "TBA"),
            winner_url=winner_url,
            total_votes=total_votes,
        ))
        sent += 1
    return {"ok": True, "queued": sent}


@router.post("/broadcasts/launch-announcement")
async def broadcast_launch_announcement(_admin: None = Depends(require_admin)):
    """Fire 'Launch Announcement' to the entire waitlist (use when flipping LAUNCH_MODE=live)."""
    db = get_db()
    launch_url = (settings.APP_URL or "").rstrip("/") + "/"
    sent = 0
    async for w in db.waitlist.find():
        if not w.get("email"):
            continue
        first = (w.get("name") or "").split(" ", 1)[0] if w.get("name") else w["email"].split("@")[0]
        mailer.fire(mailer.launch_announcement(
            email=w["email"],
            first_name=first,
            launch_url=launch_url,
        ))
        sent += 1
    return {"ok": True, "queued": sent}
