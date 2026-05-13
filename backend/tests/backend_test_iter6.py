"""Iteration 6 backend tests — DropKit referral lifecycle + Klaviyo no-op + admin broadcasts.

Covers:
  - POST /api/waitlist with ref + ref_src persists referredVia (initial only).
  - Waitlist always returns 200 even though Klaviyo is placeholder (no-op).
  - Referrer wlRefs increments to 1,2,3; priorityNotified stamped exactly once at 3.
  - GET /api/waitlist/{code}/status: priority>=3, freeMonthEarned needs paid>=5 AND selfActive.
  - GET /api/leaderboard redacts email/code.
  - POST /api/admin/broadcasts/launch-announcement → queued=N waitlist docs.
  - POST /api/admin/broadcasts/vote-opened → queued=active-subscriber count (cycle required).
  - POST /api/admin/broadcasts/vote-results → 400 without winnerId.
  - POST /api/substitutions creates doc and fires Klaviyo (no error).
  - POST /api/gifts/redeem fires Klaviyo gift-redeemed (no error).
  - Webhook orders/paid (subscription branch) fires subscription_welcome only on FIRST activation.
  - POST /api/auth/shopify/login → 503 under placeholder creds.
"""
import os
import sys
import secrets
import hmac
import hashlib
import base64
import json
from datetime import datetime, timezone, timedelta

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("BACKEND_TEST_URL") or os.environ.get(
    "REACT_APP_BACKEND_URL", "http://localhost:8001"
).rstrip("/")
API = f"{BASE_URL}/api"

DEV_EMAIL = "dev@dropkit.dev"
ADMIN_TOKEN = "dropkit-admin-dev-token"

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

sys.path.insert(0, "/app/backend")
from config import settings  # noqa: E402


def _rand_email(prefix="iter6"):
    return f"TEST_iter6_{prefix}_{secrets.token_hex(4)}@example.com"


# ---------- session-wide fixtures ----------
@pytest.fixture(scope="session")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    # Cleanup TEST_iter6_ leftovers
    c = client[DB_NAME]
    c.waitlist.delete_many({"email": {"$regex": "^TEST_iter6_"}})
    c.users.delete_many({"email": {"$regex": "^TEST_iter6_"}})
    c.users.delete_many({"shopifyCustomerId": {"$regex": "^gid://shopify/Customer/TESTiter6"}})
    c.projects.delete_many({"slug": {"$regex": "^TEST_iter6_"}})
    c.vote_cycles.delete_many({"_iter6": True})
    c.gifts.delete_many({"code": {"$regex": "^MAKER-ITER6"}})
    c.substitutions.delete_many({"_iter6": True})
    # Reset dev user — keep it inactive so other tests don't see it as active
    c.users.update_one({"email": DEV_EMAIL}, {"$set": {"subscriptionStatus": "inactive"}})
    client.close()


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def dev_bearer(db):
    """Bearer token for dev user (cookie has Secure flag → unusable over http://localhost)."""
    from auth import create_access_token  # type: ignore
    user = db.users.find_one({"email": DEV_EMAIL})
    assert user, f"dev user {DEV_EMAIL} not seeded"
    return create_access_token(str(user["_id"]), DEV_EMAIL, user.get("role", "dev"))


