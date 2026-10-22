#!/usr/bin/env python3
"""Save an event's guest list as the same CSV file the Export CSV button gives: name, status, RSVP date, answers.

    python export_guest_list.py --event hK3vQ9xLm2Pa7RtYc4Wd
    python export_guest_list.py --event hK3vQ9xLm2Pa7RtYc4Wd --status going --status maybe --out rsvps.csv

Phone numbers and emails are not in the file, as in Partiful's own export.
"""

import argparse
import sys
from pathlib import Path

from partiful_api_mcp.scripting import call, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", required=True, help="event_id from list_events.py")
    parser.add_argument(
        "--status",
        action="append",
        choices=["going", "maybe", "cant_go", "invited", "waitlist", "pending"],
        help="Only these RSVP statuses (repeatable). Default: all",
    )
    parser.add_argument("--out", help="File name. Default: the name Partiful gives the export")
    args = parser.parse_args()

    result = call("export_guest_list", {"event_id": args.event, "statuses": args.status})
    path = Path(args.out or result["filename"])
    path.write_text(result["csv"], encoding="utf-8")
    print(f"Saved {result['rows']} guests to {path}", file=sys.stderr)


if __name__ == "__main__":
    run(main)
