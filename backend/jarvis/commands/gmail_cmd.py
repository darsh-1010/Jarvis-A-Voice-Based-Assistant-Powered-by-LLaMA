# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""
Gmail commands for Jarvis.

Reads unread inbox subjects and sends emails via OAuth2.
Uses the shared google_auth helper to eliminate duplicate auth code.
"""
import base64
import logging
from email.mime.text import MIMEText

from jarvis.commands.google_auth import build_google_service
from jarvis.commands.registry import registry
from jarvis.logger import log_action


# Modify scope — grants both reading and sending permissions
_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Separate token from Calendar so scopes remain isolated per service
_TOKEN_PATH = "./google_token_gmail.json"

# Surfaces this many unread messages by default — enough for a quick briefing
_DEFAULT_INBOX_COUNT = 5


def _get_service():
    """Return an authenticated Gmail v1 service, or None on failure."""
    return build_google_service("gmail", "v1", _SCOPES, _TOKEN_PATH)


@registry.register(
    name="read_inbox",
    description="Read the latest unread email subjects from your Gmail inbox.",
)
def read_inbox(max_results: int = _DEFAULT_INBOX_COUNT) -> str:
    """
    Fetch the subjects of the most recent unread Gmail messages.

    Args:
        max_results: Maximum number of unread messages to surface (default 5).

    Returns:
        Spoken-ready string listing email subjects.
    """
    service = _get_service()
    if not service:
        return "Gmail is not configured, sir. Please add your Google credentials file."

    log_action("GMAIL_READ", f"Fetching {max_results} unread messages", "Checking your Gmail inbox.")

    try:
        result = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_results)
            .execute()
        )
        messages = result.get("messages", [])

        if not messages:
            return "Your inbox is clear, sir. No unread messages."

        subjects = []
        for msg in messages:
            detail = service.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
            headers = detail.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No subject")
            subjects.append(f"'{subject}'")

        count = len(subjects)
        return f"You have {count} unread email{'s' if count > 1 else ''}. Subjects: {', '.join(subjects)}."

    except Exception as exc:
        log_action(
            "GMAIL_READ_ERR",
            f"Error: {exc}",
            "I couldn't read your inbox.",
            level=logging.ERROR,
        )
        return "I had trouble reading your Gmail inbox, sir."


@registry.register(
    name="send_email",
    description="Send an email via Gmail. Provide the recipient address, subject, and message body.",
)
def send_email(to: str, subject: str, body: str) -> str:
    """
    Compose and send a Gmail message.

    Args:
        to:      Recipient email address.
        subject: Email subject line.
        body:    Plain-text message body.

    Returns:
        Spoken confirmation or error message.
    """
    service = _get_service()
    if not service:
        return "Gmail is not configured, sir. Please add your Google credentials file."

    # Mask recipient in logs — never log full email addresses per security policy
    masked_to = f"***{to[-10:]}" if len(to) > 10 else "***"
    log_action("GMAIL_SEND", f"To: {masked_to} | Subject: '{subject}'", f"Sending email '{subject}'.")

    try:
        mime_message = MIMEText(body)
        mime_message["to"] = to
        mime_message["subject"] = subject

        # Gmail API requires base64url-encoded raw MIME bytes
        raw_bytes = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw_bytes}).execute()

        log_action("GMAIL_SENT", f"Subject: '{subject}'", "Email sent successfully.")
        return f"Email sent successfully, sir. Subject: '{subject}'."

    except Exception as exc:
        log_action(
            "GMAIL_SEND_ERR",
            f"Error: {exc}",
            "I couldn't send the email.",
            level=logging.ERROR,
        )
        return "I had trouble sending the email, sir."
