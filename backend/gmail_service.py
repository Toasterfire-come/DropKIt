"""Gmail API integration — OAuth2 install + send.

Tokens are stored per-dev-user in MongoDB collection `gmail_tokens`.
"""
import base64
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from config import settings
from db import get_db

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


def _is_placeholder() -> bool:
    return (
        not settings.GMAIL_CLIENT_ID
        or settings.GMAIL_CLIENT_ID.startswith("PLACEHOLDER")
        or not settings.GMAIL_CLIENT_SECRET
        or settings.GMAIL_CLIENT_SECRET.startswith("PLACEHOLDER")
    )


def _flow() -> Flow:
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GMAIL_REDIRECT_URI],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.GMAIL_REDIRECT_URI,
    )


def build_auth_url(state: str) -> str:
    if _is_placeholder():
        # Return a placeholder URL the UI can show; clicking does nothing useful
        # but the dev page renders correctly.
        return f"https://accounts.google.com/o/oauth2/auth?placeholder=1&state={state}"
    flow = _flow()
    url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent", state=state
    )
    return url


async def exchange_code(code: str, user_id: str) -> dict:
    if _is_placeholder():
        raise RuntimeError("Gmail credentials are PLACEHOLDER — cannot exchange code")

    flow = _flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Look up email via tokeninfo
    email = None
    try:
        service = build("oauth2", "v2", credentials=creds, cache_discovery=False)
        info = service.userinfo().get().execute()
        email = info.get("email")
    except Exception:
        pass

    expires_at = creds.expiry or (datetime.now(timezone.utc) + timedelta(hours=1))
    doc = {
        "user_id": user_id,
        "refresh_token": creds.refresh_token,
        "access_token": creds.token,
        "expires_at": expires_at,
        "scopes": list(creds.scopes or []),
        "connected_email": email,
        "updated_at": datetime.now(timezone.utc),
    }

    db = get_db()
    await db.gmail_tokens.update_one(
        {"user_id": user_id}, {"$set": doc}, upsert=True
    )
    return {"connected_email": email}


async def get_connected(user_id: str) -> Optional[dict]:
    db = get_db()
    return await db.gmail_tokens.find_one({"user_id": user_id})


async def disconnect(user_id: str) -> bool:
    db = get_db()
    res = await db.gmail_tokens.delete_one({"user_id": user_id})
    return res.deleted_count > 0


def _build_credentials(token_doc: dict) -> Credentials:
    return Credentials(
        token=token_doc.get("access_token"),
        refresh_token=token_doc.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
        scopes=token_doc.get("scopes") or GMAIL_SCOPES,
    )


async def send_blast(user_id: str, sender: str, subject: str, html: str, recipients: List[str]) -> dict:
    """Send the same message individually to each recipient. Returns per-recipient status."""
    if _is_placeholder():
        return {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "skipped": len(recipients),
            "placeholder": True,
            "details": [{"recipient": r, "status": "skipped_placeholder"} for r in recipients],
        }

    token_doc = await get_connected(user_id)
    if not token_doc:
        raise RuntimeError("Gmail not connected for this dev user")

    creds = _build_credentials(token_doc)
    if not creds.valid:
        creds.refresh(Request())
        db = get_db()
        await db.gmail_tokens.update_one(
            {"user_id": user_id},
            {"$set": {"access_token": creds.token, "expires_at": creds.expiry or datetime.now(timezone.utc) + timedelta(hours=1)}},
        )

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    sent, failed = 0, 0
    details = []
    for to in recipients:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = to
            msg.attach(MIMEText(html, "html"))
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            r = service.users().messages().send(userId="me", body={"raw": raw}).execute()
            details.append({"recipient": to, "status": "sent", "message_id": r.get("id")})
            sent += 1
        except Exception as e:
            details.append({"recipient": to, "status": "failed", "error": str(e)})
            failed += 1

    return {
        "total": len(recipients), "sent": sent, "failed": failed, "skipped": 0,
        "placeholder": False, "details": details,
    }
