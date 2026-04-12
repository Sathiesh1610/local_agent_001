"""Convert roster Excel files into calendar .ics exports."""

from __future__ import annotations

import argparse
import uuid
from datetime import datetime, date, time, timezone, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from dateutil import parser as dateutil_parser

DEFAULT_COLUMNS = {
    "date": ["date", "work date", "shift date"],
    "start": ["start", "start time", "from"],
    "end": ["end", "end time", "to"],
    "summary": ["summary", "title", "shift", "event"],
    "description": ["description", "notes", "details"],
    "location": ["location", "venue", "site"],
}

SHIFT_MAPPINGS = {
    "S1": {"start": "06:00", "end": "15:30", "summary": "S1 (06:00–15:30)"},
    "S2": {"start": "14:00", "end": "23:30", "summary": "S2 (14:00–23:30)"},
    "S3": {"start": "22:00", "end": "07:30", "summary": "S3 (22:00–07:30)"},  # Next day end
    "EVE": {"start": "17:00", "end": "02:30", "summary": "EVE (17:00–02:30)"},  # Next day end
    "G": {"start": "09:00", "end": "18:30", "summary": "G (09:00–18:30)"},
    "OFF": {"all_day": True, "summary": "Off", "color": "#33B679"},
    "L": {"all_day": True, "summary": "Leave"},
    "PH": {"all_day": True, "summary": "Public Holiday"},
    "AL": {"all_day": True, "summary": "Annual Leave"},
}


def normalize_header(value: str) -> str:
    return str(value).strip().lower()


def find_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = [normalize_header(value) for value in columns]
    for candidate in candidates:
        if normalize_header(candidate) in normalized:
            return columns[normalized.index(normalize_header(candidate))]
    return None


def get_columns(frame: pd.DataFrame) -> dict[str, str | None]:
    columns = list(frame.columns)
    return {key: find_column(columns, candidates) for key, candidates in DEFAULT_COLUMNS.items()}


def parse_date(value: Any) -> date | None:
    if pd.isna(value):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    parsed = dateutil_parser.parse(str(value), dayfirst=False)
    return parsed.date()


def parse_time(value: Any) -> time | None:
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    parsed = dateutil_parser.parse(str(value))
    return parsed.time()


def format_ics_datetime(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
        return value.strftime("%Y%m%dT%H%M%SZ")
    return value.strftime("%Y%m%dT%H%M%S")


def format_ics_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def build_event(row: pd.Series, mapping: dict[str, str | None]) -> str:
    event_date = parse_date(row[mapping["date"]]) if mapping["date"] else None
    if event_date is None:
        raise ValueError("Roster row is missing a valid date value.")

    start_time = parse_time(row[mapping["start"]]) if mapping["start"] else None
    end_time = parse_time(row[mapping["end"]]) if mapping["end"] else None
    summary = str(row[mapping["summary"]]).strip() if mapping["summary"] and not pd.isna(row[mapping["summary"]]) else "Roster Shift"
    description = str(row[mapping["description"]]).strip() if mapping["description"] and not pd.isna(row[mapping["description"]]) else ""
    location = str(row[mapping["location"]]).strip() if mapping["location"] and not pd.isna(row[mapping["location"]]) else ""

    uid = uuid.uuid4().hex
    dtstamp = format_ics_datetime(datetime.now(timezone.utc))

    if start_time and end_time:
        dtstart = format_ics_datetime(datetime.combine(event_date, start_time))
        dtend = format_ics_datetime(datetime.combine(event_date, end_time))
        dtstart_line = f"DTSTART:{dtstart}"
        dtend_line = f"DTEND:{dtend}"
    else:
        dtstart_line = f"DTSTART;VALUE=DATE:{format_ics_date(event_date)}"
        dtend_line = f"DTEND;VALUE=DATE:{format_ics_date(event_date)}"

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        dtstart_line,
        dtend_line,
        f"SUMMARY:{summary}",
    ]

    if description:
        lines.append(f"DESCRIPTION:{description}")
    if location:
        lines.append(f"LOCATION:{location}")

    lines.extend(["END:VEVENT"])
    return "\r\n".join(lines)


