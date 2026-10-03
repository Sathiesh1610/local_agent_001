"""Google Calendar synchronization primitives for reviewed roster events.

This module deliberately does not parse Excel files or render a UI.  The next
review-window phase can create :class:`CalendarEvent` objects, let the user
edit them, and call ``sync_events`` only after explicit confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo


# These narrow scopes permit calendar selection and event management without
# requesting unrelated Google account access.
SCOPES = (
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events",
)
SOURCE_PROPERTY = "local_agent_source_id"
DEFAULT_TIMEZONE = "Asia/Kolkata"


@dataclass(frozen=True)
class CalendarEvent:
    """An approved local event ready to be created or updated in Google.

    ``source_id`` must be stable for the same roster event. It is stored as a
    private Google Calendar extended property and is used to prevent duplicate
    imports on later syncs.
    """

    source_id: str
    summary: str
    start: date | datetime
    end: date | datetime
    description: str = ""
    location: str = ""
    timezone: str = DEFAULT_TIMEZONE
    color_id: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("CalendarEvent.source_id is required.")
        if not self.summary.strip():
            raise ValueError("CalendarEvent.summary is required.")

        start_is_datetime = isinstance(self.start, datetime)
        end_is_datetime = isinstance(self.end, datetime)
        if start_is_datetime != end_is_datetime:
            raise ValueError("Event start and end must both be dates or both be datetimes.")
        if self.end <= self.start:
            raise ValueError("Event end must be later than its start.")

    @property
    def is_all_day(self) -> bool:
        return not isinstance(self.start, datetime)

    def to_google_resource(self) -> dict[str, Any]:
        """Return the Calendar API request body for this event."""
        resource: dict[str, Any] = {
            "summary": self.summary,
            "extendedProperties": {"private": {SOURCE_PROPERTY: self.source_id}},
        }
        if self.description:
            resource["description"] = self.description
        if self.location:
            resource["location"] = self.location
        if self.color_id:
            resource["colorId"] = self.color_id

        if self.is_all_day:
            resource["start"] = {"date": self.start.isoformat()}
            resource["end"] = {"date": self.end.isoformat()}
        else:
            start = _with_timezone(self.start, self.timezone)
            end = _with_timezone(self.end, self.timezone)
            resource["start"] = {"dateTime": start.isoformat(), "timeZone": self.timezone}
            resource["end"] = {"dateTime": end.isoformat(), "timeZone": self.timezone}
        return resource


@dataclass(frozen=True)
class SyncResult:
    """The result of one create-or-update operation."""

    source_id: str
    google_event_id: str
    action: str  # "created" or "updated"
    html_link: str | None = None


def _with_timezone(value: datetime, timezone_name: str) -> datetime:
    """Attach the roster timezone to naive values; preserve aware instants."""
    zone = ZoneInfo(timezone_name)
    return value.replace(tzinfo=zone) if value.tzinfo is None else value.astimezone(zone)


def build_calendar_service(
    client_secret_path: Path | str = "credentials.json",
    token_path: Path | str = "token.json",
    *,
    scopes: Sequence[str] = SCOPES,
) -> Any:
    """Authenticate a desktop user and return a Google Calendar API service.

    ``client_secret_path`` is the Desktop OAuth client JSON downloaded from a
    Google Cloud project with the Calendar API enabled. The first call opens a
    browser consent flow; refreshable credentials are stored at ``token_path``.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Google Calendar dependencies are missing. Run: python -m pip install -r requirements.txt"
        ) from exc

    secret_file = Path(client_secret_path)
    saved_token = Path(token_path)
    if not secret_file.is_file():
        raise FileNotFoundError(
            f"Google OAuth client credentials were not found: {secret_file}. "
            "Create a Desktop OAuth client in Google Cloud and download its JSON file."
        )

    credentials = None
    if saved_token.is_file():
        credentials = Credentials.from_authorized_user_file(str(saved_token), scopes)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), scopes)
            credentials = flow.run_local_server(port=0)
        saved_token.parent.mkdir(parents=True, exist_ok=True)
        saved_token.write_text(credentials.to_json(), encoding="utf-8")

    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def list_calendars(service: Any) -> list[dict[str, Any]]:
    """Return calendars available to the signed-in user."""
    calendars: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        response = service.calendarList().list(pageToken=page_token).execute()
        calendars.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return calendars


def find_event_by_source_id(service: Any, calendar_id: str, source_id: str) -> dict[str, Any] | None:
    """Find the event previously synchronized from this local source ID."""
    response = service.events().list(
        calendarId=calendar_id,
        privateExtendedProperty=f"{SOURCE_PROPERTY}={source_id}",
        maxResults=1,
    ).execute()
    events = response.get("items", [])
    return events[0] if events else None


def upsert_event(service: Any, calendar_id: str, event: CalendarEvent) -> SyncResult:
    """Create an event, or update the earlier event with the same source ID."""
    body = event.to_google_resource()
    existing = find_event_by_source_id(service, calendar_id, event.source_id)
    if existing:
        response = service.events().update(
            calendarId=calendar_id,
            eventId=existing["id"],
            body=body,
            sendUpdates="none",
        ).execute()
        action = "updated"
    else:
        response = service.events().insert(
            calendarId=calendar_id,
            body=body,
            sendUpdates="none",
        ).execute()
        action = "created"
    return SyncResult(event.source_id, response["id"], action, response.get("htmlLink"))


def sync_events(service: Any, calendar_id: str, events: Iterable[CalendarEvent]) -> list[SyncResult]:
    """Synchronize reviewed events in order and return each outcome.

    This intentionally performs no deletion. A future review UI should ask for
    explicit confirmation before removing events from a user's calendar.
    """
    return [upsert_event(service, calendar_id, event) for event in events]


def delete_event_by_source_id(service: Any, calendar_id: str, source_id: str) -> bool:
    """Delete one synchronized event; intended for a confirmed user action."""
    existing = find_event_by_source_id(service, calendar_id, source_id)
    if not existing:
        return False
    service.events().delete(calendarId=calendar_id, eventId=existing["id"], sendUpdates="none").execute()
    return True
