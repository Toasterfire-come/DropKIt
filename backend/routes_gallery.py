"""Community gallery — build submissions and public showcase."""
from datetime import datetime, timezone
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user
from db import get_db
from models import serialize

router = APIRouter(prefix="/gallery")


class BuildSubmission(BaseModel):
    project_slug: Optional[str] = None
    image_url: str
    caption: Optional[str] = None
    difficulty_rating: Optional[int] = None  # 1-5
    build_time_minutes: Optional[int] = None
    notes: Optional[str] = None
    public: bool = True


@router.post("")
async def submit_build(payload: BuildSubmission, user: dict = Depends(get_current_user)):
    """Submit a build photo + feedback after receiving a kit.

    If image_url is a placeholder, creates a dock entry without an image
    (the user can add one later via the account page).
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user["id"],
        "user_name": user.get("name", "Maker"),
        "project_slug": payload.project_slug or "",
        "image_url": payload.image_url,
        "caption": payload.caption or "",
        "difficulty_rating": payload.difficulty_rating,
        "build_time_minutes": payload.build_time_minutes,
        "notes": payload.notes or "",
        "public": payload.public,
        "approved": False,  # requires moderation before appearing in public gallery
        "created_at": now,
        "updated_at": now,
    }
    res = await db.build_gallery.insert_one(doc)
    return {"id": str(res.inserted_id), "ok": True}


@router.get("")
async def list_gallery(
    slug: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    include_unapproved: bool = False,
):
    """Public gallery — approved build submissions.

    When slug is provided, filters to that project.
    When include_unapproved is true (dev only), returns all submissions.
    """
    db = get_db()
    query = {"approved": True}
    if slug:
        query["project_slug"] = slug
    if include_unapproved:
        query.pop("approved", None)

    items = []
    async for doc in db.build_gallery.find(query).sort("created_at", -1).limit(limit):
        items.append(serialize(doc))
    return items


class ApproveBuildRequest(BaseModel):
    submission_id: str


@router.post("/approve")
async def approve_build(payload: ApproveBuildRequest, user: dict = Depends(get_current_user)):
    """Approve a build submission for the public gallery (dev only)."""
    if user.get("role") != "dev":
        raise HTTPException(status_code=403, detail="Dev role required")
    db = get_db()
    if not ObjectId.is_valid(payload.submission_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db.build_gallery.update_one(
        {"_id": ObjectId(payload.submission_id)},
        {"$set": {"approved": True, "approved_at": datetime.now(timezone.utc)}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "id": payload.submission_id}


# ============================================================
# Churn survey
# ============================================================
class ChurnSurvey(BaseModel):
    reason: str  # too_expensive | missing_features | quality | no_time | other
    detail: Optional[str] = None


@router.post("/churn-survey", include_in_schema=False)
async def submit_churn_survey(payload: ChurnSurvey, user: dict = Depends(get_current_user)):
    """Record why a user cancelled/paused. Called from the subscription portal."""
    db = get_db()
    await db.churn_surveys.insert_one({
        "user_id": user["id"],
        "user_email": user.get("email", ""),
        "reason": payload.reason,
        "detail": payload.detail or "",
        "created_at": datetime.now(timezone.utc),
    })
    return {"ok": True}