def generate_ics_from_excel(
    input_path: Path | str,
    output_path: Path | str,
    sheet_name: str | None = None,
) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)

    frame = pd.read_excel(input_path, sheet_name=sheet_name, engine="openpyxl")
    if isinstance(frame, dict):
        if not frame:
            raise ValueError("The roster file contains no sheets.")
        frame = next(iter(frame.values()))

    if frame.empty:
        raise ValueError("The roster file contains no rows.")

    mapping = get_columns(frame)
    if mapping["date"] is None:
        raise ValueError("Could not find a date column in the roster file.")

    events = [build_event(row, mapping) for _, row in frame.iterrows()]
    calendar_text = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//local_agent_001//Roster ICS Export//EN\r\n"
    calendar_text += "\r\n".join(events)
    calendar_text += "\r\nEND:VCALENDAR\r\n"

    output_path.write_text(calendar_text, encoding="utf-8")
    return output_path


def generate_ics_from_roster_matrix(
    input_path: Path | str,
    output_path: Path | str,
    person_name: str | None = None,
) -> Path:
    """Generate .ics from roster matrix format (people x dates)."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    frame = pd.read_excel(input_path, engine="openpyxl")
    if isinstance(frame, dict):
        if not frame:
            raise ValueError("The roster file contains no sheets.")
        frame = next(iter(frame.values()))

    if frame.empty:
        raise ValueError("The roster file contains no rows.")

    # Assume first column is 'Date' or names, but actually it's pivoted
    # Columns after first are dates, rows after first few are people
    # Skip header rows: Day, Offshore Team, etc.
    # Find the row where names start
    name_col = frame.columns[0]
    names_start_idx = None
    for idx, row in frame.iterrows():
        if pd.notna(row[name_col]) and row[name_col] not in ['Date', 'Day', 'Offshore Team']:
            names_start_idx = idx
            break

    if names_start_idx is None:
        raise ValueError("Could not find person names in roster.")

    # Extract people rows
    people_df = frame.iloc[names_start_idx:].copy()
    people_df.columns = frame.columns  # Keep original columns

    # Collect all shift data for better descriptions
    all_shifts = {}
    all_names = []
    for _, person_row in people_df.iterrows():
        person_name_val = person_row[name_col]
        if pd.isna(person_name_val) or person_name_val in ['Date', 'Day']:
            continue
        all_names.append(person_name_val)
        shifts_list = []
        for col in people_df.columns[1:]:  # Skip name column
            if isinstance(col, str) and col.startswith('Unnamed'):
                continue
            shift_code = person_row[col]
            shifts_list.append(str(shift_code).strip().upper() if not pd.isna(shift_code) else "")
        all_shifts[person_name_val] = shifts_list

    events = []
    date_columns = [col for col in people_df.columns[1:] if not (isinstance(col, str) and col.startswith('Unnamed'))]

    for person_idx, person_name_val in enumerate(all_names):
        if person_name and person_name.lower() not in str(person_name_val).lower():
            continue  # Filter to specific person if requested

        for date_idx, col in enumerate(date_columns):
            shift_code = all_shifts[person_name_val][date_idx]
            if not shift_code or shift_code not in SHIFT_MAPPINGS:
                continue  # Unknown or empty shift

            shift_info = SHIFT_MAPPINGS[shift_code]
            event_date = parse_date(col) if not isinstance(col, date) else col
            if event_date is None:
                continue

            event = build_event_from_shift(event_date, shift_info, person_name_val, "", all_shifts, date_idx, all_names)
            events.append(event)

    calendar_text = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//local_agent_001//Roster ICS Export//EN\r\n"
    calendar_text += "\r\n".join(events)
    calendar_text += "\r\nEND:VCALENDAR\r\n"

    output_path.write_text(calendar_text, encoding="utf-8")
    return output_path


def build_event_from_shift(event_date: date, shift_info: dict, person: str, description: str, all_shifts: dict[str, list[str]], date_index: int, all_names: list[str]) -> str:
    uid = uuid.uuid4().hex
    dtstamp = format_ics_datetime(datetime.now(timezone.utc))

    if shift_info.get("all_day"):
        dtstart_line = f"DTSTART;VALUE=DATE:{format_ics_date(event_date)}"
        dtend_line = f"DTEND;VALUE=DATE:{format_ics_date(event_date + timedelta(days=1))}"
        summary = shift_info["summary"]
    else:
        start_time = parse_time(shift_info["start"])
        end_time = parse_time(shift_info["end"])
        dtstart = format_ics_datetime(datetime.combine(event_date, start_time))
        dtend = format_ics_datetime(datetime.combine(event_date, end_time))
        # Handle next-day end times for S3 and EVE
        if shift_info.get("summary", "").startswith(("S3", "EVE")):
            dtend = format_ics_datetime(datetime.combine(event_date + timedelta(days=1), end_time))
        dtstart_line = f"DTSTART;TZID=Asia/Kolkata:{dtstart}"
        dtend_line = f"DTEND;TZID=Asia/Kolkata:{dtend}"
        summary = shift_info["summary"]

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        dtstart_line,
        dtend_line,
        f"SUMMARY:{summary}",
    ]

    # Build detailed description like the user's script
    shift_code = None
    for code, info in SHIFT_MAPPINGS.items():
        if info["summary"] == summary:
            shift_code = code
            break

    if shift_code:
        desc_parts = []

        # Colleagues in same shift
        same_shift = []
        g_eve_today = []
        for name in all_names:
            if name == person:
                continue
            today_shift = all_shifts.get(name, [])[date_index] if date_index < len(all_shifts.get(name, [])) else ""
            if today_shift == shift_code:
                same_shift.append(name)
            if today_shift in ("G", "EVE"):
                g_eve_today.append(f"{name} ({today_shift})")

        desc_parts.append("Colleagues in same shift:")
        desc_parts.extend(f"- {n}" for n in same_shift)

        if g_eve_today:
            desc_parts.append("")
            desc_parts.append("Colleagues in G / EVE:")
            desc_parts.extend(f"- {n}" for n in g_eve_today)

        # Previous and next shifts based on rotation
        prev_shift = []
        next_shift = []

        if shift_code == "S1":
            if date_index > 0:
                prev_shift = [name for name in all_names if name != person and all_shifts.get(name, [])[date_index-1] == "S3"]
            next_shift = [name for name in all_names if name != person and all_shifts.get(name, [])[date_index] == "S2"]
        elif shift_code == "S2":
            prev_shift = [name for name in all_names if name != person and all_shifts.get(name, [])[date_index] == "S1"]
            next_shift = [name for name in all_names if name != person and all_shifts.get(name, [])[date_index] == "S3"]
        elif shift_code == "S3":
            prev_shift = [name for name in all_names if name != person and all_shifts.get(name, [])[date_index] == "S2"]
            if date_index < len(all_shifts.get(person, [])) - 1:
                next_shift = [name for name in all_names if name != person and all_shifts.get(name, [])[date_index+1] == "S1"]

        desc_parts.append("")
        desc_parts.append("Previous shift:")
        desc_parts.extend(f"- {n}" for n in prev_shift)

        desc_parts.append("")
        desc_parts.append("Next shift:")
        desc_parts.extend(f"- {n}" for n in next_shift)

        lines.append("DESCRIPTION:" + "\\n".join(desc_parts))
    else:
        # For OFF/L etc., show working colleagues
        working = []
        for name in all_names:
            today_shift = all_shifts.get(name, [])[date_index] if date_index < len(all_shifts.get(name, [])) else ""
            if today_shift in {"S1", "G", "S2", "EVE", "S3"}:
                working.append(f"{name} ({today_shift})")

        desc_parts = ["Working colleagues today:"]
        desc_parts.extend(f"- {w}" for w in working)
        lines.append("DESCRIPTION:" + "\\n".join(desc_parts))

    # Add color for OFF days
    if shift_info.get("color"):
        lines.append(f"COLOR:{shift_info['color']}")
        lines.append(f"X-GOOGLE-CALENDAR-COLOR:{shift_info['color']}")

    lines.extend(["END:VEVENT"])
    return "\r\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a roster Excel file into an importable .ics calendar file.")
    parser.add_argument("input", help="Input roster Excel file path.")
    parser.add_argument("output", help="Output .ics file path.")
    parser.add_argument("--sheet", default=None, help="Optional Excel sheet name.")
    parser.add_argument("--person", default=None, help="Optional person name to filter events for (matrix format only).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # Detect if it's matrix format (columns are dates)
    frame = pd.read_excel(args.input, engine="openpyxl")
    if isinstance(frame, dict):
        frame = next(iter(frame.values()))
    columns = list(frame.columns)
    # If many columns are dates, assume matrix format
    date_columns = [c for c in columns if isinstance(c, date)]
    if len(date_columns) > 10:  # Arbitrary threshold
        result = generate_ics_from_roster_matrix(args.input, args.output, person_name=args.person)
    else:
        result = generate_ics_from_excel(args.input, args.output, sheet_name=args.sheet)
    print(f"Generated calendar file: {result}")


if __name__ == "__main__":
    main()
