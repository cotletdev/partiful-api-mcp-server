"""Check in guests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import call
from partiful_api_mcp.partiful.events import EVENT_ID, GUEST_IDS, hosted
from partiful_api_mcp.partiful.guests import all_guests, checked_in

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "event_id": EVENT_ID,
        "guest_ids": GUEST_IDS,
        "undo": {"type": "boolean", "description": "Remove the check-in instead. Default: false."},
    },
    "required": ["event_id", "guest_ids"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "event_id": "hK3vQ9xLm2Pa7RtYc4Wd",
    "undo": False,
    "changed": 2,
    "checked_in_total": 14,
}


@tool(
    name="check_in_guests",
    title="Check in guests",
    access="write",
    confirm=False,
    description="Mark guests as checked in at the door, or undo it.",
    details=(
        "Checks the given guests in, as the host's check-in list does, or takes the check-in back with undo. "
        "Guests get no message. Ids that are not on the guest list are refused. Returns how many guests "
        "changed and how many are checked in now. Hosts only."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /events/{event_id}/guests/check-in",
    example_response=EXAMPLE_RESPONSE,
)
async def check_in_guests(ctx: ToolContext, args: dict[str, Any]) -> Any:
    event_id, undo = args["event_id"], bool(args.get("undo"))
    await hosted(ctx, event_id)
    ids = list(dict.fromkeys(args["guest_ids"]))
    before = {doc["id"]: checked_in(doc) for doc in await all_guests(ctx, event_id)}
    if missing := [guest_id for guest_id in ids if guest_id not in before]:
        raise ToolError(f"Not on this event's guest list: {', '.join(missing)}.", ErrorCode.INVALID_INPUT)
    await call(ctx, "updateCheckInStatus", {"eventId": event_id, "guestIds": ids, "checkIn": not undo})
    after = {doc["id"]: checked_in(doc) for doc in await all_guests(ctx, event_id)}
    return {
        "event_id": event_id,
        "undo": undo,
        "changed": sum(1 for guest_id in ids if before[guest_id] != after.get(guest_id)),
        "checked_in_total": sum(after.values()),
    }
