"""Delete event."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import call
from partiful_api_mcp.partiful.events import EVENT_ID, hosted

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"event_id": EVENT_ID},
    "required": ["event_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {"event_id": "hK3vQ9xLm2Pa7RtYc4Wd", "deleted": True}


async def check_delete(ctx: ToolContext, args: dict[str, Any]) -> None:
    """Before approval: someone else's event fails now."""
    await hosted(ctx, args["event_id"])


@tool(
    name="delete_event",
    title="Delete event",
    access="write",
    confirm=True,
    description="Delete an event you host for everyone, with its guest list.",
    details=(
        "Deletes the event as Delete event in its settings does: the page, guest list, photos and messages "
        "are gone for everyone and cannot be restored. Guests who RSVPd may be told by Partiful. To keep the "
        "page and tell guests, use cancel_event. Hosts only. By default you confirm each call; you can "
        "switch that off for this tool."
    ),
    input_schema=INPUT_SCHEMA,
    route="DELETE /events/{event_id}",
    example_response=EXAMPLE_RESPONSE,
    check=check_delete,
)
async def delete_event(ctx: ToolContext, args: dict[str, Any]) -> Any:
    await hosted(ctx, args["event_id"])
    await call(ctx, "deleteEvent", {"eventId": args["event_id"]})
    return {"event_id": args["event_id"], "deleted": True}
