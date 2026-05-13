"""Shopify Customer Account OAuth — production-ready.

When `SHOPIFY_CUSTOMER_OAUTH_CLIENT_ID`/`_SECRET`/`_REDIRECT_URI`/`_SHOP_ID`
are all set, this implements the standard OAuth 2.0 Authorization Code flow
against Shopify's *new* Customer Account API:

  - GET  /api/auth/shopify/login    → 302 to Shopify auth URL with state
  - GET  /api/auth/shopify/callback → exchange code → load customer profile
                                       → upsert local User → set session cookies

When creds are placeholders, both endpoints return 503 and the existing
local JWT register/login (`routes_auth.py`) continues to work.

Reference:
  https://shopify.dev/docs/api/customer/auth/oauth
"""
from __future__ import annotations

import secrets
import urllib.parse
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from config import settings
from db import get_db
from auth import attach_session_cookies

router = APIRouter(prefix="/auth/shopify")


def _is_configured() -> bool:
    return all([
        settings.SHOPIFY_CUSTOMER_OAUTH_CLIENT_ID,
        settings.SHOPIFY_CUSTOMER_OAUTH_CLIENT_SECRET,
        settings.SHOPIFY_CUSTOMER_OAUTH_REDIRECT_URI,
        settings.SHOPIFY_CUSTOMER_SHOP_ID,
    ])


def _auth_base() -> str:
    # Shopify-hosted authorize endpoint for the new Customer Account API
    return f"https://shopify.com/{settings.SHOPIFY_CUSTOMER_SHOP_ID}/auth"


@router.get("/login")
async def shopify_login(request: Request):
    if not _is_configured():
        raise HTTPException(status_code=503, detail="Shopify customer login not configured")

    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    # Persist the state/nonce so we can validate the callback
    db = get_db()
    await db.shopify_oauth_states.insert_one({
        "state": state,
        "nonce": nonce,
        "created_at": datetime.now(timezone.utc),
    })

    params = {
        "client_id": settings.SHOPIFY_CUSTOMER_OAUTH_CLIENT_ID,
        "redirect_uri": settings.SHOPIFY_CUSTOMER_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email customer-account-api:full",
        "state": state,
        "nonce": nonce,
    }
    url = f"{_auth_base()}/oauth/authorize?{urllib.parse.urlencode(params)}"
    return {"redirect_url": url}


@router.get("/callback")
async def shopify_callback(code: str, state: str, response: Response):
    if not _is_configured():
        raise HTTPException(status_code=503, detail="Shopify customer login not configured")

    db = get_db()
    state_doc = await db.shopify_oauth_states.find_one({"state": state})
    if not state_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    await db.shopify_oauth_states.delete_one({"_id": state_doc["_id"]})

    # 1. Exchange code for access token
    token_url = f"{_auth_base()}/oauth/token"
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_r = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.SHOPIFY_CUSTOMER_OAUTH_CLIENT_ID,
                "client_secret": settings.SHOPIFY_CUSTOMER_OAUTH_CLIENT_SECRET,
                "redirect_uri": settings.SHOPIFY_CUSTOMER_OAUTH_REDIRECT_URI,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_r.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_r.text[:300]}")
        tokens = token_r.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access_token in response")

        # 2. Load customer profile via Customer Account API
        gql_url = f"https://shopify.com/{settings.SHOPIFY_CUSTOMER_SHOP_ID}/account/customer/api/2025-01/graphql"
        gql = "query { customer { id emailAddress { emailAddress } firstName lastName } }"
        prof_r = await client.post(
            gql_url,
            json={"query": gql},
            headers={"Authorization": access_token, "Content-Type": "application/json"},
        )
        if prof_r.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Profile fetch failed: {prof_r.text[:300]}")
        prof = prof_r.json().get("data", {}).get("customer") or {}

    cust_gid = prof.get("id")
    email = (prof.get("emailAddress") or {}).get("emailAddress")
    first = prof.get("firstName") or ""
    last = prof.get("lastName") or ""
    full_name = (first + " " + last).strip() or (email.split("@")[0] if email else "Maker")

    if not email or not cust_gid:
        raise HTTPException(status_code=400, detail="Shopify did not return customer email/id")

    now = datetime.now(timezone.utc)
    # Upsert local user — mirror Shopify customer + keep local fields for role/subscriptionStatus
    user = await db.users.find_one_and_update(
        {"email": email.lower().strip()},
        {
            "$setOnInsert": {
                "email": email.lower().strip(),
                "role": "user",
                "subscriptionStatus": "inactive",
                "voteEligibleCycles": [],
                "created_at": now,
            },
            "$set": {
                "shopifyCustomerId": cust_gid,
                "name": full_name,
                "shopify_access_token": access_token,
                "shopify_refresh_token": tokens.get("refresh_token"),
                "updated_at": now,
            },
        },
        upsert=True,
        return_document=True,
    )

    attach_session_cookies(response, str(user["_id"]), user["email"], user.get("role", "user"))
    return {"ok": True, "email": user["email"], "name": user.get("name")}
