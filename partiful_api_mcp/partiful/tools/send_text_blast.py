"""Send Text Blast."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import call
from partiful_api_mcp.partiful.events import EVENT_ID, STATUSES, hosted
from partiful_api_mcp.partiful.guests import all_guests

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

# Who a blast can go to, as the Send Text Blast modal groups guests.
_GROUPS = ["going", "maybe", "cant_go", "invited", "waitlist", "pending"]
# Text length the modal allows by SMS; email only allows more, but SMS is always on here.
_MAX_TEXT = 480

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "event_id": EVENT_ID,
        "message": {"type": "string", "minLength": 1, "maxLength": _MAX_TEXT, "description": "Message text."},
        "statuses": {
            "type": "array",
            "items": {"type": "string", "enum": _GROUPS},
            "minItems": 1,
            "description": "Who receives it: going, maybe, cant_go, invited, waitlist, pending.",
        },
        "show_on_event_page": {
            "type": "boolean",
            "description": "Also show the blast in the event's activity feed. Default: true.",
        },
    },
    "required": ["event_id", "message", "statuses"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "event_id": "hK3vQ9xLm2Pa7RtYc4Wd",
    "recipients": 37,
    "by_status": {"going": 28, "maybe": 9},
    "sent": True,
}


async def _recipients(ctx: ToolContext, args: dict[str, Any]) -> dict[str, int]:
    await hosted(ctx, args["event_id"])
    docs = await all_guests(ctx, args["event_id"])
    by_status = {name: sum(1 for doc in docs if doc.get("status") in STATUSES[name]) for name in args["statuses"]}
    if not sum(by_status.values()):
        raise ToolError("No guest has the chosen statuses, so the blast would reach nobody.", ErrorCode.INVALID_INPUT)
    return by_status


async def check_blast(ctx: ToolContext, args: dict[str, Any]) -> None:
    """Before approval: a blast to nobody or on someone else's event fails now."""
    await _recipients(ctx, args)


@tool(
    name="send_text_blast",
    title="Send Text Blast",
    access="write",
    confirm=True,
    description="Text a message to guests by RSVP status. Partiful allows up to 10 Text Blasts per event.",
    details=(
        "Sends a Text Blast as the host's Send Text Blast does: by text and email to every guest with the "
        "chosen RSVP statuses, push for guests with the app, and shown in the event's feed unless "
        "show_on_event_page is false. Real people get it at once and it cannot be taken back. Up to 480 "
        "characters. recipients and by_status count the guests with those statuses at the moment of sending; "
        "a choice that reaches nobody is refused before you confirm. Partiful allows 10 blasts per event and "
        "refuses a blast to Invited when that group holds more than 100 guests. The answer does not say how "
        "many blasts are left. Hosts only. By default you confirm each call; you can switch that off for this "
        "tool."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /events/{event_id}/text-blasts",
    example_response=EXAMPLE_RESPONSE,
    check=check_blast,
)
async def send_text_blast(ctx: ToolContext, args: dict[str, Any]) -> Any:
    by_status = await _recipients(ctx, args)
    to = [value for name in args["statuses"] for value in STATUSES[name]]
    await call(
        ctx,
        "createTextBlast",
        {
            "eventId": args["event_id"],
            "message": {
                "text": args["message"].strip(),
                "to": to,
                "showOnEventPage": args.get("show_on_event_page", True),
                "notificationChannels": ["Sms", "Email"],
            },
        },
    )
    return {"event_id": args["event_id"], "recipients": sum(by_status.values()), "by_status": by_status, "sent": True}
