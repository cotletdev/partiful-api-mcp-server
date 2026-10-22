#!/usr/bin/env python3
"""Export guests of one or more events as rows for a spreadsheet, one column per questionnaire question.

    python export_rsvps.py --event hK3vQ9xLm2Pa7RtYc4Wd --status going --out supper-club.csv
    python export_rsvps.py --event EVENT_A --event EVENT_B --out season.csv

Each row has the event, name, status, plus-ones, check-in and RSVP time. Import the CSV into Google Sheets
or Excel, or append it to the sheet you keep.
"""

import argparse

from partiful_api_mcp.scripting import call, paginate, run, write_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", action="append", required=True, help="event_id from list_events.py (repeatable)")
    parser.add_argument(
        "--status", choices=["all", "going", "maybe", "cant_go", "invited", "waitlist", "pending"], default="all"
    )
    parser.add_argument("--out", help="Save to .csv or .json instead of printing")
    args = parser.parse_args()

    rows = []
    for event_id in args.event:
        title = call("get_event", {"event_id": event_id})["title"]
        params = {"event_id": event_id, "status": args.status, "limit": 200}
        for guest in paginate("list_guests", params, "guests"):
            row = {
                "event": title,
                "name": guest["name"],
                "status": guest["status"],
                "count": guest.get("count"),
                "plus_ones": ", ".join(guest.get("plus_ones") or []),
                "checked_in": guest.get("checked_in"),
                "rsvp_at": guest.get("rsvp_at"),
            }
            for answer in guest.get("answers") or []:
                row[answer["question"]] = answer["answer"]
            rows.append(row)
    write_rows(rows, args.out)


if __name__ == "__main__":
    run(main)
