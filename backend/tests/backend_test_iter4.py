"""Iteration 4 backend tests — Waitlist + Referral program + Shopify auth + Substitutions rotation + dev/stats."""
import os
import secrets
import pytest
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_URL = os.environ.get("BACKEND_TEST_URL") or os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

DEV_EMAIL = "dev@dropkit.dev"
DEV_PASS = "dropkit-dev-2026"
ADMIN_TOKEN = "dropkit-admin-dev-token"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "dropkit")


def _rand_email(prefix="iter4"):
    return f"TEST_{prefix}_{secrets.token_hex(4)}@example.com"


@pytest.fixture(scope="session")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    # cleanup test rows
    client[DB_NAME].waitlist.delete_many({"email": {"$regex": "^TEST_iter4_"}})
    client[DB_NAME].users.delete_many({"email": {"$regex": "^TEST_iter4_"}})
    client[DB_NAME].projects.delete_many({"slug": {"$regex": "^TEST_iter4_"}})
    client.close()


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def dev_session(db):
    """Build an authenticated session via Bearer token (cookie has Secure flag → unusable on http://localhost)."""
    import sys
    sys.path.insert(0, "/app/backend")
    from auth import create_access_token  # type: ignore
    user = db.users.find_one({"email": DEV_EMAIL})
    assert user, f"dev user {DEV_EMAIL} not seeded"
    token = create_access_token(str(user["_id"]), DEV_EMAIL, user.get("role", "dev"))
    sess = requests.Session()
    sess.headers.update({"Authorization": f"Bearer {token}"})
    return sess


# ============================================================
# 1. POST /api/waitlist — basic + idempotency + name required
# ============================================================
class TestWaitlist:
    def test_join_returns_referral_code(self, s):
        email = _rand_email("join1")
        r = s.post(f"{API}/waitlist", json={"name": "Alice Anderson", "email": email})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert isinstance(data.get("referralCode"), str) and len(data["referralCode"]) >= 6
        assert isinstance(data.get("message"), str)

    def test_join_without_name_returns_422(self, s):
        email = _rand_email("noname")
        r = s.post(f"{API}/waitlist", json={"email": email})
        assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"

    def test_join_with_empty_name_returns_422(self, s):
        email = _rand_email("empty")
        r = s.post(f"{API}/waitlist", json={"name": "", "email": email})
        assert r.status_code == 422

    def test_join_idempotent_same_code(self, s):
        email = _rand_email("idem")
        r1 = s.post(f"{API}/waitlist", json={"name": "Bob Brown", "email": email})
        r2 = s.post(f"{API}/waitlist", json={"name": "Bob Brown", "email": email})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["referralCode"] == r2.json()["referralCode"]


# ============================================================
# 2. Referral mechanics — self-ref blocked, status counts
# ============================================================
class TestReferral:
    def test_self_referral_not_credited(self, s):
        email = _rand_email("self")
        r1 = s.post(f"{API}/waitlist", json={"name": "Cara Cole", "email": email})
        code = r1.json()["referralCode"]
        # Same person tries to "ref themselves" -- joins again with own code
        r2 = s.post(f"{API}/waitlist", json={"name": "Cara Cole", "email": email, "ref": code})
        assert r2.status_code == 200
        st = s.get(f"{API}/waitlist/{code}/status").json()
        assert st["waitlistReferrals"] == 0, f"self-ref should not credit; got {st}"

    def test_referral_credit_and_priority(self, s, db):
        # referrer joins
        ref_email = _rand_email("ref")
        ref_resp = s.post(f"{API}/waitlist", json={"name": "Dana Doe", "email": ref_email}).json()
        code = ref_resp["referralCode"]
        # 3 distinct referees join with this code
        for i in range(3):
            s.post(f"{API}/waitlist", json={"name": f"Friend{i} Fox", "email": _rand_email(f"friend{i}"), "ref": code})
        st = s.get(f"{API}/waitlist/{code}/status").json()
        assert st["waitlistReferrals"] >= 3
        assert st["priority"] is True
        assert st["paidReferrals"] == 0
        assert st["freeMonthEarned"] is False
        assert st["selfActive"] is False

    def test_status_bogus_code_404(self, s):
        r = s.get(f"{API}/waitlist/NOPESUCHC/status")
        assert r.status_code == 404

    def test_free_month_requires_paid_and_self_active(self, s, db):
        # Set up referrer with 5 paid referrals manually + self active
        ref_email = _rand_email("paid")
        rc = s.post(f"{API}/waitlist", json={"name": "Eli Edwards", "email": ref_email}).json()["referralCode"]
        # paidReferralCount = 5 BUT selfActive=False
        db.waitlist.update_one({"referralCode": rc}, {"$set": {"paidReferralCount": 5}})
        st = s.get(f"{API}/waitlist/{rc}/status").json()
        assert st["paidReferrals"] == 5
        assert st["freeMonthEarned"] is False, "selfActive=False should block reward"

        # Now make the referrer themselves an active subscriber
        db.users.update_one(
            {"email": ref_email},
            {"$set": {"email": ref_email, "subscriptionStatus": "active"}},
            upsert=True,
        )
        st2 = s.get(f"{API}/waitlist/{rc}/status").json()
        assert st2["selfActive"] is True
        assert st2["freeMonthEarned"] is True


