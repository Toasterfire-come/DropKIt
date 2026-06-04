"""SendGrid email service — drop-in replacement for Gmail SMTP.

When SENDGRID_API_KEY is not set or is a placeholder, all sends log to
console with a [SENDGRID PLACEHOLDER] prefix instead of hitting the API.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

import httpx

log = logging.getLogger("dropkit.sendgrid")


def _is_placeholder() -> bool:
    from config import settings
    return not settings.SENDGRID_API_KEY or settings.SENDGRID_API_KEY.startswith("PLACEHOLDER")


def _from_email() -> Dict[str, str]:
    from config import settings
    email = settings.SHIPPING_FROM_EMAIL or settings.GMAIL_USER or "noreply@dropkit.local"
    name = settings.SHIPPING_FROM_NAME or "DropKit"
    return {"email": email, "name": name}


def _reply_to() -> Dict[str, str]:
    from config import settings
    email = settings.GMAIL_USER or settings.SHIPPING_FROM_EMAIL or ""
    name = settings.SHIPPING_FROM_NAME or "DropKit"
    return {"email": email, "name": name} if email else _from_email()


async def send_html(
    to_emails: List[str],
    subject: str,
    html_body: str,
    unique_args: Optional[Dict[str, str]] = None,
) -> Dict:
    """Send a single HTML email to one or more recipients via SendGrid v3 Mail Send API.

    Returns {"id": "...", "status": "sent"} on success,
    or {"placeholder": True, "skipped": N} when SendGrid isn't configured.
    """
    if _is_placeholder():
        log.info("--- [SENDGRID PLACEHOLDER] ---")
        log.info("  To: %s", ", ".join(to_emails))
        log.info("  Subject: %s", subject)
        log.info("  Body length: %d chars", len(html_body))
        log.info("-----------------------------")
        return {"placeholder": True, "skipped": len(to_emails)}

    from config import settings

    payload = {
        "personalizations": [
            {
                "to": [{"email": e.strip()} for e in to_emails if e.strip()],
                "subject": subject,
            }
        ],
        "from": _from_email(),
        "reply_to": _reply_to(),
        "content": [{"type": "text/html", "value": html_body}],
    }

    if unique_args:
        payload["personalizations"][0]["custom_args"] = unique_args

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if r.status_code in (200, 201, 202):
                # SendGrid returns 202 Accepted on success with no body
                msg_id = r.headers.get("X-Message-Id", "")
                log.info("SendGrid sent to %d recipient(s): %s", len(to_emails), msg_id)
                return {"id": msg_id, "status": "sent"}
            else:
                log.error(
                    "SendGrid error %s: %s",
                    r.status_code,
                    r.text[:500],
                )
                return {"status": "error", "code": r.status_code, "detail": r.text[:300]}
    except httpx.TimeoutException:
        log.warning("SendGrid timeout sending to %s", to_emails[0] if to_emails else "?")
        return {"status": "error", "detail": "timeout"}
    except Exception as e:
        log.exception("SendGrid send failed")
        return {"status": "error", "detail": str(e)}


async def send_single(
    to_email: str,
    subject: str,
    html_body: str,
    unique_id: Optional[str] = None,
) -> Dict:
    """Convenience wrapper for single-recipient sends."""
    return await send_html(
        to_emails=[to_email],
        subject=subject,
        html_body=html_body,
        unique_args={"unique_id": unique_id} if unique_id else None,
    )
