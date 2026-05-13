"""DropKit backend API tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://mvp-planner-6.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_TOKEN = "dropkit-admin-dev-token"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# Health
def test_health(s):
    r = s.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_launch_mode(s):
    r = s.get(f"{API}/launch-mode")
    assert r.status_code == 200
    assert r.json() == {"mode": "waitlist"}


# Waitlist
def test_waitlist_valid_idempotent(s):
    email = f"test_{int(time.time())}@dropkit-test.com"
    r1 = s.post(f"{API}/waitlist", json={"email": email, "source": "test"})
    assert r1.status_code == 200, r1.text
    assert r1.json()["ok"] is True
    r2 = s.post(f"{API}/waitlist", json={"email": email, "source": "test"})
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_waitlist_invalid_email(s):
    r = s.post(f"{API}/waitlist", json={"email": "not-an-email"})
    assert r.status_code == 422


# Projects empty
def test_projects_current_null(s):
    r = s.get(f"{API}/projects/current")
    assert r.status_code == 200
    # may be null if no active project. Allow null or dict
    assert r.json() is None or isinstance(r.json(), dict)


def test_projects_past_limit(s):
    r = s.get(f"{API}/projects/past?limit=6")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_projects_list(s):
    r = s.get(f"{API}/projects")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_projects_nonexistent(s):
    r = s.get(f"{API}/projects/does-not-exist-xyz-123")
    assert r.status_code == 404


# Votes
def test_votes_current_null(s):
    r = s.get(f"{API}/votes/current")
    assert r.status_code == 200


def test_votes_submit_unauth(s):
    r = s.post(f"{API}/votes", json={"candidateProjectId": "x"})
    assert r.status_code == 401


# Subscriber endpoints unauth
def test_account_sub_unauth(s):
    r = s.get(f"{API}/account/subscription")
    assert r.status_code == 401


def test_substitutions_options_unauth(s):
    r = s.get(f"{API}/substitutions/options")
    assert r.status_code == 401


# Gifts
def test_gift_invalid(s):
    r = s.post(f"{API}/gifts/redeem", json={"code": "INVALID-XXXX-0000"})
    assert r.status_code == 404


# FAQ
def test_faq(s):
    r = s.get(f"{API}/faq")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 10
    assert all("q" in i and "a" in i for i in data)


# Admin
def test_admin_no_token(s):
    payload = {
        "slug": "unauth-test", "title": "t", "description": "d", "board": "ESP32",
        "difficulty": "INTERMEDIATE", "cycleMonth": 1, "cycleYear": 2026,
    }
    r = s.post(f"{API}/admin/projects", json=payload)
    assert r.status_code == 401, f"expected 401 got {r.status_code}: {r.text}"


def test_admin_create_and_activate_project(s):
    slug = f"test-proj-{int(time.time())}"
    payload = {
        "slug": slug,
        "title": "Test Project",
        "description": "test desc",
        "board": "ESP32",
        "difficulty": "INTERMEDIATE",
        "cycleMonth": 1,
        "cycleYear": 2026,
        "isActive": True,
        "stockCount": 10,
    }
    r = s.post(f"{API}/admin/projects", json=payload, headers={"X-Admin-Token": ADMIN_TOKEN})
    assert r.status_code in (200, 201), r.text
    created = r.json()
    assert created["slug"] == slug

    # GET /projects shows it
    r2 = s.get(f"{API}/projects")
    assert any(p.get("slug") == slug for p in r2.json())

    # GET by slug
    r3 = s.get(f"{API}/projects/{slug}")
    assert r3.status_code == 200
    assert r3.json()["slug"] == slug

    # GET current returns it
    r4 = s.get(f"{API}/projects/current")
    assert r4.status_code == 200
    cur = r4.json()
    assert cur is not None and cur["slug"] == slug

    # Cleanup
    pid = created.get("id") or created.get("_id")
    if pid:
        s.delete(f"{API}/admin/projects/{pid}", headers={"X-Admin-Token": ADMIN_TOKEN})


# Shopify webhook (placeholder secret bypass)
def test_shopify_webhook_orders_paid(s):
    body = {
        "id": 999888777,
        "total_price": "40.00",
        "customer": {
            "id": 12345,
            "email": "webhookuser@dropkit.test",
            "admin_graphql_api_id": "gid://shopify/Customer/12345",
        },
        "line_items": [],
    }
    r = requests.post(
        f"{API}/webhooks/shopify",
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Topic": "orders/paid",
            "X-Shopify-Hmac-Sha256": "placeholder",
            "X-Shopify-Shop-Domain": "dropkit-dev.myshopify.com",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json().get("received") is True
