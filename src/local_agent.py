"""Local agent entry point for roster and calendar utilities.

This script runs a tiny interactive loop. When you type the command
"Generate Roster" (optionally followed by arguments) the agent will
invoke `src/roster_to_ics.py` to produce an .ics file.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path


def run_agent() -> None:
    """Run a small REPL that accepts commands.

    Supported commands:
    - Generate Roster [args...] : runs src/roster_to_ics.py with the provided args
    - exit / quit              : leave the REPL
    If no args are supplied to `Generate Roster`, the REPL will prompt
    for an input and output path.
    """
    print("Roster agent ready.")
    print("Type 'Generate Roster <input> <output> [--sheet NAME] [--person NAME]' or 'exit'.")

    # If stdin is not interactive, do not enter the REPL.
    if not sys.stdin.isatty():
        print("No interactive stdin available; exiting local agent.")
        return

    # Resolve the roster conversion script relative to this module.
    script_path = Path(__file__).with_name("roster_to_ics.py")

    try:
        while True:
            try:
                line = input("agent> ").strip()
            except EOFError:
                break

            if not line:
                continue

            lowered = line.lower()
            if lowered in ("exit", "quit"):
                print("Exiting agent.")
                break

            if lowered.startswith("generate roster"):
                # Extract the arguments after the command
                rest = line[len("generate roster"):].strip()
                args = shlex.split(rest) if rest else []

                if len(args) < 2:
                    # Prompt for missing paths
                    input_path = input("Input roster file path: ").strip()
                    output_path = input("Output .ics file path: ").strip()
                    if not input_path or not output_path:
                        print("Input and output paths are required.")
                        continue
                    cmd = [sys.executable, str(script_path), input_path, output_path] + args
                else:
                    cmd = [sys.executable, str(script_path)] + args

                print(f"Running: {' '.join(cmd)}")
                try:
                    completed = subprocess.run(cmd)
                    if completed.returncode == 0:
                        print("Roster generation completed.")
                    else:
                        print(f"Roster generator exited with code {completed.returncode}.")
                except Exception as exc:
                    print(f"Failed to run roster generator: {exc}")
                continue

            print("Unknown command. Try 'Generate Roster' or 'exit'.")
    except KeyboardInterrupt:
        print("\nAgent interrupted; exiting.")


if __name__ == "__main__":
    run_agent()
