#!/usr/bin/env python3
"""Sum up the Guest Questionnaire answers of an event: each answer with how many guests gave it and who.

    python questionnaire_summary.py --event hK3vQ9xLm2Pa7RtYc4Wd
    python questionnaire_summary.py --event hK3vQ9xLm2Pa7RtYc4Wd --question "Dietary restrictions"

Counts going guests by default, with their plus-ones. Guests who RSVP'd before a question existed are listed
as having no answer, so you know whom to ask.
"""

import argparse
from collections import defaultdict

from partiful_api_mcp.scripting import paginate, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", required=True, help="event_id from list_events.py")
    parser.add_argument("--status", default="going", choices=["all", "going", "maybe", "waitlist", "pending"])
    parser.add_argument("--question", help="Only this question (exact text)")
    args = parser.parse_args()

    guests = list(paginate("list_guests", {"event_id": args.event, "status": args.status, "limit": 200}, "guests"))
    questions: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for guest in guests:
        for answer in guest.get("answers") or []:
            text = " ".join(str(answer["answer"]).split()).lower() or "(blank)"
            questions[answer["question"]][text].append(guest["name"])
    head_count = sum(g.get("count") or 1 for g in guests)
    print(f"{len(guests)} guests ({head_count} with plus-ones), status {args.status}")
    for question, answers in questions.items():
        if args.question and question != args.question:
            continue
        answered = {name for names in answers.values() for name in names}
        print(f"\n{question}")
        for text, names in sorted(answers.items(), key=lambda item: -len(item[1])):
            print(f"  {len(names):>3}  {text}: {', '.join(names)}")
        missing = [g["name"] for g in guests if g["name"] not in answered]
        if missing:
            print(f"  no answer: {', '.join(missing)}")


if __name__ == "__main__":
    run(main)
