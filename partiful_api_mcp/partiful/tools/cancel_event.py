"""Cancel event."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import call
from partiful_api_mcp.partiful.events import EVENT_ID, event_info, hosted, status

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "event_id": EVENT_ID,
        "message": {"type": "string", "maxLength": 480, "description": "Note to guests sent with the cancellation."},
        "notify_guests": {
            "type": "boolean",
            "description": "Let Partiful tell the guests that the event is canceled. Default: true.",
        },
    },
    "required": ["event_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {"event_id": "hK3vQ9xLm2Pa7RtYc4Wd", "status": "canceled", "guests_notified": True}


async def check_cancel(ctx: ToolContext, args: dict[str, Any]) -> None:
    """Before approval: someone else's or an already canceled event fails now."""
    event = await hosted(ctx, args["event_id"])
    if event.get("status") == "CANCELED":
        raise ToolError("This event is already canceled.", ErrorCode.INVALID_INPUT)


@tool(
    name="cancel_event",
    title="Cancel event",
    access="write",
    confirm=True,
    description="Cancel an event. Partiful notifies the guests.",
    details=(
        "Cancels the event as Cancel event on its page does: the page stays up marked canceled. By default "
        "Partiful texts the guests on the list with your message, so this reaches real people; notify_guests "
        "false cancels without telling anyone. An event that is already canceled is refused. It cannot be "
        "undone here. Hosts only. By default you confirm each call; you can switch that off for this tool."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /events/{event_id}/cancel",
    example_response=EXAMPLE_RESPONSE,
    check=check_cancel,
)
async def cancel_event(ctx: ToolContext, args: dict[str, Any]) -> Any:
    await check_cancel(ctx, args)
    notify = args.get("notify_guests", True)
    await call(
        ctx,
        "cancelEvent",
        {
            "eventId": args["event_id"],
            "cancellationMessage": (args.get("message") or "").strip(),
            "shouldSkipNotifyGuests": not notify,
        },
    )
    after = await event_info(ctx, args["event_id"])
    return {"event_id": args["event_id"], "status": status(after), "guests_notified": bool(notify)}
