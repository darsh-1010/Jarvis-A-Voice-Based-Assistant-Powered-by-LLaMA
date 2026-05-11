# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""
Google Calendar commands for Jarvis.

Uses a shared OAuth2 helper for token management. On first run, a browser
window opens once to grant access; subsequent runs use the cached token.
Requires GOOGLE_CREDENTIALS_PATH to point to a downloaded OAuth2 JSON.
"""
import datetime
import logging

from jarvis.commands.google_auth import build_google_service
from jarvis.commands.registry import registry
from jarvis.logger import log_action


# Read/write scope so Jarvis can both list and create calendar events
_SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Per-service token cache keeps Calendar and Gmail tokens isolated
_TOKEN_PATH = "./google_token_calendar.json"


def _get_service():
    """Return an authenticated Calendar v3 service, or None on failure."""
    return build_google_service("calendar", "v3", _SCOPES, _TOKEN_PATH)


@registry.register(
    name="list_calendar_events",
    description="List upcoming events from Google Calendar. Optionally specify how many events to fetch.",
)
def list_calendar_events(max_results: int = 5) -> str:
    """
    Fetch upcoming Google Calendar events and return a spoken summary.

    Args:
        max_results: Maximum number of events to fetch (default 5).

    Returns:
        Spoken-ready string listing upcoming events.
    """
    service = _get_service()
    if not service:
        return "Google Calendar is not set up, sir. Please add your credentials file."

    log_action("CALENDAR_LIST", f"Fetching {max_results} upcoming events", "Checking your calendar.")

    try:
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now_iso,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = result.get("items", [])

        if not items:
            return "Your calendar is clear for now, sir."

        summaries = []
        for event in items:
            name = event.get("summary", "Untitled event")
            start_raw = event.get("start", {})
            # All-day events have 'date'; timed events have 'dateTime'
            start_val = start_raw.get("dateTime", start_raw.get("date", "unknown time"))
            summaries.append(f"'{name}' at {start_val}")

        event_list = ", and ".join(summaries)
        count = len(items)
        return f"You have {count} upcoming event{'s' if count > 1 else ''}: {event_list}."

    except Exception as exc:
        log_action(
            "CALENDAR_LIST_ERR",
            f"Error: {exc}",
            "I couldn't retrieve your calendar events.",
            level=logging.ERROR,
        )
        return "I had trouble reading your calendar, sir."


@registry.register(
    name="create_calendar_event",
    description="Create a new Google Calendar event with a title, date, start time, and optional duration.",
)
def create_calendar_event(
    title: str,
    date: str,
    start_time: str,
    duration_hours: int = 1,
) -> str:
    """
    Create a timed Google Calendar event.

    Args:
        title:          Event title / summary.
        date:           Date string in YYYY-MM-DD format.
        start_time:     Start time in HH:MM (24-hour) format.
        duration_hours: Duration in hours (default 1).

    Returns:
        Spoken confirmation string.
    """
    service = _get_service()
    if not service:
        return "Google Calendar is not set up, sir. Please add your credentials file."

    log_action(
        "CALENDAR_CREATE",
        f"Title: '{title}' | Date: {date} | Start: {start_time}",
        f"Creating calendar event '{title}'.",
    )

    try:
        start_dt = datetime.datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + datetime.timedelta(hours=duration_hours)

        event_body = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": config.user_timezone},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": config.user_timezone},
        }

        created = service.events().insert(calendarId="primary", body=event_body).execute()
        event_id = created.get("id", "unknown")
        log_action("CALENDAR_CREATED", f"Event ID: {event_id}", f"Event '{title}' created.")
        return f"Done, sir. I've added '{title}' to your calendar on {date} at {start_time}."

    except ValueError as exc:
        log_action(
            "CALENDAR_CREATE_ERR",
            f"Date parse error: {exc}",
            "Invalid date or time format for calendar event.",
            level=logging.WARNING,
        )
        return "I couldn't create the event due to an invalid date or time format, sir."
    except Exception as exc:
        log_action(
            "CALENDAR_CREATE_ERR",
            f"API error: {exc}",
            "I couldn't create the calendar event.",
            level=logging.ERROR,
        )
        return "I had trouble creating the calendar event, sir."
