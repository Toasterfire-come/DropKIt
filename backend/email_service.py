"""DropKit email dispatcher — pure Gmail API, no Klaviyo.

Drop-in replacement for the old `klaviyo_service`: same public surface
(`fire`, `waitlist_joined`, `referrer_notify_new_signup`, etc.) so every
caller in routes_public / routes_webhooks / routes_admin keeps working.

Each function:
  1. Picks the matching HTML template from /app/backend/email_templates/
  2. Substitutes `{{ var }}` tokens against the event properties
  3. Wraps it in `_layout.html`
  4. Queues a Gmail API send via the dev user's connected mailbox

When Gmail OAuth isn't connected yet (placeholder creds or no token row),
sends silently no-op — exactly like the old Klaviyo behaviour.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import gmail_service
from db import get_db

log = logging.getLogger("dropkit.email")

TEMPLATES_DIR = Path(__file__).parent / "email_templates"
_LAYOUT_CACHE: Optional[str] = None
_TEMPLATE_CACHE: Dict[str, str] = {}


def _layout() -> str:
    global _LAYOUT_CACHE
    if _LAYOUT_CACHE is None:
        _LAYOUT_CACHE = (TEMPLATES_DIR / "_layout.html").read_text(encoding="utf-8")
    return _LAYOUT_CACHE


def _load(filename: str) -> str:
    if filename not in _TEMPLATE_CACHE:
        path = TEMPLATES_DIR / filename
        _TEMPLATE_CACHE[filename] = path.read_text(encoding="utf-8") if path.exists() else ""
    return _TEMPLATE_CACHE[filename]


def _render(filename: str, ctx: Dict[str, Any]) -> str:
    """Render a body template into _layout.html with simple `{{ key }}` substitution."""
    body = _load(filename)
    if not body:
        body = "<p>(template missing)</p>"
    layout = _layout()

    # Strip Jinja-style template inheritance blocks so the body is plain HTML
    body = re.sub(r"{%\s*extends[^%]*%}", "", body)
    body = re.sub(r"{%\s*block\s+\w+\s*%}", "", body)
    body = re.sub(r"{%\s*endblock\s*%}", "", body)

    def _sub(html: str) -> str:
        def repl(m: re.Match) -> str:
            key = m.group(1).strip().split(".")[-1]  # `event.first_name` → `first_name`
            v = ctx.get(key, "")
            return "" if v is None else str(v)
        return re.sub(r"{{\s*([^}]+?)\s*}}", repl, html)

    rendered_body = _sub(body)
    full = layout.replace("{% block body %}{% endblock %}", rendered_body)
    # Final pass for tokens that live in the layout itself
    return _sub(full)


async def _dev_user_id() -> Optional[str]:
    """Cache lookup of the dev user — we send from their connected Gmail."""
    db = get_db()
    u = await db.users.find_one({"role": "dev"})
    return str(u["_id"]) if u else None


async def _send(recipient: str, subject: str, html: str, unique_id: Optional[str] = None) -> None:
    """Single-recipient Gmail send. No-op when Gmail isn't connected."""
    if not recipient:
        return
    db = get_db()
    if unique_id:
        seen = await db.email_log.find_one({"unique_id": unique_id})
        if seen:
            return  # idempotency guard

    user_id = await _dev_user_id()
    if not user_id:
        result = {"placeholder": True, "reason": "no_dev_user"}
    else:
        token = await gmail_service.get_connected(user_id)
        sender = (token or {}).get("connected_email") or os.environ.get("SHIPPING_FROM_EMAIL", "")
        try:
            result = await gmail_service.send_blast(
                user_id=user_id, sender=sender,
                subject=subject, html=html, recipients=[recipient],
            )
        except RuntimeError as e:
            log.warning("Gmail send skipped (%s) → %s", recipient, e)
            result = {"placeholder": True, "error": str(e)}

    await db.email_log.insert_one({
        "unique_id": unique_id,
        "recipient": recipient,
        "subject": subject,
        "result": result,
        "created_at": datetime.now(timezone.utc),
    })


