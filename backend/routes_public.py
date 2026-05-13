"""Public + subscriber routes for DropKit."""
import secrets
import string
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from db import get_db
from models import (
    ProjectOut, VoteSubmit,
    SubstitutionCreate, GiftRedeem, WaitlistJoin,
    SubscriptionStatusOut, SubscriptionAction, serialize,
)
from shopify_client import shopify
from auth import get_current_user
from config import settings
import email_service as mailer

router = APIRouter()


# ============================================================
# Public — Waitlist (+ referral)
# ============================================================
def _gen_ref_code(n: int = 7) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L
    return "".join(secrets.choice(alphabet) for _ in range(n))


async def _unique_ref_code(db) -> str:
    for _ in range(8):
        code = _gen_ref_code()
        if not await db.waitlist.find_one({"referralCode": code}):
            return code
    # extreme edge — extend length
    return _gen_ref_code(10)


@router.post("/waitlist")
async def join_waitlist(payload: WaitlistJoin):
    db = get_db()
    now = datetime.now(timezone.utc)

    # Validate referrer (must exist) and prevent self-loop
    referrer_code = None
    if payload.ref:
        rcode = payload.ref.strip().upper()
        ref_doc = await db.waitlist.find_one({"referralCode": rcode})
        if ref_doc and ref_doc.get("email") != payload.email:
            referrer_code = rcode

    existing = await db.waitlist.find_one({"email": payload.email})
    code = existing.get("referralCode") if existing and existing.get("referralCode") else await _unique_ref_code(db)

    set_fields = {
        "name": payload.name.strip(),
        "referralCode": code,
    }
    insert_fields = {
        "email": payload.email,
        "source": payload.source,
        "createdAt": now,
    }
    # Only attach referredByCode on initial insert (don't change history on re-submit)
    if not existing and referrer_code:
        insert_fields["referredByCode"] = referrer_code
        if payload.ref_src:
            insert_fields["referredVia"] = payload.ref_src.lower()

    try:
        await db.waitlist.update_one(
            {"email": payload.email},
            {"$setOnInsert": insert_fields, "$set": set_fields},
            upsert=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Fire-and-forget Gmail email (rendered from /app/backend/email_templates/)
    if not existing:
        first_name = payload.name.strip().split(" ", 1)[0]
        custom_props = {
            "referral_code": code,
            "source": payload.source or "unknown",
        }
        if referrer_code:
            custom_props["referred_by_code"] = referrer_code
        if payload.ref_src:
            custom_props["referred_via"] = payload.ref_src.lower()

        mailer.fire(mailer.waitlist_joined(
            email=payload.email,
            first_name=first_name,
            referral_code=code,
            referred_by_code=referrer_code,
            referred_via=payload.ref_src.lower() if payload.ref_src else None,
            source=payload.source or "unknown",
        ))
        mailer.fire(mailer.subscribe_to_waitlist(
            email=payload.email,
            first_name=first_name,
            custom_props=custom_props,
        ))

        # If this signup was referred, notify the referrer + check priority unlock
        if referrer_code:
            ref_doc = await db.waitlist.find_one({"referralCode": referrer_code})
            if ref_doc:
                wl_refs = await db.waitlist.count_documents({"referredByCode": referrer_code})
                mailer.fire(mailer.referrer_notify_new_signup(
                    referrer_email=ref_doc["email"],
                    referrer_name=ref_doc.get("name", ""),
                    referee_first_name=first_name,
                    waitlist_referrals=wl_refs,
                    referral_code=referrer_code,
                ))
                # Priority unlock — fire once when crossing 3
                if wl_refs == 3 and not ref_doc.get("priorityNotified"):
                    mailer.fire(mailer.priority_unlocked(
                        email=ref_doc["email"],
                        first_name=(ref_doc.get("name", "").split(" ", 1)[0] or ""),
                        referral_code=referrer_code,
                    ))
                    await db.waitlist.update_one(
                        {"_id": ref_doc["_id"]},
                        {"$set": {"priorityNotified": True, "priorityNotifiedAt": now}},
                    )

    return {
        "ok": True,
        "message": "You're on the list. We'll be in touch.",
        "referralCode": code,
    }


@router.post("/waitlist/lookup")
async def waitlist_lookup(payload: dict):
    """Look up a referral code by email — for users who already joined and
    want to find their share link without re-submitting the form.

    Returns 200 either way (privacy: don't leak which emails exist), but only
    includes `referralCode` when a match is found. The frontend treats a
    missing code as "not on the list yet — go sign up".
    """
    email = (payload or {}).get("email", "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="email required")
    db = get_db()
    doc = await db.waitlist.find_one({"email": email})
    if not doc or not doc.get("referralCode"):
        return {"ok": True, "found": False}
    return {"ok": True, "found": True, "referralCode": doc["referralCode"]}


@router.get("/waitlist/{code}/status")
async def waitlist_status(code: str):
    db = get_db()
    code = code.strip().upper()
    doc = await db.waitlist.find_one({"referralCode": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Referral code not found")

    waitlist_refs = await db.waitlist.count_documents({"referredByCode": code})
    paid_refs = doc.get("paidReferralCount", 0)

    self_active = False
    if doc.get("email"):
        u = await db.users.find_one({"email": doc["email"]})
        self_active = bool(u and u.get("subscriptionStatus") == "active")

    return {
        "code": code,
        "email": doc["email"],
        "name": doc.get("name", ""),
        "waitlistReferrals": waitlist_refs,
        "paidReferrals": paid_refs,
        "priority": waitlist_refs >= 3,
        "freeMonthEarned": paid_refs >= 5 and self_active,
        "selfActive": self_active,
        "createdAt": doc.get("createdAt"),
    }


@router.get("/leaderboard")
async def leaderboard(limit: int = Query(default=20, ge=1, le=100)):
    """Public leaderboard — top referrers by waitlist referrals.

    Returns minimal info: first name + initial, referral counts. No emails or codes.
    """
    db = get_db()
    # Aggregate waitlist signups grouped by referredByCode → count
    pipeline = [
        {"$match": {"referredByCode": {"$type": "string"}}},
        {"$group": {"_id": "$referredByCode", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    rows = []
    async for r in db.waitlist.aggregate(pipeline):
        code = r["_id"]
        ref_doc = await db.waitlist.find_one({"referralCode": code})
        if not ref_doc:
            continue
        full_name = (ref_doc.get("name") or "").strip()
        parts = full_name.split()
        display = full_name
        if len(parts) >= 2:
            display = f"{parts[0]} {parts[1][0].upper()}."
        rows.append({
            "name": display or "A Maker",
            "waitlistReferrals": r["count"],
            "paidReferrals": ref_doc.get("paidReferralCount", 0),
        })
    return {"rows": rows}


@router.get("/launch-mode")
async def launch_mode():
    from shopify_client import shopify_is_configured
    return {
        "mode": settings.LAUNCH_MODE,
        "shopify_auth_enabled": all([
            settings.SHOPIFY_CUSTOMER_OAUTH_CLIENT_ID,
            settings.SHOPIFY_CUSTOMER_OAUTH_CLIENT_SECRET,
            settings.SHOPIFY_CUSTOMER_OAUTH_REDIRECT_URI,
            settings.SHOPIFY_CUSTOMER_SHOP_ID,
        ]),
        "shopify_checkout_enabled": shopify_is_configured() and bool(getattr(settings, "SHOPIFY_SUBSCRIPTION_VARIANT_ID", "")),
    }


# ============================================================
# Public — Projects
# ============================================================
@router.get("/projects", response_model=List[ProjectOut])
async def list_projects(
    current: Optional[bool] = Query(default=None),
    past: Optional[int] = Query(default=None, ge=1, le=24),
):
    db = get_db()
    query = {}
    if current is True:
        query["isActive"] = True

    cursor = db.projects.find(query).sort([("cycleYear", -1), ("cycleMonth", -1)])
    if past:
        cursor = cursor.limit(past)
    items = []
    async for doc in cursor:
        if current and not doc.get("isActive"):
            continue
        items.append(serialize(doc))
    return items


@router.get("/projects/current")
async def get_current_project():
    db = get_db()
    doc = await db.projects.find_one({"isActive": True})
    return serialize(doc) if doc else None


@router.get("/projects/past")
async def get_past_projects(limit: int = Query(default=6, ge=1, le=24)):
    db = get_db()
    cursor = db.projects.find({"isActive": False}).sort(
        [("cycleYear", -1), ("cycleMonth", -1)]
    ).limit(limit)
    return [serialize(d) async for d in cursor]


@router.get("/projects/{slug}")
async def get_project(slug: str):
    db = get_db()
    doc = await db.projects.find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    return serialize(doc)


# ============================================================
# Public — Vote (read-only) + Subscriber vote (auth required)
# ============================================================
@router.get("/votes/current")
async def get_current_vote_cycle():
    db = get_db()
    now = datetime.now(timezone.utc)
    cycle = await db.vote_cycles.find_one({
        "votingOpenAt": {"$lte": now},
        "votingCloseAt": {"$gte": now},
    })
    if not cycle:
        # Return the next upcoming cycle if any
        cycle = await db.vote_cycles.find_one(
            {"votingOpenAt": {"$gt": now}},
            sort=[("votingOpenAt", 1)],
        )
        if not cycle:
            return None

    out = serialize(cycle)
    # Hydrate candidates
    cand_ids = [ObjectId(cid) for cid in cycle.get("candidateProjectIds", []) if ObjectId.is_valid(cid)]
    candidates = []
    async for p in db.projects.find({"_id": {"$in": cand_ids}}):
        candidates.append(serialize(p))
    out["candidates"] = candidates

    # Aggregate vote tallies
    pipeline = [
        {"$match": {"voteCycleId": cycle["_id"]}},
        {"$group": {"_id": "$candidateProjectId", "count": {"$sum": 1}}},
    ]
    results = {}
    total = 0
    async for r in db.votes.aggregate(pipeline):
        results[str(r["_id"])] = r["count"]
        total += r["count"]
    out["results"] = results
    out["totalVotes"] = total
    return out


@router.post("/votes")
async def submit_vote(payload: VoteSubmit, user: dict = Depends(get_current_user)):
    db = get_db()
    if user.get("subscriptionStatus") != "active":
        raise HTTPException(status_code=403, detail="Subscription must be active to vote")

    now = datetime.now(timezone.utc)
    cycle = await db.vote_cycles.find_one({
        "votingOpenAt": {"$lte": now},
        "votingCloseAt": {"$gte": now},
    })
    if not cycle:
        raise HTTPException(status_code=400, detail="No active vote cycle")

    cycle_key = f"{cycle['cycleYear']}-{cycle['cycleMonth']:02d}"
    if cycle_key not in user.get("voteEligibleCycles", []):
        raise HTTPException(status_code=403, detail="Not eligible to vote this cycle")

    if not ObjectId.is_valid(payload.candidateProjectId):
        raise HTTPException(status_code=400, detail="Invalid candidate id")
    if ObjectId(payload.candidateProjectId) not in cycle.get("candidateProjectIds", []):
        # candidateProjectIds may be stored as strings
        if payload.candidateProjectId not in [str(c) for c in cycle.get("candidateProjectIds", [])]:
            raise HTTPException(status_code=400, detail="Candidate not in this cycle")

    try:
        await db.votes.insert_one({
            "userId": ObjectId(user["id"]),
            "candidateProjectId": ObjectId(payload.candidateProjectId),
            "voteCycleId": cycle["_id"],
            "createdAt": now,
        })
    except Exception:
        raise HTTPException(status_code=409, detail="You already voted in this cycle")

    return {"ok": True}


# ============================================================
# Subscriber — Substitutions
# ============================================================
@router.get("/substitutions/options")
async def substitution_options(user: dict = Depends(get_current_user)):
    """Subscription substitution catalog.

    Rotation rules:
    - Past projects with `stockCount > 0` stay in rotation regardless of age.
    - Past projects with `stockCount == 0` are hidden, UNLESS the project is
      currently in its 6th month since it was active (last chance visibility).
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    cur_idx = now.year * 12 + (now.month - 1)

    out = []
    cursor = db.projects.find({"isActive": False}).sort(
        [("cycleYear", -1), ("cycleMonth", -1)]
    )
    async for p in cursor:
        proj_idx = int(p.get("cycleYear", 0)) * 12 + (int(p.get("cycleMonth", 1)) - 1)
        age_months = max(0, cur_idx - proj_idx)
        in_stock = (p.get("stockCount") or 0) > 0
        is_sixth_month = age_months == 6
        if in_stock or is_sixth_month:
            out.append({**serialize(p), "ageMonths": age_months, "sixthMonth": is_sixth_month})
    return out


@router.post("/substitutions")
async def create_substitution(
    payload: SubstitutionCreate, user: dict = Depends(get_current_user)
):
    db = get_db()
    if user.get("subscriptionStatus") != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")

    now = datetime.now(timezone.utc)
    if now.day > 10:
        raise HTTPException(status_code=400, detail="Substitution window closed (10th of month)")

    if not ObjectId.is_valid(payload.substitutedProjectId):
        raise HTTPException(status_code=400, detail="Invalid project id")

    # Atomically decrement stock if available
    target = await db.projects.find_one_and_update(
        {"_id": ObjectId(payload.substitutedProjectId), "stockCount": {"$gt": 0}, "isActive": False},
        {"$inc": {"stockCount": -1}},
    )
    if not target:
        raise HTTPException(status_code=409, detail="Out of stock")

    existing = await db.substitutions.find_one({
        "userId": ObjectId(user["id"]),
        "cycleMonth": now.month,
        "cycleYear": now.year,
    })
    if existing:
        # rollback stock
        await db.projects.update_one(
            {"_id": ObjectId(payload.substitutedProjectId)}, {"$inc": {"stockCount": 1}}
        )
        raise HTTPException(status_code=409, detail="Already substituted this cycle")

    doc = {
        "userId": ObjectId(user["id"]),
        "originalProjectId": ObjectId(payload.originalProjectId) if ObjectId.is_valid(payload.originalProjectId) else payload.originalProjectId,
        "substitutedProjectId": ObjectId(payload.substitutedProjectId),
        "cycleMonth": now.month,
        "cycleYear": now.year,
        "status": "pending",
        "requestedAt": now,
        "fulfilledAt": None,
    }
    res = await db.substitutions.insert_one(doc)

    # Klaviyo: confirm substitution
    original = await db.projects.find_one({"_id": doc["originalProjectId"]}) if isinstance(doc["originalProjectId"], ObjectId) else None
    mailer.fire(mailer.substitution_confirmed(
        email=user.get("email") or "",
        first_name=(user.get("name", "").split(" ", 1)[0] if user.get("name") else ""),
        original_title=(original or {}).get("title", "this month's kit"),
        substituted_title=target.get("title", "your selection"),
        cycle_label=f"{now.year}-{now.month:02d}",
    ))

    return {"ok": True, "id": str(res.inserted_id)}


# ============================================================
# Subscriber — Subscription self-service (pause/skip/resume)
# ============================================================
@router.get("/account/subscription", response_model=SubscriptionStatusOut)
async def get_subscription_status(user: dict = Depends(get_current_user)):
    next_billing = None
    contract_id = user.get("shopifySubscriptionContractId")
    if contract_id and not settings.SHOPIFY_ADMIN_ACCESS_TOKEN.startswith("PLACEHOLDER"):
        try:
            data = await shopify.get_subscription_contract(contract_id)
            nb = data.get("subscriptionContract", {}).get("nextBillingDate")
            if nb:
                next_billing = datetime.fromisoformat(nb.replace("Z", "+00:00"))
        except Exception:
            pass

    return SubscriptionStatusOut(
        status=user.get("subscriptionStatus", "inactive"),
        nextBillingDate=next_billing,
        contractId=contract_id,
        voteEligibleCycles=user.get("voteEligibleCycles", []),
        canVote=user.get("subscriptionStatus") == "active",
    )


@router.post("/account/subscription")
async def manage_subscription(
    payload: SubscriptionAction, user: dict = Depends(get_current_user)
):
    if not user.get("shopifySubscriptionContractId"):
        raise HTTPException(status_code=404, detail="No subscription contract")

    cid = user["shopifySubscriptionContractId"]

    # Real Shopify Admin API mutation calls
    if payload.action == "pause":
        await shopify.pause_subscription(cid)
        # status sync happens via subscription_contracts/update webhook
    elif payload.action == "resume":
        await shopify.resume_subscription(cid)
    elif payload.action == "skip":
        # Next cycle index resolution would query Shopify in production; using 1 as placeholder
        await shopify.skip_next_billing_cycle(cid, cycle_index=1)

    return {"ok": True, "action": payload.action}


# ============================================================
# Public — Gift redemption
# ============================================================
@router.post("/gifts/redeem")
async def redeem_gift(payload: GiftRedeem):
    db = get_db()
    gift = await db.gifts.find_one({"code": payload.code.upper().strip()})
    if not gift:
        raise HTTPException(status_code=404, detail="Invalid gift code")
    if gift.get("status") == "redeemed":
        raise HTTPException(status_code=409, detail="Gift already redeemed")

    update = {
        "status": "redeemed",
        "redeemedAt": datetime.now(timezone.utc),
    }
    if payload.shippingAddressShopifyCustomerId:
        update["recipientShopifyCustomerId"] = payload.shippingAddressShopifyCustomerId

    # Create deferred Shopify subscription contract for recipient (real Admin API call)
    if (
        payload.shippingAddressShopifyCustomerId
        and not settings.SHOPIFY_ADMIN_ACCESS_TOKEN.startswith("PLACEHOLDER")
    ):
        try:
            await shopify.create_subscription_contract_for_gift(
                customer_id=payload.shippingAddressShopifyCustomerId,
                recipient_email=gift["recipientEmail"],
                duration_months=gift["durationMonths"],
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Shopify contract create failed: {e}")

    await db.gifts.update_one({"_id": gift["_id"]}, {"$set": update})

    # Klaviyo: notify both recipient and buyer
    buyer_email = gift.get("buyerEmail")
    if buyer_email:
        mailer.fire(mailer.gift_redeemed(
            buyer_email=buyer_email,
            recipient_email=gift["recipientEmail"],
            code=gift["code"],
            duration_months=gift["durationMonths"],
        ))

    return {
        "ok": True,
        "durationMonths": gift["durationMonths"],
        "recipientEmail": gift["recipientEmail"],
    }


# ============================================================
# Public — Replacement request (damaged / missing component)
# ============================================================
class ReplacementRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    order_label: Optional[str] = Field(default=None, max_length=80)
    component_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    photo_url: Optional[str] = None


@router.post("/replacements")
async def create_replacement(payload: ReplacementRequest):
    """Subscriber-facing form. Stores a request that the dev approves from /dev."""
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {**payload.model_dump(), "status": "pending", "created_at": now}
    res = await db.replacement_requests.insert_one(doc)
    return {"ok": True, "id": str(res.inserted_id)}


# ============================================================
# Public — FAQ (static content)
# ============================================================
FAQ_CONTENT = [
    {"q": "How does the subscription work?", "a": "DropKit ships you a curated electronics project kit every month for $40 + shipping. Billing is monthly, auto-renewing via Shopify Payments, and you can pause or skip at any time from your account."},
    {"q": "Where do you ship?", "a": "United States only at MVP launch. International shipping is on our post-launch roadmap."},
    {"q": "What skill level is this for?", "a": "Adult makers and intermediate hobbyists. We assume comfort with breadboards, basic wiring, and an IDE. Some projects are 'Adv. Intermediate' for a bit more challenge."},
    {"q": "What if I already have this month's project?", "a": "You can swap it for any of the past 6 months' kits (subject to stock) before the 10th of the month. One substitution per cycle."},
    {"q": "Can I pause or skip a month?", "a": "Yes. Both pause and skip are available from your account portal. Skipped cycles aren't billed and don't include voting eligibility."},
    {"q": "How does voting work?", "a": "Each month, active subscribers vote on the project two months out. Voting opens on the 1st and closes on the 7th. Results are announced on the 8th."},
    {"q": "Can I gift a subscription?", "a": "Yes — 1-month and 3-month gifts are available. The recipient gets a redemption code by email and chooses their shipping address at redemption."},
    {"q": "How do I cancel?", "a": "Cancel any time from your Shopify customer account — no questions asked, no hidden fees."},
    {"q": "What if a component is damaged or missing?", "a": "Email support and we'll ship a replacement, case-by-case. We aim to respond within 48 hours and ship within 5 business days."},
    {"q": "Is the software really open source?", "a": "Yes. All project software, schematics, and BOMs are released on GitHub under MIT or CC BY-SA. Use, fork, and contribute freely."},
]


@router.get("/faq")
async def get_faq():
    return FAQ_CONTENT


# ============================================================
# Admin (token-protected) — manage projects + vote cycles
# ============================================================
def require_admin(x_admin_token: Optional[str] = None):
    """Stub dependency; real impl in admin router."""
    return None


def _gen_gift_code() -> str:
    chunk = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    year = datetime.now(timezone.utc).year
    return f"MAKER-{chunk}-{year}"
