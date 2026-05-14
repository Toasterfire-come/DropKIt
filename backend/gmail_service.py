import os
from typing import Optional, List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import smtplib
from email.mime.text import MIMEText

# Placeholder for actual Gmail API client
_gmail_service = None

def _is_placeholder() -> bool:
    """Checks if the Gmail service is running in placeholder mode."""
    return os.environ.get("GMAIL_PLACEHOLDER") == "true"

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
            "redirect_uris": ["http://localhost:3000/auth/gmail/callback"], # Example redirect URI
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
        return {"connected": True, "email": os.environ.get("GMAIL_USER", "placeholder@example.com")}
    # Simulate checking database for user's credentials
    # If credentials exist and are valid, return user info
    # For now, assume connected if not in placeholder mode and GMAIL_USER is set
    if os.environ.get("GMAIL_USER") and os.environ.get("GMAIL_APP_PASSWORD"):
        return {"connected": True, "email": os.environ.get("GMAIL_USER")}
    return None

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
    Sends a blast email using Gmail API.
    """
    if _is_placeholder():
        print(f"--- Placeholder Email Blast ---")
        print(f"From: {sender}")
        print(f"To: {', '.join(recipients)}")
        print(f"Subject: {subject}")
        print(f"Body:\n{html}")
        print(f"-----------------------------")
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
        msg['From'] = sender_email # Use the configured sender email
        msg['To'] = ', '.join(recipients)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipients, msg.as_string())

        return {"sent": len(recipients)}

    except HttpError as error:
        print(f"An error occurred: {error}")
        # Handle specific Gmail API errors if necessary
        return {"error": str(error)}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": str(e)}
