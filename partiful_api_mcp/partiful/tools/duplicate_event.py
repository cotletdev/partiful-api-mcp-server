"""Duplicate event."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful import firestore
from partiful_api_mcp.partiful.client import call, id_token
from partiful_api_mcp.partiful.events import EVENT_ID, detail, event_info, hosted, moment, zone
from partiful_api_mcp.partiful.tools.get_event import EXAMPLE_RESPONSE as EVENT

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "event_id": EVENT_ID,
        "start_at": {
            "type": "string",
            "description": "Start of the copy, ISO 8601. Without an offset it is read in the event's time zone.",
        },
        "title": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
            "description": "Title of the copy. Default: the same.",
        },
    },
    "required": ["event_id", "start_at"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "copied_from": "aQ4tX9cEn6Hb2LsVw8Rk",
    **EVENT,
    "event_id": "bK7dR3nMp5Gc9TzXy1Qf",
    "start_at": "2026-12-12T19:00:00-05:00",
    "end_at": "2026-12-12T23:00:00-05:00",
    "guests": {"going": 0, "maybe": 0, "cant_go": 0, "invited": 0, "waitlist": 0, "pending": 0},
}


@tool(
    name="duplicate_event",
    title="Duplicate event",
    access="write",
    confirm=False,
    description="Copy an event with its settings to a new date. The copy has no guests yet.",
    details=(
        "Makes a copy as Duplicate on the event page does: title, description, location, theme, questionnaire "
        "and RSVP settings, no guests and no messages. The copy starts at start_at and keeps the original's "
        "length; Partiful does not copy the RSVP deadline. Nobody is invited. Returns the new event. Hosts only."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /events/{event_id}/duplicate",
    example_response=EXAMPLE_RESPONSE,
)
async def duplicate_event(ctx: ToolContext, args: dict[str, Any]) -> Any:
    uid, _ = await id_token(ctx)
    source = await hosted(ctx, args["event_id"])
    tz = zone(source.get("timezone") or ctx.profile.timezone)
    start = moment(args["start_at"], tz, "start_at")
    copy_id = await call(ctx, "cloneEvent", {"clonedEventId": args["event_id"], "timezone": tz.key})
    if not isinstance(copy_id, str) or not copy_id:
        raise ToolError("Partiful did not copy the event.", ErrorCode.TARGET_ERROR)
    changes: dict[str, Any] = {"startDate": start, "updatedBy": firestore.Ref(f"users/{uid}")}
    old_start, old_end = _time(source.get("startDate")), _time(source.get("endDate"))
    if old_start and old_end and old_end > old_start:
        changes["endDate"] = start + (old_end - old_start)
    if args.get("title"):
        changes["title"] = args["title"].strip()
    await firestore.update(ctx, f"events/{copy_id}", changes, () if "endDate" in changes else ("endDate",))
    return {"copied_from": args["event_id"], **detail(await event_info(ctx, copy_id))}


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value[:1].isdigit():
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
