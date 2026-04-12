"""Google Calendar integration stubs for the roster agent."""

from __future__ import annotations


def sync_to_google_calendar(*, roster_path: str, credentials_path: str) -> None:
    """Placeholder for Google Calendar sync.

    This repository currently supports generating an .ics export from roster Excel files.
    Google Calendar syncing can be added later using the Google Calendar API.
    """
    raise NotImplementedError(
        "Google Calendar sync is not implemented yet. Use roster_to_ics.generate_ics_from_excel() instead."
    )
