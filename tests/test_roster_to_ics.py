"""Tests for roster to .ics export functionality."""

from pathlib import Path

import pandas as pd

from src.roster_to_ics import generate_ics_from_excel


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