# ============================================================
# 1. Waitlist ref + ref_src persistence + no-op Klaviyo
# ============================================================
class TestWaitlistReferralTracking:
    def test_ref_src_persisted_on_initial_insert_only(self, s, db):
        # Alice joins (becomes referrer)
        alice_email = _rand_email("alice1")
        ra = s.post(f"{API}/waitlist", json={"name": "Alice Anderson", "email": alice_email})
        assert ra.status_code == 200, ra.text
        alice_code = ra.json()["referralCode"]
        assert isinstance(alice_code, str) and len(alice_code) >= 6

        # Bob joins WITH ref + ref_src=tw
        bob_email = _rand_email("bob1")
        rb = s.post(
            f"{API}/waitlist",
            json={"name": "Bob Brown", "email": bob_email, "ref": alice_code, "ref_src": "tw"},
        )
        assert rb.status_code == 200, rb.text

        bob = db.waitlist.find_one({"email": bob_email})
        assert bob is not None
        assert bob.get("referredByCode") == alice_code
        assert bob.get("referredVia") == "tw"

        # Resubmit Bob with a DIFFERENT ref_src — history must not change
        rb2 = s.post(
            f"{API}/waitlist",
            json={"name": "Bob Brown", "email": bob_email, "ref": alice_code, "ref_src": "bsky"},
        )
        assert rb2.status_code == 200
        bob2 = db.waitlist.find_one({"email": bob_email})
        assert bob2.get("referredVia") == "tw", "referredVia must not change on resubmit"
        assert bob2.get("referredByCode") == alice_code

    def test_waitlist_returns_200_even_with_placeholder_klaviyo(self, s):
        # The whole point: Klaviyo must no-op silently. POST must always succeed.
        email = _rand_email("noop")
        r = s.post(f"{API}/waitlist", json={"name": "No Op", "email": email})
        assert r.status_code == 200, r.text
        assert r.json().get("referralCode")


# ============================================================
# 2. Referrer notification + priority unlock (idempotent at #3)
# ============================================================
class TestReferrerNotificationAndPriority:
    def test_priority_unlocks_exactly_once_at_third_signup(self, s, db):
        # Alice (referrer)
        alice_email = _rand_email("alice2")
        ra = s.post(f"{API}/waitlist", json={"name": "Alice Adams", "email": alice_email})
        alice_code = ra.json()["referralCode"]

        # Pre-state: Alice has no priority flag
        alice = db.waitlist.find_one({"email": alice_email})
        assert not alice.get("priorityNotified")

        # First two referees → wlRefs=1, wlRefs=2; priorityNotified must stay false
        for i, src in enumerate(["tw", "wa"], start=1):
            email = _rand_email(f"ref{i}")
            r = s.post(
                f"{API}/waitlist",
                json={"name": f"Ref{i} User", "email": email, "ref": alice_code, "ref_src": src},
            )
            assert r.status_code == 200
            status = s.get(f"{API}/waitlist/{alice_code}/status").json()
            assert status["waitlistReferrals"] == i
            assert status["priority"] is (i >= 3)
            alice = db.waitlist.find_one({"email": alice_email})
            assert not alice.get("priorityNotified"), f"priority must not fire before 3, fired at {i}"

        # Third referee → wlRefs=3, priorityNotified=True, priorityNotifiedAt set
        third_email = _rand_email("ref3")
        r3 = s.post(
            f"{API}/waitlist",
            json={"name": "Ref3 User", "email": third_email, "ref": alice_code, "ref_src": "sms"},
        )
        assert r3.status_code == 200
        status3 = s.get(f"{API}/waitlist/{alice_code}/status").json()
        assert status3["waitlistReferrals"] == 3
        assert status3["priority"] is True
        alice = db.waitlist.find_one({"email": alice_email})
        assert alice.get("priorityNotified") is True
        assert alice.get("priorityNotifiedAt") is not None
        first_notified_at = alice["priorityNotifiedAt"]

        # Fourth referee → wlRefs=4, priorityNotified must NOT be re-stamped
        fourth_email = _rand_email("ref4")
        s.post(
            f"{API}/waitlist",
            json={"name": "Ref4 User", "email": fourth_email, "ref": alice_code, "ref_src": "email"},
        )
        alice4 = db.waitlist.find_one({"email": alice_email})
        assert alice4.get("priorityNotified") is True
        assert alice4.get("priorityNotifiedAt") == first_notified_at, \
            "priorityNotifiedAt must be set exactly once"


