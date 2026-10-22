"""Create event."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import call
from partiful_api_mcp.partiful.editing import FIELDS, apply
from partiful_api_mcp.partiful.events import detail, event_info, moment, utc_iso, zone
from partiful_api_mcp.partiful.tools.get_event import EXAMPLE_RESPONSE as EVENT

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

# What the create form saves besides the inputs (web app defaults, 21.10.2026).
_DEFAULTS: dict[str, Any] = {
    "showHostList": True,
    "showGuestCount": True,
    "showGuestList": True,
    "showActivityTimestamps": True,
    "displayInviteButton": True,
    "allowGuestPhotoUpload": True,
    "enableGuestReminders": True,
    "rsvpsEnabled": True,
    "allowGuestsToInviteMutuals": True,
}
# Set by createEvent itself; the rest of the inputs go through the same edit as update_event.
_ON_CREATE = ("title", "start_at", "end_at", "timezone", "description")

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        **FIELDS,
        "timezone": {
            "type": "string",
            "description": "IANA zone the event is shown in, e.g. America/New_York. Default: the browser's zone.",
        },
        "visibility": {
            "type": "string",
            "enum": ["private", "public"],
            "description": "private: only people with the link (default). public: anyone on or off Partiful.",
        },
    },
    "required": ["title", "start_at"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    **EVENT,
    "guests": {"going": 0, "maybe": 0, "cant_go": 0, "invited": 0, "waitlist": 0, "pending": 0},
}


@tool(
    name="create_event",
    title="Create event",
    access="write",
    confirm=False,
    description="New event page. Nobody is invited until you call invite_guests.",
    details=(
        "Creates and publishes an event page hosted by this account, as Create on partiful.com does, with "
        "Partiful's default theme. It is private (only people with the link) unless visibility is public. "
        "Nobody is invited or texted; share url or call invite_guests. Times without an offset are read in "
        "timezone. Guest Approval and a guest limit exclude each other, so a call with both is refused. "
        "Returns the new event."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /events",
    example_response=EXAMPLE_RESPONSE,
)
async def create_event(ctx: ToolContext, args: dict[str, Any]) -> Any:
    tz = zone(args.get("timezone") or ctx.profile.timezone)
    start = moment(args["start_at"], tz, "start_at")
    event: dict[str, Any] = {
        **_DEFAULTS,
        "title": args["title"].strip(),
        "startDate": utc_iso(start),
        "timezone": tz.key,
        "description": args.get("description") or "",
        "status": "UNSAVED",
        "visibility": args.get("visibility") or "private",
    }
    if args.get("end_at"):
        end = moment(args["end_at"], tz, "end_at")
        if end <= start:
            raise ToolError("end_at must be after start_at.", ErrorCode.INVALID_INPUT)
        event["endDate"] = utc_iso(end)
    event_id = await call(ctx, "createEvent", {"event": event, "cohostIds": []})
    if not isinstance(event_id, str) or not event_id:
        raise ToolError("Partiful did not create the event.", ErrorCode.TARGET_ERROR)
    rest = {key: value for key, value in args.items() if key in FIELDS and key not in _ON_CREATE}
    if rest:
        await apply(ctx, event_id, await event_info(ctx, event_id), rest)
    return detail(await event_info(ctx, event_id))
