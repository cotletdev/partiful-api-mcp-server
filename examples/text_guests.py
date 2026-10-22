#!/usr/bin/env python3
"""Send a Text Blast to an event's guests by RSVP status, after showing how many people it reaches.

    python text_guests.py --event hK3vQ9xLm2Pa7RtYc4Wd --to going --to maybe --message "Door code is 4512" --dry-run
    python text_guests.py --event hK3vQ9xLm2Pa7RtYc4Wd --to invited --message "Please RSVP by Friday"

Partiful allows 10 blasts per event and does not say how many are left, so merge updates into one message.
A blast to Invited works only up to 100 people. A sent blast cannot be pulled back: run with --dry-run first.
"""

import argparse

from partiful_api_mcp.scripting import call, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", required=True, help="event_id from list_events.py")
    parser.add_argument(
        "--to",
        action="append",
        required=True,
        choices=["going", "maybe", "cant_go", "invited", "waitlist", "pending"],
        help="RSVP status that gets the text (repeatable)",
    )
    parser.add_argument("--message", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Only show who would get it")
    parser.add_argument("--yes", action="store_true", help="Send without asking")
    args = parser.parse_args()

    event = call("get_event", {"event_id": args.event})
    counts = event.get("guests") or {}
    reach = {status: counts.get(status, 0) for status in args.to}
    print(f"{event['title']}: {sum(reach.values())} guests ({', '.join(f'{s} {n}' for s, n in reach.items())})")
    print(f"Message: {args.message}")
    if args.dry_run:
        return
    if not args.yes and input("Send this Text Blast? [y/N] ").strip().lower() != "y":
        print("Not sent.")
        return
    result = call("send_text_blast", {"event_id": args.event, "message": args.message, "statuses": args.to})
    print(f"Sent to {result['recipients']} guests: {result['by_status']}")


if __name__ == "__main__":
    run(main)
