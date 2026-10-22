#!/usr/bin/env python3
"""List the people you can invite through Partiful: your past guests and mutuals, with shared events.

    python list_past_guests.py
    python list_past_guests.py --not-on hK3vQ9xLm2Pa7RtYc4Wd --out to-invite.csv
    python list_past_guests.py --query maya

The user_id column is what invite_guests takes.
"""

import argparse

from partiful_api_mcp.scripting import paginate, run, write_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--not-on", help="Leave out people already on this event (event_id)")
    parser.add_argument("--query", help="Only names containing this text")
    parser.add_argument("--out", help="Save to .csv or .json instead of printing")
    args = parser.parse_args()

    params = {"not_on_event_id": args.not_on, "query": args.query, "limit": 200}
    rows = []
    for person in paginate("list_past_guests", params, "people"):
        last = person.pop("last_shared_event", None) or {}
        rows.append({**person, "last_shared_event": last.get("title")})
    write_rows(rows, args.out)


if __name__ == "__main__":
    run(main)