# ============================================================
# 3. /waitlist/{code}/status — priority + freeMonthEarned rules
# ============================================================
class TestWaitlistStatus:
    def test_freemonth_requires_paid_and_self_active(self, s, db):
        # Make a fresh referrer
        email = _rand_email("fm")
        r = s.post(f"{API}/waitlist", json={"name": "Free Month", "email": email})
        code = r.json()["referralCode"]

        # 5 paid referrals but referrer NOT self-active → freeMonthEarned False
        db.waitlist.update_one(
            {"referralCode": code}, {"$set": {"paidReferralCount": 5}}
        )
        status = s.get(f"{API}/waitlist/{code}/status").json()
        assert status["paidReferrals"] == 5
        assert status["selfActive"] is False
        assert status["freeMonthEarned"] is False

        # Now also make the user self-active in users collection
        db.users.update_one(
            {"email": email},
            {"$set": {"email": email, "subscriptionStatus": "active"}},
            upsert=True,
        )
        status2 = s.get(f"{API}/waitlist/{code}/status").json()
        assert status2["selfActive"] is True
        assert status2["freeMonthEarned"] is True

        # Drop paid to 4 → freeMonthEarned False again
        db.waitlist.update_one(
            {"referralCode": code}, {"$set": {"paidReferralCount": 4}}
        )
        status3 = s.get(f"{API}/waitlist/{code}/status").json()
        assert status3["paidReferrals"] == 4
        assert status3["freeMonthEarned"] is False


# ============================================================
# 4. /leaderboard redaction
# ============================================================
class TestLeaderboardRedacted:
    def test_no_email_no_code_leak(self, s):
        r = s.get(f"{API}/leaderboard")
        assert r.status_code == 200
        rows = r.json().get("rows", [])
        for row in rows:
            assert "email" not in row, f"email leaked: {row}"
            assert "referralCode" not in row, f"code leaked: {row}"
            assert "code" not in row
            assert "name" in row and "waitlistReferrals" in row


