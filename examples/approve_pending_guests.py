#!/usr/bin/env python3
"""Approve pending guests of a Guest Approval event whose questionnaire answers contain your keywords.

    python approve_pending_guests.py --event hK3vQ9xLm2Pa7RtYc4Wd --match inc --match llc --dry-run
    python approve_pending_guests.py --event hK3vQ9xLm2Pa7RtYc4Wd --all --max 20

Guests who do not match stay Pending: nobody is rejected. Partiful tells each approved guest, so run with
--dry-run first. --max keeps you to your head count.
"""

import argparse

from partiful_api_mcp.scripting import call, paginate, run


def matches(guest: dict, keywords: list[str]) -> bool:
    text = " ".join(str(a.get("answer", "")) for a in guest.get("answers") or []).lower()
    return any(k.lower() in text for k in keywords)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", required=True, help="event_id from list_events.py")
    parser.add_argument("--match", action="append", default=[], help="Approve if an answer contains this (repeatable)")
    parser.add_argument("--all", action="store_true", help="Approve everyone pending")
    parser.add_argument("--max", type=int, help="Approve at most this many")
    parser.add_argument("--dry-run", action="store_true", help="Only show who would be approved")
    args = parser.parse_args()
    if not args.all and not args.match:
        parser.error("pass --match WORD (one or more) or --all")

    pending = list(paginate("list_guests", {"event_id": args.event, "status": "pending", "limit": 200}, "guests"))
    chosen = [g for g in pending if args.all or matches(g, args.match)][: args.max]
    print(f"{len(pending)} pending, {len(chosen)} to approve")
    for guest in pending:
        mark = "approve" if guest in chosen else "keep   "
        answers = "; ".join(f"{a['question']}: {a['answer']}" for a in guest.get("answers") or [])
        print(f"  {mark} {guest['name']}  {answers}")
    if args.dry_run or not chosen:
        return
    result = call("approve_guests", {"event_id": args.event, "guest_ids": [g["guest_id"] for g in chosen]})
    print(result)


if __name__ == "__main__":
    run(main)
