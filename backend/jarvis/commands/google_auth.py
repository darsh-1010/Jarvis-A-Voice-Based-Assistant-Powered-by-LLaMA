# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""
Shared Google OAuth2 authentication helper for Jarvis.

Centralises the token-acquisition and refresh logic so Calendar and Gmail
can reuse one code path instead of duplicating it — eliminating the
duplicate-code lint violation and making credential rotation a single-file change.
"""
import logging
import os

from jarvis.config import config
from jarvis.logger import log_action


def build_google_service(api_name: str, api_version: str, scopes: list[str], token_path: str):
    """
    Build and return an authenticated Google API service client.

    Loads credentials from the path configured in GOOGLE_CREDENTIALS_PATH,
    refreshes the access token when expired, and runs the browser-based
    OAuth flow only on the very first use.

    Args:
        api_name:    Google API name (e.g. 'calendar', 'gmail').
        api_version: API version string (e.g. 'v3', 'v1').
        scopes:      List of OAuth2 scope strings required by the API.
        token_path:  Local file path where the cached token JSON is stored.

    Returns:
        A googleapiclient Resource, or None if auth fails.
    """
    creds_path = config.google_credentials_path
    if not os.path.exists(creds_path):
        log_action(
            "GOOGLE_AUTH_MISSING",
            f"Credentials not found at: {creds_path}",
            "Google credentials file is missing.",
            level=logging.WARNING,
        )
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)

        # Refresh expired token or run the OAuth flow for the first time
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())

        return build(api_name, api_version, credentials=creds)

    except Exception as exc:
        log_action(
            "GOOGLE_AUTH_ERR",
            f"Auth error for {api_name}: {exc}",
            f"I couldn't authenticate with Google {api_name}.",
            level=logging.ERROR,
        )
        return None
