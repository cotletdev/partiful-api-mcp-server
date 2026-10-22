"""Event edits as the web app makes them (recorded 21.10.2026): a Firestore update of `events/{eventId}` with
`updatedBy`, and the location through the callable `setEventLocation`, which keeps it out of that update.

Guest Approval and a guest limit exclude each other: turning approval on clears `maxCapacity` and the
waitlist, and the first guest limit turns the waitlist on, as the settings panel does.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.partiful import firestore
from partiful_api_mcp.partiful.client import call, id_token
from partiful_api_mcp.partiful.events import moment, zone

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

# The inputs create_event and update_event share; create_event requires title and start_at.
FIELDS: dict[str, Any] = {
    "title": {"type": "string", "minLength": 1, "maxLength": 200, "description": "Event title."},
    "start_at": {
        "type": "string",
        "description": "Start, ISO 8601. Without an offset it is read in the event's time zone.",
    },
    "end_at": {"type": "string", "description": "End, ISO 8601. Optional; must be after start_at."},
    "timezone": {"type": "string", "description": "IANA zone the event is shown in, e.g. America/New_York."},
    "location": {"type": "string", "maxLength": 300, "description": "Address, place name or link."},
    "description": {"type": "string", "maxLength": 5000, "description": "Event details shown on the page."},
    "rsvp_deadline": {"type": "string", "description": "Last moment guests can RSVP, ISO 8601."},
    "max_guests": {
        "type": ["integer", "null"],
        "minimum": 1,
        "description": "Guest limit; RSVPs over it go to the waitlist. null removes the limit.",
    },
    "guest_approval": {
        "type": "boolean",
        "description": "Guests ask to join and you approve them (Guest Approval). Clears max_guests.",
    },
    "questions": {
        "type": "array",
        "items": {"type": "string", "minLength": 1, "maxLength": 200},
        "maxItems": 10,
        "description": "Guest Questionnaire, short-answer questions asked at RSVP. An empty list turns it off.",
    },
}


async def apply(ctx: ToolContext, event_id: str, old: dict[str, Any], args: dict[str, Any]) -> list[str]:
    """Writes the given inputs to the event `old` (getEventInfo's event); returns the input names changed."""
    uid, _ = await id_token(ctx)
    tz_name = args.get("timezone") or old.get("timezone") or ctx.profile.timezone
    tz = zone(tz_name)
    changes: dict[str, Any] = {}
    remove: list[str] = []
    append: dict[str, list[Any]] = {}
    if "timezone" in args:
        changes["timezone"] = tz.key
    for name, field in (("title", "title"), ("description", "description")):
        if name in args:
            changes[field] = args[name].strip() if name == "title" else args[name]
    start = moment(args["start_at"], tz, "start_at") if args.get("start_at") else _stored(old.get("startDate"))
    end = moment(args["end_at"], tz, "end_at") if args.get("end_at") else _stored(old.get("endDate"))
    if args.get("start_at"):
        changes["startDate"] = start
    if args.get("end_at"):
        changes["endDate"] = end
    if start and end and end <= start and (args.get("start_at") or args.get("end_at")):
        raise ToolError("end_at must be after start_at.", ErrorCode.INVALID_INPUT)
    if args.get("rsvp_deadline"):
        changes["rsvpDeadline"] = moment(args["rsvp_deadline"], tz, "rsvp_deadline")
    approval = args.get("guest_approval")
    if approval is True and args.get("max_guests") is not None:
        raise ToolError("Guest Approval events have no guest limit: give one of the two.", ErrorCode.INVALID_INPUT)
    if approval is not None:
        changes["guestAction"] = "APPLY" if approval else "RSVP"
        if approval:
            remove.append("maxCapacity")
            changes["enableWaitlist"] = False
    if "max_guests" in args:
        if old.get("guestAction") == "APPLY" and approval is not False and args["max_guests"] is not None:
            raise ToolError("This event uses Guest Approval, which has no guest limit.", ErrorCode.INVALID_INPUT)
        if args["max_guests"] is None:
            remove.append("maxCapacity")
            changes["enableWaitlist"] = False
        else:
            changes["maxCapacity"] = args["max_guests"]
            if old.get("maxCapacity") is None:
                changes["enableWaitlist"] = True
    if "questions" in args:
        if args["questions"]:
            base = int(time.time() * 1000)
            version = {
                "questions": [
                    {"id": str(base + i), "text": text.strip(), "required": False, "type": "short_answer"}
                    for i, text in enumerate(args["questions"])
                ],
                "createdAt": datetime.now(UTC),
                "createdBy": firestore.Ref(f"users/{uid}"),
            }
            append["questionnaireVersions"] = [version]
            changes["questionnaireEnabled"] = True
        else:
            changes["questionnaireEnabled"] = False
    if changes or remove or append:
        changes["updatedBy"] = firestore.Ref(f"users/{uid}")
        await firestore.update(ctx, f"events/{event_id}", changes, tuple(remove), append)
    if "location" in args:
        await call(
            ctx,
            "setEventLocation",
            {"eventId": event_id, "locationInfo": {"type": "freeform", "value": args["location"].strip()}},
        )
    return [name for name in FIELDS if name in args]


def _stored(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value[:1].isdigit():
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
