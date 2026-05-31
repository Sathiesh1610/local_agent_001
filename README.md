# local_agent_001

A local agent scaffold for roster processing and calendar export.

## What is included

- `src/` for application code
- `tests/` for unit tests
- `samples/` for roster input and .ics output examples
- `.gitignore` for Python and VS Code files
- `requirements.txt` for dependencies

## Roster workflow

1. Place a roster file in `roster/` or `samples/`.
2. Run `python src/roster_to_ics.py <roster.xlsx> <output.ics>` to generate a calendar export.
3. For a single person output, add `--person "Sathiesh M"`.
4. Alternatively use the local agent REPL: `python src/local_agent.py`, then type `Generate Roster <input> <output> --person "Sathiesh M"`.
5. Optionally list sheets in a workbook with `python src/roster_to_ics.py --list-sheets roster/Roster-June 26_UPD.xlsx`.
6. Import the generated `.ics` file into Google Calendar or another calendar app.

## Supported roster formats

- **Matrix format** (like Roster-April 26_UPD.xlsx): People as rows, dates as columns, shift codes in cells.
- **Event format** (like sample_roster.xlsx): Each row is an event with date, start, end, summary columns.

Shift codes are mapped to times (S1=06:00-15:30, S2=14:00-23:30, S3=22:00-07:30, EVE=17:00-02:30, G=09:00-18:30, OFF=all day, etc.).

## Features

- **Detailed descriptions**: Includes colleagues in same shift, previous/next shift transitions, and G/EVE colleagues.
- **Timezone support**: Events use Asia/Kolkata timezone.
- **Color coding**: OFF days get green color in Google Calendar.
- **Person filtering**: Generate calendar for specific team members only.
- **Example output**: `samples/sathiesh_m.ics` is generated for `Sathiesh M`.

## Next steps

1. Open this workspace in VS Code.
2. Create or activate a Python environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run tests with `pytest`.

## Run in VS Code

- Use **Terminal > Run Task...** and choose `Run roster-to-ics` to generate `samples/run_output.ics`.
- Use **Run and Debug** and select `Python: Run roster_to_ics` to execute the main conversion inside VS Code.
