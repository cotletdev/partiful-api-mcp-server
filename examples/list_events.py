#!/usr/bin/env python3
"""List the Partiful events you host with date, status and guest counts per RSVP status.

    python list_events.py
    python list_events.py --when past --out past-events.csv

The event_id column is what the other scripts take as --event.
"""

import argparse

from partiful_api_mcp.scripting import paginate, run, write_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--when", choices=["upcoming", "past", "all"], default="upcoming")
    parser.add_argument("--out", help="Save to .csv or .json instead of printing")
    args = parser.parse_args()

    rows = []
    for event in paginate("list_events", {"when": args.when, "limit": 50}, "events"):
        counts = event.pop("guests", {}) or {}
        rows.append({**event, **{f"guests_{status}": n for status, n in counts.items()}})
    write_rows(rows, args.out)


if __name__ == "__main__":
    run(main)
