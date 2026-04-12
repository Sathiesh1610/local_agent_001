"""Local agent entry point for roster and calendar utilities."""

from __future__ import annotations


def run_agent() -> None:
    """Print a short startup message for the local agent."""
    print("Roster agent ready.")
    print("Use src/roster_to_ics.py to convert roster Excel files into .ics exports.")


if __name__ == "__main__":
    run_agent()
