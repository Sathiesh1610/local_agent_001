"""Tests for roster to .ics export functionality."""

from pathlib import Path
from datetime import date

import pandas as pd

from src.roster_to_ics import SHIFT_MAPPINGS, build_event_from_shift, generate_ics_from_excel


def test_generate_ics_from_excel(tmp_path: Path) -> None:
    sample_file = tmp_path / "sample_roster.xlsx"
    output_file = tmp_path / "generated_calendar.ics"

    data = {
        "Date": ["2026-04-14"],
        "Start": ["08:00"],
        "End": ["16:00"],
        "Summary": ["Test Shift"],
        "Description": ["Unit test roster entry."],
        "Location": ["Office"],
    }
    df = pd.DataFrame(data)
    df.to_excel(sample_file, index=False)

    result_path = generate_ics_from_excel(sample_file, output_file)
    assert result_path.exists()

    content = result_path.read_text(encoding="utf-8")
    assert "BEGIN:VCALENDAR" in content
    assert "END:VCALENDAR" in content
    assert "SUMMARY:Test Shift" in content
    assert "LOCATION:Office" in content


def test_off_day_description_groups() -> None:
    event = build_event_from_shift(
        event_date=date(2026, 7, 1),
        shift_info=SHIFT_MAPPINGS["OFF"],
        person="Sathiesh M",
        description="",
        all_shifts={
            "Sathiesh M": ["OFF"],
            "Anita": ["S1"],
            "Bala": ["S2"],
            "Chandru": ["EVE"],
            "Deepa": ["S3"],
        },
        date_index=0,
        all_names=["Sathiesh M", "Anita", "Bala", "Chandru", "Deepa"],
    )

    assert "SUMMARY:Off" in event
    assert "Colleagues in shift S1:" in event
    assert "- Anita" in event
    assert "Colleagues in shift S2:" in event
    assert "- Bala" in event
    assert "Colleagues in shift EVE:" in event
    assert "- Chandru" in event
    assert "Colleagues in shift S3:" in event
    assert "- Deepa" in event
