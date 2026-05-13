"""Local JWT auth — bcrypt password hashing + httpOnly cookie sessions.

Roles: 'user' (default), 'dev' (toggles UI mode, full admin).
"""
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from bson import ObjectId
from fastapi import HTTPException, Request

from config import settings
from db import get_db

ALG = "HS256"
ACCESS_MIN = 60 * 12  # 12 hours
REFRESH_DAYS = 7


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def _now():
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": _now() + timedelta(minutes=ACCESS_MIN),
        "iat": _now(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALG)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": _now() + timedelta(days=REFRESH_DAYS),
        "iat": _now(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALG)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(request: Request) -> dict:
    # Cookie first, then Authorization header (mobile / extension contexts)
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    db = get_db()
    try:
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user id")
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    user["id"] = str(user.pop("_id"))
    user.pop("password_hash", None)
    return user


async def get_current_dev(request: Request) -> dict:
    user = await get_current_user(request)
    if user.get("role") != "dev":
        raise HTTPException(status_code=403, detail="Dev role required")
    return user


def attach_session_cookies(response, user_id: str, email: str, role: str):
    access = create_access_token(user_id, email, role)
    refresh = create_refresh_token(user_id)
    secure = not settings.APP_URL.startswith("http://")
    response.set_cookie(
        "access_token", access,
        httponly=True, secure=secure, samesite="lax",
        max_age=ACCESS_MIN * 60, path="/",
    )
    response.set_cookie(
        "refresh_token", refresh,
        httponly=True, secure=secure, samesite="lax",
        max_age=REFRESH_DAYS * 24 * 60 * 60, path="/",
    )
    return access


def clear_session_cookies(response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


# ------------------------------ Brute force protection ------------------------------
LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15


async def check_lockout(identifier: str):
    db = get_db()
    rec = await db.login_attempts.find_one({"identifier": identifier})
    if not rec:
        return
    if rec.get("locked_until") and rec["locked_until"] > _now():
        mins = int((rec["locked_until"] - _now()).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Try again in {mins} minute(s).",
        )


async def record_failed_login(identifier: str):
    db = get_db()
    rec = await db.login_attempts.find_one({"identifier": identifier})
    count = (rec.get("count", 0) if rec else 0) + 1
    update = {"count": count, "updated_at": _now()}
    if count >= LOCKOUT_THRESHOLD:
        update["locked_until"] = _now() + timedelta(minutes=LOCKOUT_MINUTES)
        update["count"] = 0
    await db.login_attempts.update_one(
        {"identifier": identifier}, {"$set": update}, upsert=True
    )


async def clear_login_attempts(identifier: str):
    db = get_db()
    await db.login_attempts.delete_one({"identifier": identifier})


# ------------------------------ Seed dev user ------------------------------
async def seed_dev_user():
    if not settings.DEV_EMAIL or not settings.DEV_PASSWORD:
        return
    db = get_db()
    email = settings.DEV_EMAIL.lower().strip()
    existing = await db.users.find_one({"email": email})
    if not existing:
        await db.users.insert_one({
            "email": email,
            "password_hash": hash_password(settings.DEV_PASSWORD),
            "name": settings.DEV_NAME,
            "role": "dev",
            "subscriptionStatus": "inactive",
            "voteEligibleCycles": [],
            "created_at": _now(),
            "updated_at": _now(),
        })
    elif not verify_password(settings.DEV_PASSWORD, existing.get("password_hash", "")):
        await db.users.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": hash_password(settings.DEV_PASSWORD), "role": "dev"}},
        )
    elif existing.get("role") != "dev":
        await db.users.update_one({"_id": existing["_id"]}, {"$set": {"role": "dev"}})
