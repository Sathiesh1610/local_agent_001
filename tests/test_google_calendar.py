from datetime import date, datetime

import pytest

from src.google_calendar import CalendarEvent, SOURCE_PROPERTY, upsert_event


def test_all_day_event_becomes_google_date_resource() -> None:
    event = CalendarEvent("july-01-off", "Off", date(2026, 7, 1), date(2026, 7, 2))

    resource = event.to_google_resource()

    assert resource["start"] == {"date": "2026-07-01"}
    assert resource["end"] == {"date": "2026-07-02"}
    assert resource["extendedProperties"]["private"][SOURCE_PROPERTY] == "july-01-off"


def test_timed_event_uses_roster_timezone() -> None:
    event = CalendarEvent(
        "july-01-s1", "S1", datetime(2026, 7, 1, 6), datetime(2026, 7, 1, 15, 30)
    )

    resource = event.to_google_resource()

    assert resource["start"]["dateTime"] == "2026-07-01T06:00:00+05:30"
    assert resource["end"]["dateTime"] == "2026-07-01T15:30:00+05:30"


def test_event_rejects_zero_length_range() -> None:
    with pytest.raises(ValueError, match="later"):
        CalendarEvent("bad", "Off", date(2026, 7, 1), date(2026, 7, 1))


class _Request:
    def __init__(self, response: dict) -> None:
        self.response = response

    def execute(self) -> dict:
        return self.response


class _Events:
    def __init__(self, existing: dict | None) -> None:
        self.existing = existing
        self.calls: list[tuple[str, dict]] = []

    def list(self, **kwargs):
        self.calls.append(("list", kwargs))
        return _Request({"items": [self.existing] if self.existing else []})

    def insert(self, **kwargs):
        self.calls.append(("insert", kwargs))
        return _Request({"id": "created-id"})

    def update(self, **kwargs):
        self.calls.append(("update", kwargs))
        return _Request({"id": kwargs["eventId"]})


class _Service:
    def __init__(self, existing: dict | None) -> None:
        self.events_resource = _Events(existing)

    def events(self) -> _Events:
        return self.events_resource


def test_upsert_creates_when_source_id_is_new() -> None:
    service = _Service(existing=None)
    event = CalendarEvent("july-01-s1", "S1", date(2026, 7, 1), date(2026, 7, 2))

    result = upsert_event(service, "primary", event)

    assert result.action == "created"
    assert [call[0] for call in service.events_resource.calls] == ["list", "insert"]


def test_upsert_updates_when_source_id_exists() -> None:
    service = _Service(existing={"id": "existing-id"})
    event = CalendarEvent("july-01-s1", "S1", date(2026, 7, 1), date(2026, 7, 2))

    result = upsert_event(service, "primary", event)

    assert result.action == "updated"
    assert result.google_event_id == "existing-id"
    assert [call[0] for call in service.events_resource.calls] == ["list", "update"]
