# local_agent_001

A local agent scaffold for roster processing and calendar export.

## What is included

- `src/` for application code
- `tests/` for unit tests
- `samples/` for roster input and .ics output examples
- `.gitignore` for Python and VS Code files
- `requirements.txt` for dependencies

## Roster workflow

1. Place a sample roster file in `samples/` (supports both row-per-event and matrix formats).
2. Run `python src/roster_to_ics.py <roster.xlsx> <output.ics>` to generate .ics.
3. Optionally filter to a person: `python src/roster_to_ics.py <roster.xlsx> <output.ics> --person "Sathiesh M"`.
4. Import the generated `.ics` file into Google Calendar or another calendar app.

## Supported roster formats

- **Matrix format** (like Roster-April 26_UPD.xlsx): People as rows, dates as columns, shift codes in cells.
- **Event format** (like sample_roster.xlsx): Each row is an event with date, start, end, summary columns.

Shift codes are mapped to times (S1=06:00-15:30, S2=14:00-23:30, S3=22:00-07:30, EVE=17:00-02:30, G=09:00-18:30, OFF=all day, etc.).

## Features

- **Detailed descriptions**: Includes colleagues in same shift, previous/next shift transitions, and G/EVE colleagues.
- **Timezone support**: Events use Asia/Kolkata timezone.
- **Color coding**: OFF days get green color in Google Calendar.
- **Person filtering**: Generate calendar for specific team members only.

## Next steps

1. Open this workspace in VS Code.
2. Create or activate a Python environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run tests with `pytest`.
