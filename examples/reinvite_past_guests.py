#!/usr/bin/env python3
"""Copy the last edition of a recurring event to a new date and invite the people who were going to it.

    python reinvite_past_guests.py --event hK3vQ9xLm2Pa7RtYc4Wd --start 2026-11-14T19:00 --dry-run
    python reinvite_past_guests.py --event hK3vQ9xLm2Pa7RtYc4Wd --start 2026-11-14T19:00 --checked-in-only

The copy keeps settings and questionnaire. Partiful does not copy the RSVP deadline, so set a new one with
update_event if you had one. Only guests with a Partiful account can be re-invited this way.
Invites reach people at once: run with --dry-run first.
"""

import argparse

from partiful_api_mcp.scripting import call, paginate, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", required=True, help="event_id of the edition to copy")
    parser.add_argument("--start", required=True, help="Start of the new edition, ISO 8601, in the event's time zone")
    parser.add_argument("--title", help="Title of the copy. Default: the same")
    parser.add_argument("--checked-in-only", action="store_true", help="Only guests who were checked in")
    parser.add_argument("--dry-run", action="store_true", help="Only show the list, copy nothing")
    args = parser.parse_args()

    params = {"event_id": args.event, "status": "going", "limit": 200}
    if args.checked_in_only:
        params["checked_in"] = True
    guests = [g for g in paginate("list_guests", params, "guests") if g.get("user_id")]
    print(f"{len(guests)} guests to re-invite: {', '.join(g['name'] for g in guests)}")
    if args.dry_run:
        return

    copy = call("duplicate_event", {"event_id": args.event, "start_at": args.start, "title": args.title})
    print(f"New event {copy['title']} on {copy['start_at']}: {copy['url']}")
    # People already on the copy (the hosts) come back from list_past_guests as excluded, so ask it who is left.
    wanted = {g["user_id"] for g in guests}
    invitable = paginate("list_past_guests", {"not_on_event_id": copy["event_id"], "limit": 200}, "people")
    user_ids = [p["user_id"] for p in invitable if p["user_id"] in wanted]
    if not user_ids:
        print("Nobody left to invite.")
        return
    result = call("invite_guests", {"event_id": copy["event_id"], "user_ids": user_ids})
    print(f"Invited {result['invited']}, {result['invited_total']} invited in total")


if __name__ == "__main__":
    run(main)
