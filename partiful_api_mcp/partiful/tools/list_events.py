"""List events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.helpers import limit, page_cursor
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import call, id_token
from partiful_api_mcp.partiful.events import summary

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "when": {
            "type": "string",
            "enum": ["upcoming", "past", "all"],
            "description": "upcoming, past or all. Default: upcoming.",
        },
        "limit": {"type": "integer", "description": "1 to 50. Default: 20."},
        "cursor": {"type": "string", "description": "next_cursor from the previous call."},
    },
    "required": [],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "events": [
        {
            "event_id": "hK3vQ9xLm2Pa7RtYc4Wd",
            "title": "Rooftop dinner",
            "start_at": "2026-11-14T19:00:00-05:00",
            "end_at": "2026-11-14T23:00:00-05:00",
            "timezone": "America/New_York",
            "location": "21 Mercer St, New York",
            "status": "active",
            "guests": {"going": 28, "maybe": 9, "cant_go": 4, "invited": 31, "waitlist": 0, "pending": 0},
            "url": "https://partiful.com/e/hK3vQ9xLm2Pa7RtYc4Wd",
        }
    ],
    "next_cursor": None,
}


@tool(
    name="list_events",
    title="List events",
    access="read",
    confirm=False,
    description="Events you host, with date, status and guest counts.",
    details=(
        "Returns the events this account hosts or cohosts, as the Hosting tab of the home page lists them: "
        "start and end in the event's time zone, active or canceled, and guests per RSVP status. Events you "
        "were only invited to are left out. Upcoming come soonest first, past most recent first. Use event_id "
        "in the other tools."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /events",
    example_response=EXAMPLE_RESPONSE,
)
async def list_events(ctx: ToolContext, args: dict[str, Any]) -> Any:
    uid, _ = await id_token(ctx)
    when = args.get("when") or "upcoming"
    items: list[dict[str, Any]] = []
    if when in ("upcoming", "all"):
        data = await call(ctx, "getMyUpcomingEventsForHomePage")
        items += sorted((data or {}).get("upcomingEvents") or [], key=lambda e: str(e.get("startDate") or ""))
    if when in ("past", "all"):
        data = await call(ctx, "getMyPastEventsForHomePage")
        past = (data or {}).get("pastEvents") or []
        items += sorted(past, key=lambda e: str(e.get("startDate") or ""), reverse=True)
    mine = [item for item in items if uid in (item.get("ownerIds") or [])]
    page, size = page_cursor(args.get("cursor")), limit(args, 20, 50)
    chunk = mine[(page - 1) * size : page * size]
    return {
        "events": [summary(item) for item in chunk],
        "next_cursor": str(page + 1) if page * size < len(mine) else None,
    }