# ============================================================
# 3. GET /api/leaderboard — privacy redaction
# ============================================================
class TestLeaderboard:
    def test_leaderboard_redacts_names_no_email_no_code(self, s):
        # ensure at least one referrer with referrals exists
        ref_email = _rand_email("lb")
        code = s.post(f"{API}/waitlist", json={"name": "Lana Lee", "email": ref_email}).json()["referralCode"]
        s.post(f"{API}/waitlist", json={"name": "Mark Miller", "email": _rand_email("lb_f"), "ref": code})
        r = s.get(f"{API}/leaderboard")
        assert r.status_code == 200
        body = r.json()
        assert "rows" in body
        for row in body["rows"]:
            assert "email" not in row
            assert "code" not in row and "referralCode" not in row
            assert "name" in row
            # Two-word names should be redacted as "First L."
            assert "@" not in row["name"]


# ============================================================
# 4. /api/launch-mode — both shopify flags false with placeholders
# ============================================================
class TestLaunchMode:
    def test_launch_mode_flags_false(self, s):
        r = s.get(f"{API}/launch-mode")
        assert r.status_code == 200
        data = r.json()
        assert "mode" in data
        assert data["shopify_auth_enabled"] is False
        assert data["shopify_checkout_enabled"] is False


# ============================================================
# 5. Shopify customer OAuth — 503 when not configured
# ============================================================
class TestShopifyAuth:
    def test_shopify_login_503(self, s):
        r = s.get(f"{API}/auth/shopify/login", allow_redirects=False)
        assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text}"


# ============================================================
# 6. Substitutions rotation rule (auth required)
# ============================================================
class TestSubstitutions:
    def test_rotation_rule(self, db, dev_session):
        # Seed three past projects:
        #  - A: in-stock, 12 months old      → SHOULD appear
        #  - B: out-of-stock, 6 months old   → SHOULD appear (sixth month edge)
        #  - C: out-of-stock, 3 months old   → SHOULD NOT appear
        #  - D: out-of-stock, 12 months old  → SHOULD NOT appear
        now = datetime.now(timezone.utc)
        cur_idx = now.year * 12 + (now.month - 1)

        def cy_cm(months_back):
            idx = cur_idx - months_back
            return idx // 12, (idx % 12) + 1

        seeds = []
        for i, (label, stock, age) in enumerate([("A", 5, 12), ("B", 0, 6), ("C", 0, 3), ("D", 0, 12)]):
            y, m = cy_cm(age)
            seeds.append({
                "title": f"TEST_iter4 {label}",
                "slug": f"TEST_iter4_{label}_{secrets.token_hex(3)}",
                "description": "seed",
                "board": "ESP32",
                "difficulty": "INTERMEDIATE",
                "cycleMonth": m,
                "cycleYear": y,
                "stockCount": stock,
                "isActive": False,
                "createdAt": now,
            })
        db.projects.insert_many(seeds)

        # mark dev user active so it doesn't 403 on /substitutions (options doesn't require active)
        r = dev_session.get(f"{API}/substitutions/options")
        assert r.status_code == 200, r.text
        items = r.json()
        slugs = {it["slug"]: it for it in items if it.get("slug", "").startswith("TEST_iter4_")}

        a_slug = next((s for s in slugs if s.startswith("TEST_iter4_A_")), None)
        b_slug = next((s for s in slugs if s.startswith("TEST_iter4_B_")), None)
        c_slug = next((s for s in slugs if s.startswith("TEST_iter4_C_")), None)
        d_slug = next((s for s in slugs if s.startswith("TEST_iter4_D_")), None)

        assert a_slug is not None, "in-stock past project should appear regardless of age"
        assert b_slug is not None, "out-of-stock project at 6 months should appear (sixth-month edge)"
        assert c_slug is None, "out-of-stock 3-month project should be hidden"
        assert d_slug is None, "out-of-stock 12-month project should be hidden"

        # sanity flags
        assert slugs[b_slug]["sixthMonth"] is True
        assert slugs[a_slug]["ageMonths"] == 12


# ============================================================
# 7. /api/dev/stats has projection fields
# ============================================================
class TestDevStats:
    def test_dev_stats_projection_fields(self, dev_session):
        r = dev_session.get(f"{API}/dev/stats")
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("active_subscribers", "avg_monthly_growth", "projected_next_month"):
            assert k in data, f"missing {k} in /dev/stats: {data.keys()}"

    def test_dev_stats_requires_dev_role(self, s):
        # unauthenticated
        r = s.get(f"{API}/dev/stats")
        assert r.status_code in (401, 403)
