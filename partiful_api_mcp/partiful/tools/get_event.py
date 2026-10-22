"""Get event."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.events import EVENT_ID, detail, event_info

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"event_id": EVENT_ID},
    "required": ["event_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "event_id": "hK3vQ9xLm2Pa7RtYc4Wd",
    "title": "Rooftop dinner",
    "start_at": "2026-11-14T19:00:00-05:00",
    "end_at": "2026-11-14T23:00:00-05:00",
    "timezone": "America/New_York",
    "location": "21 Mercer St, New York",
    "status": "active",
    "guests": {"going": 28, "maybe": 9, "cant_go": 4, "invited": 31, "waitlist": 0, "pending": 0},
    "url": "https://partiful.com/e/hK3vQ9xLm2Pa7RtYc4Wd",
    "description": "Bring a drink to share.",
    "rsvp_deadline": "2026-11-12T18:00:00-05:00",
    "max_guests": 60,
    "waitlist": True,
    "guest_approval": False,
    "questions": ["Dietary restrictions"],
    "visibility": "private",
    "short_url": "https://go.partiful.com/aB3dE5fG",
}


@tool(
    name="get_event",
    title="Get event",
    access="read",
    confirm=False,
    description=(
        "Full event: title, description, start and end, location, RSVP deadline, guest limit, Guest Approval "
        "and waitlist settings, link."
    ),
    details=(
        "Returns one event as its page shows it to the host, with guests per RSVP status and the Guest "
        "Questionnaire questions. Times are in the event's time zone. Works for any event the account can "
        "open; the write tools need an event it hosts."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /events/{event_id}",
    example_response=EXAMPLE_RESPONSE,
)
async def get_event(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return detail(await event_info(ctx, args["event_id"]))
