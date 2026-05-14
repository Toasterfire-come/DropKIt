import os
from typing import Optional, List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import smtplib
from email.mime.text import MIMEText
import logging

log = logging.getLogger("dropkit.gmail")

# Placeholder for actual Gmail API client
_gmail_service = None

def _is_placeholder() -> bool:
    """Checks if the Gmail service is running in placeholder mode."""
    # Check if GMAIL_USER or GMAIL_APP_PASSWORD are not set or are placeholders
    return not os.environ.get("GMAIL_USER") or not os.environ.get("GMAIL_APP_PASSWORD") or \
           os.environ.get("GMAIL_USER").startswith("PLACEHOLDER") or \
           os.environ.get("GMAIL_APP_PASSWORD").startswith("PLACEHOLDER")

def _flow() -> Flow:
    """Builds the OAuth2 flow for Gmail API."""
    # In a real application, you would load client secrets from a file.
    # For this example, we'll assume they are set as environment variables
    # or handled elsewhere.
    # For simplicity, we'll use a dummy client ID and secret here.
    # In production, these should be securely managed.
    client_config = {
        "installed": {
            "client_id": os.environ.get("GMAIL_CLIENT_ID", "dummy_client_id"),
            "client_secret": os.environ.get("GMAIL_CLIENT_SECRET", "dummy_client_secret"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.environ.get("GMAIL_REDIRECT_URI", "http://localhost:3000/auth/gmail/callback")], # Example redirect URI
        }
    }
    scopes = ["https://www.googleapis.com/auth/gmail.send"]
    return Flow.from_client_config(client_config, scopes=scopes)

async def get_connected(user_id: str) -> Optional[Dict]:
    """
    Checks if a user is connected to Gmail.
    In a real app, this would query a database for stored credentials.
    For this example, we'll simulate a connection status.
    """
    if _is_placeholder():
        # Return placeholder info if not configured or placeholder creds are used
        return {"connected": False, "email": os.environ.get("GMAIL_USER", "placeholder@example.com")}

    # Simulate checking database for user's credentials
    # If credentials exist and are valid, return user info
    # For now, assume connected if not in placeholder mode and GMAIL_USER/APP_PASSWORD are set
    if os.environ.get("GMAIL_USER") and os.environ.get("GMAIL_APP_PASSWORD"):
        return {"connected": True, "email": os.environ.get("GMAIL_USER")}
    return {"connected": False, "email": os.environ.get("GMAIL_USER", "placeholder@example.com")}

def _build_credentials(token_doc: Dict) -> Credentials:
    """Builds Credentials object from a token document."""
    return Credentials(
        token=token_doc.get("access_token"),
        refresh_token=token_doc.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GMAIL_CLIENT_ID", "dummy_client_id"),
        client_secret=os.environ.get("GMAIL_CLIENT_SECRET", "dummy_client_secret"),
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )

async def send_blast(user_id: str, sender: str, subject: str, html: str, recipients: List[str]) -> Dict:
    """
    Sends a blast email using Gmail API via SMTP with App Password.
    """
    if _is_placeholder():
        log.info(f"--- Placeholder Email Blast ---")
        log.info(f"From: {sender}")
        log.info(f"To: {', '.join(recipients)}")
        log.info(f"Subject: {subject}")
        log.info(f"Body:\n{html}")
        log.info(f"-----------------------------")
        return {"placeholder": True, "skipped": len(recipients)}

    # Use environment variables for sender email and app password
    sender_email = os.environ.get("GMAIL_USER")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender_email:
        raise ValueError("GMAIL_USER environment variable not set.")
    if not app_password:
        raise ValueError("GMAIL_APP_PASSWORD environment variable not set.")

    try:
        # Using SMTP for sending emails with App Password
        msg = MIMEText(html, 'html')
        msg['Subject'] = subject
        msg['From'] = sender_email # Use the configured sender email from GMAIL_USER
        msg['To'] = ', '.join(recipients)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipients, msg.as_string())

        log.info(f"Successfully sent email blast to {len(recipients)} recipients.")
        return {"sent": len(recipients)}

    except smtplib.SMTPAuthenticationError as e:
        log.error(f"SMTP Authentication error: {e}. Check GMAIL_USER and GMAIL_APP_PASSWORD.")
        raise ValueError(f"SMTP Authentication error: {e}. Check credentials.") from e
    except smtplib.SMTPException as e:
        log.error(f"SMTP error occurred: {e}")
        raise RuntimeError(f"SMTP error occurred: {e}") from e
    except Exception as e:
        log.exception(f"An unexpected error occurred during email sending: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

async def disconnect(user_id: str) -> bool:
    """
    Simulates disconnecting Gmail. In a real app, this would remove stored credentials.
    """
    if _is_placeholder():
        return True # Placeholder disconnect is always successful
    # Simulate removing credentials from database
    log.info(f"Simulating Gmail disconnect for user_id: {user_id}")
    # In a real implementation, you would delete the stored credentials for this user_id
    return True