def fire(coro) -> None:
    """Fire-and-forget — schedule on the current loop and log errors."""
    try:
        loop = asyncio.get_event_loop()
        task = loop.create_task(coro)

        def _log(t):
            if t.cancelled():
                return
            exc = t.exception()
            if exc:
                log.error("email background task failed: %s", exc)

        task.add_done_callback(_log)
    except Exception:
        log.exception("Failed to schedule email task")


# ============================================================
# 12 lifecycle event helpers — signatures match the old klaviyo_service
# ============================================================
async def waitlist_joined(email, first_name, referral_code,
                          referred_by_code=None, referred_via=None,
                          source="home_hero"):
    ctx = {
        "first_name": first_name, "referral_code": referral_code,
        "share_url": f"/?ref={referral_code}",
        "referred_by_code": referred_by_code or "",
        "referred_via": referred_via or "", "source": source,
    }
    html = _render("01_waitlist_joined.html", ctx)
    await _send(email, f"You're on the DropKit list, {first_name}", html, f"waitlist:{referral_code}")


# Klaviyo compatibility shim — legacy callers expect a `subscribe_to_waitlist`
async def subscribe_to_waitlist(*args, **kwargs):
    return None


async def referrer_notify_new_signup(referrer_email, referrer_name,
                                     referee_first_name, waitlist_referrals,
                                     referral_code):
    ctx = {
        "referrer_first_name": referrer_name.split(" ", 1)[0] if referrer_name else "",
        "referee_first_name": referee_first_name,
        "referrals_so_far": waitlist_referrals,
        "referrals_needed_for_priority": max(0, 3 - waitlist_referrals),
        "referral_code": referral_code,
        "share_url": f"/?ref={referral_code}",
    }
    html = _render("02_referral_joined.html", ctx)
    await _send(referrer_email, "Someone joined with your DropKit link",
                html, f"refjoin:{referrer_email}:{waitlist_referrals}")


async def priority_unlocked(email, first_name, referral_code):
    ctx = {"first_name": first_name, "referral_code": referral_code,
           "share_url": f"/?ref={referral_code}"}
    html = _render("03_priority_unlocked.html", ctx)
    await _send(email, "You unlocked priority shipping", html, f"priority:{referral_code}")


async def free_month_earned(email, first_name, referral_code, discount_code,
                            discount_amount_cents, discount_expires_at):
    ctx = {
        "first_name": first_name, "referral_code": referral_code,
        "discount_code": discount_code,
        "discount_amount": f"${discount_amount_cents / 100:.2f}",
        "discount_expires_at": discount_expires_at,
        "milestone": "5_referrals",
    }
    html = _render("04_free_month_earned.html", ctx)
    await _send(email, "You earned a free month on us", html, f"reward:{discount_code}")


async def subscription_welcome(email, first_name, order_id, first_kit_title=None):
    ctx = {"first_name": first_name, "order_id": order_id,
           "first_kit_title": first_kit_title or "your first DropKit project"}
    html = _render("05_subscription_welcome.html", ctx)
    await _send(email, "Welcome to DropKit", html, f"welcome:{order_id}")


async def vote_opened(email, first_name, cycle_label, candidates, vote_url, closes_at):
    cands_html = "".join(
        f"<li><strong>{c.get('title','')}</strong> · {c.get('board','')} · {c.get('difficulty','')}</li>"
        for c in (candidates or [])
    )
    ctx = {"first_name": first_name, "cycle_label": cycle_label,
           "candidates_html": cands_html, "vote_url": vote_url, "closes_at": closes_at}
    html = _render("06_vote_opened.html", ctx)
    await _send(email, "Vote opens now — pick the next DropKit project",
                html, f"vote_open:{email}:{cycle_label}")


async def vote_results(email, first_name, cycle_label, winner_title, winner_url, total_votes):
    ctx = {"first_name": first_name, "cycle_label": cycle_label,
           "winner_title": winner_title, "winner_url": winner_url,
           "total_votes": total_votes}
    html = _render("07_vote_results.html", ctx)
    await _send(email, f"Winner: {winner_title}", html, f"vote_result:{email}:{cycle_label}")