# ============================================================
# 5. Admin broadcasts
# ============================================================
class TestAdminBroadcasts:
    HDR = {"X-Admin-Token": ADMIN_TOKEN}

    def test_launch_announcement_queued_equals_waitlist_count(self, s, db):
        # queued must equal current waitlist doc count (with email)
        r = s.post(f"{API}/admin/broadcasts/launch-announcement", headers=self.HDR)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        wl_with_email = db.waitlist.count_documents({"email": {"$exists": True, "$ne": None}})
        assert data["queued"] == wl_with_email, f"queued={data['queued']} expected={wl_with_email}"

    def test_launch_announcement_requires_admin_token(self, s):
        r = s.post(f"{API}/admin/broadcasts/launch-announcement")
        assert r.status_code == 401

    def test_vote_opened_queued_equals_active_subs(self, s, db):
        # Seed: ensure dev user is active subscriber so queued >= 1
        db.users.update_one(
            {"email": DEV_EMAIL},
            {"$set": {"subscriptionStatus": "active", "email": DEV_EMAIL}},
            upsert=True,
        )
        # Seed projects + vote cycle
        proj_ids = []
        for i in range(2):
            pid = db.projects.insert_one({
                "title": f"TEST iter6 Project {i}",
                "slug": f"TEST_iter6_proj_{secrets.token_hex(3)}_{i}",
                "description": "tmp",
                "board": "ESP32",
                "difficulty": "INTERMEDIATE",
                "cycleMonth": 6,
                "cycleYear": 2026,
                "stockCount": 0,
                "isActive": False,
                "createdAt": datetime.now(timezone.utc),
            }).inserted_id
            proj_ids.append(pid)

        cycle_id = db.vote_cycles.insert_one({
            "cycleMonth": 6,
            "cycleYear": 2026,
            "candidateProjectIds": proj_ids,
            "votingOpenAt": datetime.now(timezone.utc) - timedelta(days=1),
            "votingCloseAt": datetime.now(timezone.utc) + timedelta(days=7),
            "winnerId": None,
            "_iter6": True,
        }).inserted_id

        active_count = db.users.count_documents({"subscriptionStatus": "active"})
        r = s.post(
            f"{API}/admin/broadcasts/vote-opened",
            headers=self.HDR,
            json={"cycleId": str(cycle_id)},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["queued"] == active_count

        # Bad cycleId → 400
        r_bad = s.post(
            f"{API}/admin/broadcasts/vote-opened",
            headers=self.HDR,
            json={"cycleId": "not-an-id"},
        )
        assert r_bad.status_code == 400

        # Missing cycle → 404
        r_miss = s.post(
            f"{API}/admin/broadcasts/vote-opened",
            headers=self.HDR,
            json={"cycleId": str(ObjectId())},
        )
        assert r_miss.status_code == 404

    def test_vote_results_requires_winner(self, s, db):
        # Cycle without winnerId → 400
        cycle_id = db.vote_cycles.insert_one({
            "cycleMonth": 7,
            "cycleYear": 2026,
            "candidateProjectIds": [],
            "votingOpenAt": datetime.now(timezone.utc),
            "votingCloseAt": datetime.now(timezone.utc) + timedelta(days=1),
            "winnerId": None,
            "_iter6": True,
        }).inserted_id
        r = s.post(
            f"{API}/admin/broadcasts/vote-results",
            headers=self.HDR,
            json={"cycleId": str(cycle_id)},
        )
        assert r.status_code == 400, r.text

        # Now set a winner + 1 project
        winner_id = db.projects.insert_one({
            "title": "TEST iter6 Winner",
            "slug": f"TEST_iter6_winner_{secrets.token_hex(3)}",
            "description": "tmp",
            "board": "ESP32",
            "difficulty": "INTERMEDIATE",
            "cycleMonth": 7,
            "cycleYear": 2026,
            "stockCount": 0,
            "isActive": False,
            "createdAt": datetime.now(timezone.utc),
        }).inserted_id
        db.vote_cycles.update_one({"_id": cycle_id}, {"$set": {"winnerId": winner_id}})
        r2 = s.post(
            f"{API}/admin/broadcasts/vote-results",
            headers=self.HDR,
            json={"cycleId": str(cycle_id)},
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["ok"] is True
        assert r2.json()["queued"] >= 0


# ============================================================
# 6. /substitutions creates doc + Klaviyo no-error
# ============================================================
class TestSubstitution:
    def test_create_substitution_no_klaviyo_error(self, s, db, dev_bearer):
        # Set dev user active
        db.users.update_one(
            {"email": DEV_EMAIL},
            {"$set": {"subscriptionStatus": "active"}},
            upsert=True,
        )
        # Seed a past in-stock project to substitute INTO
        past_id = db.projects.insert_one({
            "title": "TEST iter6 Past Kit",
            "slug": f"TEST_iter6_past_{secrets.token_hex(3)}",
            "description": "x",
            "board": "ESP32",
            "difficulty": "INTERMEDIATE",
            "cycleMonth": 1,
            "cycleYear": 2025,
            "stockCount": 5,
            "isActive": False,
            "createdAt": datetime.now(timezone.utc),
        }).inserted_id
        # Original project (current) — any valid ObjectId works
        orig_id = db.projects.insert_one({
            "title": "TEST iter6 Current",
            "slug": f"TEST_iter6_cur_{secrets.token_hex(3)}",
            "description": "x",
            "board": "ESP32",
            "difficulty": "INTERMEDIATE",
            "cycleMonth": datetime.now(timezone.utc).month,
            "cycleYear": datetime.now(timezone.utc).year,
            "stockCount": 0,
            "isActive": False,
            "createdAt": datetime.now(timezone.utc),
        }).inserted_id

        # Clean any prior substitution for dev user this cycle
        now = datetime.now(timezone.utc)
        user = db.users.find_one({"email": DEV_EMAIL})
        db.substitutions.delete_many({
            "userId": user["_id"], "cycleMonth": now.month, "cycleYear": now.year,
        })

        # Substitution window is closed after day 10 → skip in that case
        if now.day > 10:
            pytest.skip("Substitution window closed (after 10th)")

        headers = {"Authorization": f"Bearer {dev_bearer}"}
        payload = {
            "originalProjectId": str(orig_id),
            "substitutedProjectId": str(past_id),
        }
        r = s.post(f"{API}/substitutions", json=payload, headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True and body.get("id")

        # Verify persisted
        sub = db.substitutions.find_one({"_id": ObjectId(body["id"])})
        assert sub is not None
        assert sub["substitutedProjectId"] == past_id
        # Mark so cleanup picks it up
        db.substitutions.update_one({"_id": sub["_id"]}, {"$set": {"_iter6": True}})


# ============================================================
# 7. /gifts/redeem fires Klaviyo gift_redeemed (no error)
# ============================================================
class TestGiftRedeem:
    def test_redeem_pending_gift_succeeds(self, s, db):
        code = f"MAKER-ITER6{secrets.token_hex(2).upper()}-2026"
        db.gifts.insert_one({
            "code": code,
            "buyerShopifyOrderId": "TEST_ORDER_iter6",
            "buyerEmail": _rand_email("buyer"),
            "recipientEmail": _rand_email("recip"),
            "durationMonths": 1,
            "status": "pending",
            "recipientShopifyCustomerId": None,
            "redeemedAt": None,
            "createdAt": datetime.now(timezone.utc),
        })
        r = s.post(f"{API}/gifts/redeem", json={"code": code})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["durationMonths"] == 1

        # Verify status flipped
        g = db.gifts.find_one({"code": code})
        assert g["status"] == "redeemed"

    def test_invalid_code_404(self, s):
        r = s.post(f"{API}/gifts/redeem", json={"code": "MAKER-NOPE-9999"})
        assert r.status_code == 404


# ============================================================
# 8. Webhook orders/paid — subscription_welcome fires only on FIRST activation
# ============================================================
class TestSubscriptionWelcomeIdempotent:
    """We can't easily intercept Klaviyo, but the welcome branch only runs when
    existing_user.subscriptionStatus != 'active' BEFORE the upsert. We verify
    that the second webhook does NOT log/raise and the user remains active.
    """

    def _sign(self, body_bytes: bytes) -> str:
        secret = settings.SHOPIFY_WEBHOOK_SECRET or ""
        digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).digest()
        return base64.b64encode(digest).decode()

    def test_orders_paid_repeat_does_not_error(self, s, db):
        # Build a fake orders/paid payload for a brand-new TEST customer
        cust_id = f"TESTiter6{secrets.token_hex(3)}"
        customer_gid = f"gid://shopify/Customer/{cust_id}"
        buyer_email = _rand_email("subwelcome")
        order_id = secrets.token_hex(6)
        payload = {
            "id": order_id,
            "total_price": "40.00",
            "customer": {
                "id": cust_id,
                "admin_graphql_api_id": customer_gid,
                "email": buyer_email,
                "first_name": "Sub",
            },
            "line_items": [{"properties": []}],
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "X-Shopify-Topic": "orders/paid",
            "X-Shopify-Hmac-Sha256": self._sign(body_bytes),
            "Content-Type": "application/json",
        }

        # First webhook: should activate the new user
        r1 = s.post(f"{API}/webhooks/shopify", data=body_bytes, headers=headers)
        # If HMAC verification fails (e.g. webhook secret empty/placeholder), the route
        # may reject. We accept either path but assert behavior consistently.
        if r1.status_code in (401, 403):
            pytest.skip(f"Webhook HMAC not verifiable in this env (status={r1.status_code})")
        assert r1.status_code == 200, r1.text

        u1 = db.users.find_one({"shopifyCustomerId": customer_gid})
        assert u1 is not None
        assert u1.get("subscriptionStatus") == "active"

        # Second webhook (repeat order, same customer already active): must still 200
        payload["id"] = secrets.token_hex(6)
        body2 = json.dumps(payload).encode("utf-8")
        headers["X-Shopify-Hmac-Sha256"] = self._sign(body2)
        r2 = s.post(f"{API}/webhooks/shopify", data=body2, headers=headers)
        assert r2.status_code == 200, r2.text

        # User must still be active (no regression)
        u2 = db.users.find_one({"shopifyCustomerId": customer_gid})
        assert u2.get("subscriptionStatus") == "active"


# ============================================================
# 9. /auth/shopify/login returns 503 under placeholder creds
# ============================================================
class TestShopifyAuthPlaceholder:
    def test_login_503(self, s):
        r = s.get(f"{API}/auth/shopify/login", allow_redirects=False)
        assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text[:200]}"
