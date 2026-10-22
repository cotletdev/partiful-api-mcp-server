"""List guests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.helpers import limit, page_cursor
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.events import EVENT_ID, STATUS_NAMES, hosted
from partiful_api_mcp.partiful.guests import all_guests, guest

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "event_id": EVENT_ID,
        "status": {
            "type": "string",
            "enum": ["all", *STATUS_NAMES],
            "description": "all, going, maybe, cant_go, invited, waitlist or pending. Default: all.",
        },
        "checked_in": {"type": "boolean", "description": "Only guests who are checked in (true) or not (false)."},
        "limit": {"type": "integer", "description": "1 to 200. Default: 100."},
        "cursor": {"type": "string", "description": "next_cursor from the previous call."},
    },
    "required": ["event_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "guests": [
        {
            "guest_id": "zQ4mR8tLw2Ya6NcPe3Kb",
            "name": "Maya Chen",
            "status": "going",
            "count": 2,
            "plus_ones": ["Leo Park"],
            "checked_in": False,
            "rsvp_at": "2026-11-02T18:21:18-05:00",
            "message": "Can't wait!",
            "user_id": "Hn7bV2xQ9kLm4TrW8sYc3Pd5Fg61",
            "answers": [{"question": "Dietary restrictions", "answer": "Vegetarian"}],
        }
    ],
    "total": 1,
    "next_cursor": None,
}


@tool(
    name="list_guests",
    title="List guests",
    access="read",
    confirm=False,
    description="Guests of an event with RSVP status, check-in and Guest Questionnaire answers.",
    details=(
        "Returns the guest list the host sees, oldest RSVP first: name, RSVP status, party size with plus-one "
        "names, check-in, RSVP note and questionnaire answers. Hosts only. going includes guests approved on a "
        "Guest Approval event. guest_id goes to approve_guests and check_in_guests; total counts the guests "
        "that match the filters."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /events/{event_id}/guests",
    example_response=EXAMPLE_RESPONSE,
)
async def list_guests(ctx: ToolContext, args: dict[str, Any]) -> Any:
    event = await hosted(ctx, args["event_id"])
    rows = [guest(doc, event) for doc in await all_guests(ctx, args["event_id"])]
    wanted = args.get("status") or "all"
    if wanted != "all":
        rows = [row for row in rows if row["status"] == wanted]
    if "checked_in" in args:
        rows = [row for row in rows if row["checked_in"] is args["checked_in"]]
    page, size = page_cursor(args.get("cursor")), limit(args, 100, 200)
    return {
        "guests": rows[(page - 1) * size : page * size],
        "total": len(rows),
        "next_cursor": str(page + 1) if page * size < len(rows) else None,
    }
