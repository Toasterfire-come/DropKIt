"""DropKit iter2 — auth + ui-mode + dev panel + role-protected endpoint tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

DEV_EMAIL = "dev@dropkit.dev"
DEV_PASSWORD = "dropkit-dev-2026"


def _new_email():
    return f"test_iter2_{int(time.time()*1000)}@dropkit-test.com"


@pytest.fixture(scope="module")
def fresh_email():
    return _new_email()


@pytest.fixture
def user_session():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def dev_session():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    r = sess.post(f"{API}/auth/login", json={"email": DEV_EMAIL, "password": DEV_PASSWORD})
    assert r.status_code == 200, f"dev login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["role"] == "dev"
    return sess


# ---------------- Register / Login / Me / Logout ----------------
def test_register_new_user_returns_user_and_sets_cookie(user_session, fresh_email):
    r = user_session.post(f"{API}/auth/register",
                          json={"email": fresh_email, "password": "password123", "name": "Iter2 Tester"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == fresh_email
    assert data["role"] == "user"
    assert "id" in data and isinstance(data["id"], str)
    assert "access_token" in user_session.cookies
    assert "refresh_token" in user_session.cookies

    me = user_session.get(f"{API}/auth/me")
    assert me.status_code == 200
    me_data = me.json()
    assert me_data["email"] == fresh_email
    assert me_data["role"] == "user"


def test_register_duplicate_email_returns_409(user_session, fresh_email):
    # ensure user from previous test exists; if not, create
    user_session.post(f"{API}/auth/register",
                      json={"email": fresh_email, "password": "password123"})
    r = requests.post(f"{API}/auth/register",
                      json={"email": fresh_email, "password": "password123"})
    assert r.status_code == 409, r.text


def test_register_short_password_returns_422():
    r = requests.post(f"{API}/auth/register",
                      json={"email": _new_email(), "password": "short"})
    assert r.status_code == 422


def test_login_dev_returns_role_dev():
    r = requests.post(f"{API}/auth/login",
                      json={"email": DEV_EMAIL, "password": DEV_PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "dev"
    assert "access_token" in r.cookies


def test_login_wrong_password_returns_401():
    # Use unique IP-distinct email so brute force lockout doesn't trip other tests
    r = requests.post(f"{API}/auth/login",
                      json={"email": f"never_{int(time.time())}@dropkit-test.com",
                            "password": "wrongpassword"})
    assert r.status_code == 401


def test_me_without_cookie_returns_401():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401


def test_logout_clears_cookie():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login", json={"email": DEV_EMAIL, "password": DEV_PASSWORD})
    assert r.status_code == 200
    assert "access_token" in sess.cookies
    r2 = sess.post(f"{API}/auth/logout")
    assert r2.status_code == 200
    # After logout, /me should fail
    r3 = sess.get(f"{API}/auth/me")
    assert r3.status_code == 401


# ---------------- UI mode ----------------
def test_ui_mode_public_get():
    r = requests.get(f"{API}/ui-mode")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] in ("waitlist", "live")


def test_ui_mode_post_unauth_returns_401():
    r = requests.post(f"{API}/ui-mode", json={"mode": "live"})
    assert r.status_code == 401


def test_ui_mode_post_non_dev_returns_403():
    # register a fresh non-dev user
    sess = requests.Session()
    email = _new_email()
    rr = sess.post(f"{API}/auth/register",
                   json={"email": email, "password": "password123"})
    assert rr.status_code == 200
    r = sess.post(f"{API}/ui-mode", json={"mode": "live"})
    assert r.status_code == 403, r.text


def test_ui_mode_post_as_dev_persists_and_revert(dev_session):
    r = dev_session.post(f"{API}/ui-mode", json={"mode": "live"})
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "live"

    # public GET reflects
    r2 = requests.get(f"{API}/ui-mode")
    assert r2.status_code == 200
    assert r2.json()["mode"] == "live"

    # revert to waitlist
    r3 = dev_session.post(f"{API}/ui-mode", json={"mode": "waitlist"})
    assert r3.status_code == 200
    assert r3.json()["mode"] == "waitlist"

    r4 = requests.get(f"{API}/ui-mode")
    assert r4.json()["mode"] == "waitlist"


# ---------------- Dev stats ----------------
def test_dev_stats_requires_dev_role():
    r = requests.get(f"{API}/dev/stats")
    assert r.status_code == 401


def test_dev_stats_as_dev_returns_counts(dev_session):
    r = dev_session.get(f"{API}/dev/stats")
    assert r.status_code == 200, r.text
    body = r.json()
    for key in ("users", "waitlist", "projects", "active_project", "gifts",
                "gifts_redeemed", "substitutions", "vote_cycles", "ui_mode"):
        assert key in body
        if key != "ui_mode":
            assert isinstance(body[key], int)
    assert body["users"] >= 1  # at least the dev user


# ---------------- Votes / Account guards ----------------
def test_votes_post_unauth_returns_401():
    r = requests.post(f"{API}/votes", json={"candidateProjectId": "x"})
    assert r.status_code == 401


def test_account_subscription_with_auth_returns_status():
    sess = requests.Session()
    email = _new_email()
    rr = sess.post(f"{API}/auth/register",
                   json={"email": email, "password": "password123"})
    assert rr.status_code == 200
    r = sess.get(f"{API}/account/subscription")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "inactive"


def test_account_subscription_pause_without_contract_returns_404():
    sess = requests.Session()
    email = _new_email()
    rr = sess.post(f"{API}/auth/register",
                   json={"email": email, "password": "password123"})
    assert rr.status_code == 200
    r = sess.post(f"{API}/account/subscription", json={"action": "pause"})
    assert r.status_code == 404, r.text
