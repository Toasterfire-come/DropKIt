"""Auth + UI-mode + AppSettings routes."""
from datetime import datetime, timezone
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from auth import (
    attach_session_cookies, check_lockout, clear_login_attempts,
    clear_session_cookies, create_access_token, get_current_dev,
    get_current_user, hash_password, record_failed_login, verify_password,
)
from config import settings
from db import get_db
from shopify_client import shopify

router = APIRouter()


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    role: str
    subscriptionStatus: Optional[str] = None
    shopifyCustomerId: Optional[str] = None


def _user_out(user: dict) -> UserOut:
    return UserOut(
        id=user["id"] if "id" in user else str(user["_id"]),
        email=user["email"],
        name=user.get("name"),
        role=user.get("role", "user"),
        subscriptionStatus=user.get("subscriptionStatus"),
        shopifyCustomerId=user.get("shopifyCustomerId"),
    )


@router.post("/auth/register", response_model=UserOut)
async def register(payload: RegisterIn, response: Response):
    db = get_db()
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already registered")

    now = datetime.now(timezone.utc)
    user_doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": payload.name or email.split("@")[0],
        "role": "user",
        "subscriptionStatus": "inactive",
        "voteEligibleCycles": [],
        "created_at": now,
        "updated_at": now,
    }

    # Real Shopify Admin API customer creation — production-ready, no-op when placeholder.
    # We only set shopifyCustomerId on the doc when a real id comes back; this keeps the
    # unique index clean (no null-collision under partialFilterExpression).
    if not settings.SHOPIFY_ADMIN_ACCESS_TOKEN.startswith("PLACEHOLDER"):
        try:
            data = await shopify.create_customer(email=email, name=payload.name)
            cust = data.get("customerCreate", {}).get("customer", {})
            if cust.get("id"):
                user_doc["shopifyCustomerId"] = cust["id"]
        except Exception:
            pass  # don't block signup if Shopify is down — sync later via webhook

    res = await db.users.insert_one(user_doc)
    user_doc["id"] = str(res.inserted_id)

    attach_session_cookies(response, user_doc["id"], email, "user")
    return _user_out(user_doc)


@router.post("/auth/login", response_model=UserOut)
async def login(payload: LoginIn, request: Request, response: Response):
    db = get_db()
    email = payload.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"

    await check_lockout(identifier)
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        await record_failed_login(identifier)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await clear_login_attempts(identifier)
    user["id"] = str(user["_id"])
    attach_session_cookies(response, user["id"], email, user.get("role", "user"))
    return _user_out(user)


@router.post("/auth/logout")
async def logout(response: Response):
    clear_session_cookies(response)
    return {"ok": True}


@router.get("/auth/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return _user_out(user)


@router.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    rtoken = request.cookies.get("refresh_token")
    if not rtoken:
        raise HTTPException(status_code=401, detail="No refresh token")
    from auth import decode_token
    payload = decode_token(rtoken)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    db = get_db()
    try:
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user")
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access = create_access_token(str(user["_id"]), user["email"], user.get("role", "user"))
    secure = not settings.APP_URL.startswith("http://")
    response.set_cookie(
        "access_token", access,
        httponly=True, secure=secure, samesite="lax",
        max_age=12 * 60 * 60, path="/",
    )
    return {"ok": True}


# ============================================================
# UI mode — stored in app_settings collection (singleton doc)
# ============================================================
SETTINGS_KEY = "ui_mode"


class UIModeOut(BaseModel):
    mode: Literal["waitlist", "live"]


class UIModeUpdate(BaseModel):
    mode: Literal["waitlist", "live"]


async def _get_ui_mode_value() -> str:
    db = get_db()
    doc = await db.app_settings.find_one({"key": SETTINGS_KEY})
    if doc and doc.get("value"):
        return doc["value"]
    return settings.LAUNCH_MODE or "waitlist"


@router.get("/ui-mode", response_model=UIModeOut)
async def get_ui_mode():
    return UIModeOut(mode=await _get_ui_mode_value())


@router.post("/ui-mode", response_model=UIModeOut)
async def set_ui_mode(payload: UIModeUpdate, _: dict = Depends(get_current_dev)):
    db = get_db()
    now = datetime.now(timezone.utc)
    await db.app_settings.update_one(
        {"key": SETTINGS_KEY},
        {"$set": {"key": SETTINGS_KEY, "value": payload.mode, "updated_at": now}},
        upsert=True,
    )
    return UIModeOut(mode=payload.mode)


# ============================================================
# Dev panel — quick stats
# ============================================================
@router.get("/dev/stats")
async def dev_stats(_: dict = Depends(get_current_dev)):
    db = get_db()
    # Lightweight projection (current active subs + projected next month)
    from routes_inventory import _subscriber_projection
    projection = await _subscriber_projection()
    return {
        "users": await db.users.count_documents({}),
        "waitlist": await db.waitlist.count_documents({}),
        "projects": await db.projects.count_documents({}),
        "active_project": await db.projects.count_documents({"isActive": True}),
        "gifts": await db.gifts.count_documents({}),
        "gifts_redeemed": await db.gifts.count_documents({"status": "redeemed"}),
        "substitutions": await db.substitutions.count_documents({}),
        "vote_cycles": await db.vote_cycles.count_documents({}),
        "ui_mode": await _get_ui_mode_value(),
        "active_subscribers": projection["current"],
        "avg_monthly_growth": projection["avg_monthly_growth"],
        "projected_next_month": projection["projected_next_month"],
    }