async def substitution_confirmed(email, first_name, original_title,
                                 substituted_title, cycle_label):
    ctx = {"first_name": first_name, "original_title": original_title,
           "substituted_title": substituted_title, "cycle_label": cycle_label}
    html = _render("08_substitution_confirmed.html", ctx)
    await _send(email, f"Substitution confirmed for {cycle_label}",
                html, f"sub:{email}:{cycle_label}")


async def gift_purchased(buyer_email, buyer_first_name, recipient_email,
                         duration_months, order_id):
    ctx = {"buyer_first_name": buyer_first_name or "",
           "recipient_email": recipient_email,
           "duration_months": duration_months, "order_id": order_id}
    html = _render("09_gift_purchased.html", ctx)
    await _send(buyer_email, "Your DropKit gift is on the way",
                html, f"gift_buy:{order_id}")


async def gift_code_issued(recipient_email, code, duration_months, redeem_url):
    ctx = {"gift_code": code, "duration_months": duration_months, "redeem_url": redeem_url}
    html = _render("10_gift_code_issued.html", ctx)
    await _send(recipient_email, "You got a DropKit gift", html, f"gift_code:{code}")


async def gift_redeemed(buyer_email, recipient_email, code, duration_months):
    ctx = {"recipient_email": recipient_email, "gift_code": code,
           "duration_months": duration_months}
    html = _render("11_gift_redeemed.html", ctx)
    await _send(buyer_email, "Your DropKit gift was redeemed",
                html, f"gift_redeem:{code}")


async def launch_announcement(email, first_name, launch_url):
    ctx = {"first_name": first_name, "launch_url": launch_url}
    html = _render("12_launch_announcement.html", ctx)
    await _send(email, "DropKit is live", html, f"launch:{email}")


async def replacement_approved(email, first_name, kit_title, component_name,
                               order_label, tracking_code, tracking_url):
    ctx = {
        "first_name": first_name or "maker",
        "kit_title": kit_title or "DropKit",
        "component_name": component_name,
        "order_label": order_label,
        "tracking_code": tracking_code or "—",
        "tracking_url": tracking_url or "#",
    }
    html = _render("13_replacement_approved.html", ctx)
    await _send(email, f"Replacement on the way: {component_name}",
                html, f"replace:{order_label}:{component_name}")


async def cycle_summary(email, cycle_label, orders_shipped, gross_revenue,
                        refunds, net_revenue, substitutions, new_subscribers,
                        churned, projected_next):
    ctx = {
        "cycle_label": cycle_label,
        "orders_shipped": orders_shipped,
        "gross_revenue": f"{gross_revenue:.2f}",
        "refunds": f"{refunds:.2f}",
        "net_revenue": f"{net_revenue:.2f}",
        "substitutions": substitutions,
        "new_subscribers": new_subscribers,
        "churned": churned,
        "projected_next": projected_next,
    }
    html = _render("14_cycle_summary.html", ctx)
    await _send(email, f"{cycle_label} · cycle closed", html, f"cycle_close:{cycle_label}")


async def tax_nexus_alert(email, state, ytd_revenue_cents, threshold_cents):
    body = f"""
    <div style="font-family:Inter,sans-serif;color:#F0F0EE;">
      <h1 style="font-size:22px;">Tax nexus crossing — {state}</h1>
      <p>Year-to-date revenue from <strong>{state}</strong> shipments has crossed
         <strong>80%</strong> of that state's economic-nexus threshold.</p>
      <table cellpadding="8" style="border-collapse:collapse;border:1px solid #30363D;font-family:ui-monospace,monospace;">
        <tr><td>YTD revenue from {state}</td><td><strong>${ytd_revenue_cents / 100:,.2f}</strong></td></tr>
        <tr><td>Nexus threshold</td><td>${threshold_cents / 100:,.2f}</td></tr>
      </table>
      <p style="margin-top:20px;">Register a sales-tax permit in {state} before the next ship-out
         or talk to your CPA. Once you cross 100%, every dollar after that is taxable retroactively.</p>
    </div>
    """
    layout = _layout().replace("{% block body %}{% endblock %}", body)
    await _send(email, f"⚠️ Sales tax nexus crossing — {state}",
                layout, f"nexus:{state}:{datetime.now(timezone.utc).strftime('%Y-%m')}")
