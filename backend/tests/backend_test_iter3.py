"""DropKit iter3 — checkout (public) + dev orders/shipping/gmail/email blast tests."""
import os
import time
import pytest
import requests

# Use REACT_APP_BACKEND_URL since /api routes are routed through ingress to backend
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://mvp-planner-6.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

DEV_EMAIL = "dev@dropkit.dev"
DEV_PASSWORD = "dropkit-dev-2026"

VALID_ADDRESS = {
    "name": "Test Buyer",
    "street1": "123 Test St",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94103",
    "country": "US",
    "phone": "4155550100",
}


# ---------- session fixtures ----------
@pytest.fixture(scope="module")
def dev_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": DEV_EMAIL, "password": DEV_PASSWORD})
    assert r.status_code == 200, f"dev login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def user_session():
    """A logged-in non-dev user session for 403 checks."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"iter3_user_{int(time.time()*1000)}@dropkit-test.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return s


# ============================================================
# Checkout — public
# ============================================================
class TestCheckoutPublic:
    def test_quote_valid_returns_options(self):
        r = requests.post(f"{API}/checkout/quote", json={
            "email": "buyer@example.com", "address": VALID_ADDRESS,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "quote_id" in data and isinstance(data["quote_id"], str)
        opts = data["options"]
        for key in ("cheapest", "priority"):
            assert key in opts
            o = opts[key]
            assert "rate" in o
            assert isinstance(o["shipping_cents"], int)
            assert isinstance(o["tax_cents"], int)
            assert isinstance(o["total_cents"], int)
            assert o["total_cents"] == data["subscription_cents"] + o["shipping_cents"] + o["tax_cents"]
        # Save quote_id for next test on class instance
        TestCheckoutPublic.quote_id = data["quote_id"]

    def test_quote_invalid_email_returns_422(self):
        r = requests.post(f"{API}/checkout/quote", json={
            "email": "not-an-email", "address": VALID_ADDRESS,
        })
        assert r.status_code == 422, r.text

    def test_start_with_valid_quote_returns_redirect(self):
        qid = getattr(TestCheckoutPublic, "quote_id", None)
        assert qid, "previous quote test did not run"
        r = requests.post(f"{API}/checkout/start", json={
            "quote_id": qid, "rate_choice": "cheapest",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "redirect_url" in data
        assert data["redirect_url"].startswith("http")

    def test_start_with_bad_quote_id_returns_404(self):
        # use a valid ObjectId format that does not exist
        r = requests.post(f"{API}/checkout/start", json={
            "quote_id": "000000000000000000000000", "rate_choice": "cheapest",
        })
        assert r.status_code == 404, r.text


# ============================================================
# Dev orders
# ============================================================
class TestDevOrders:
    def test_list_orders_no_auth_returns_401(self):
        r = requests.get(f"{API}/dev/orders")
        assert r.status_code == 401

    def test_list_orders_with_dev_returns_array(self, dev_session):
        r = dev_session.get(f"{API}/dev/orders")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        # capture an order id for detail test (iter1 webhook seeded one)
        if data:
            TestDevOrders.order_id = data[0].get("id") or data[0].get("_id")
        else:
            TestDevOrders.order_id = None

    def test_order_detail_with_dev_returns_hydrated(self, dev_session):
        oid = getattr(TestDevOrders, "order_id", None)
        if not oid:
            pytest.skip("No order present in DB to test detail")
        r = dev_session.get(f"{API}/dev/orders/{oid}")
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("order", "user", "current_project", "shipment"):
            assert key in data

    def test_list_orders_with_non_dev_returns_403(self, user_session):
        r = user_session.get(f"{API}/dev/orders")
        assert r.status_code == 403, r.text


# ============================================================
# Dev shipping (quote + label)
# ============================================================
class TestDevShipping:
    def test_quote_with_dev_returns_rates(self, dev_session):
        # need a real order id — fall back to any 24-char hex string for the request
        oid = getattr(TestDevOrders, "order_id", None) or "000000000000000000000000"
        r = dev_session.post(f"{API}/dev/shipping/quote", json={
            "order_id": oid, "address": VALID_ADDRESS,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "cheapest" in data and "priority" in data
        assert "shipment_id" in data
        # capture for label test
        TestDevShipping.shipment_id = data["shipment_id"]
        TestDevShipping.cheapest_rate_id = data["cheapest"]["id"]

    def test_buy_label_with_dev_returns_urls(self, dev_session):
        oid = getattr(TestDevOrders, "order_id", None)
        if not oid:
            pytest.skip("No order to attach label to")
        sid = getattr(TestDevShipping, "shipment_id", None)
        rid = getattr(TestDevShipping, "cheapest_rate_id", None)
        if not sid or not rid:
            pytest.skip("Previous quote did not run")
        r = dev_session.post(f"{API}/dev/shipping/labels", json={
            "order_id": oid, "shipment_id": sid, "rate_id": rid,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        # placeholder mode should expose label urls + tracking_code
        assert "tracking_code" in data
        assert data.get("placeholder") is True
        # at least one of pdf/zpl/qr/postage_url should be present
        url_keys = {k for k in data.keys() if "url" in k.lower()}
        assert len(url_keys) >= 1, f"No label urls returned: {data}"


# ============================================================
# Dev Gmail
# ============================================================
class TestDevGmail:
    def test_status_no_auth_returns_401(self):
        r = requests.get(f"{API}/dev/gmail/status")
        assert r.status_code == 401

    def test_status_as_dev_returns_disconnected(self, dev_session):
        r = dev_session.get(f"{API}/dev/gmail/status")
        assert r.status_code == 200, r.text
        # connected should be False since placeholder creds
        assert r.json().get("connected") is False

    def test_connect_as_dev_returns_auth_url(self, dev_session):
        r = dev_session.post(f"{API}/dev/gmail/connect")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "auth_url" in data
        # placeholder should still be a google domain url
        assert "accounts.google.com" in data["auth_url"], f"auth_url={data['auth_url']}"

    def test_connect_as_non_dev_returns_403(self, user_session):
        r = user_session.post(f"{API}/dev/gmail/connect")
        assert r.status_code == 403


# ============================================================
# Dev Email Blast
# ============================================================
class TestDevEmailBlast:
    def test_blast_test_to_returns_placeholder(self, dev_session):
        r = dev_session.post(f"{API}/dev/email/blast", json={
            "subject": "TEST_iter3 subject",
            "html": "<p>Hello from iter3 test</p>",
            "audience": "waitlist",
            "test_to": "test_iter3@dropkit-test.com",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("total") == 1
        assert data.get("skipped") == 1
        assert data.get("placeholder") is True

    def test_blast_waitlist_audience_returns_placeholder(self, dev_session):
        # seed a waitlist row to ensure recipients > 0
        seed_email = f"iter3_wl_{int(time.time()*1000)}@dropkit-test.com"
        wl = requests.post(f"{API}/waitlist", json={"email": seed_email})
        assert wl.status_code in (200, 201, 409), wl.text

        r = dev_session.post(f"{API}/dev/email/blast", json={
            "subject": "TEST_iter3 mass",
            "html": "<p>hi</p>",
            "audience": "waitlist",
        })
        # Could 200 (placeholder) or 400 (no recipients) — assert clean state
        assert r.status_code in (200, 400), r.text
        if r.status_code == 200:
            data = r.json()
            assert data.get("total", 0) > 0
            assert data.get("skipped") == data.get("total")
            assert data.get("placeholder") is True

    def test_blasts_history_as_dev(self, dev_session):
        r = dev_session.get(f"{API}/dev/email/blasts")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_blast_as_non_dev_returns_403(self, user_session):
        r = user_session.post(f"{API}/dev/email/blast", json={
            "subject": "x", "html": "y", "test_to": "x@y.com",
        })
        assert r.status_code == 403
