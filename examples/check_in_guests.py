#!/usr/bin/env python3
"""Check guests in at the door by name, or undo a check-in.

    python check_in_guests.py --event hK3vQ9xLm2Pa7RtYc4Wd --name "Maya Chen" --name "Leo Park"
    python check_in_guests.py --event hK3vQ9xLm2Pa7RtYc4Wd --name "Maya Chen" --undo

A name matches a going guest when it equals the guest's Partiful name, case aside. Two guests with the same
name stop the script, so you pick by guest_id from export_rsvps.py instead.
"""

import argparse
import sys

from partiful_api_mcp.scripting import call, paginate, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", required=True, help="event_id from list_events.py")
    parser.add_argument("--name", action="append", required=True, help="Guest name (repeatable)")
    parser.add_argument("--undo", action="store_true", help="Remove the check-in instead")
    args = parser.parse_args()

    guests = list(paginate("list_guests", {"event_id": args.event, "status": "going", "limit": 200}, "guests"))
    ids = []
    for name in args.name:
        found = [g for g in guests if g["name"].casefold() == name.casefold()]
        if len(found) != 1:
            sys.exit(f"{name}: {len(found)} going guests with this name")
        ids.append(found[0]["guest_id"])
    result = call("check_in_guests", {"event_id": args.event, "guest_ids": ids, "undo": args.undo})
    print(f"Changed {result['changed']}, {result['checked_in_total']} checked in now")


if __name__ == "__main__":
    run(main)
