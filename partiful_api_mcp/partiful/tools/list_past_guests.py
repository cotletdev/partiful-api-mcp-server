"""List past guests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.helpers import limit, page_cursor
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import call, id_token

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

# getContacts pages as the web app asks for them; past this many pages the rest is left out.
_PAGE = 1000
_MAX_PAGES = 5

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "not_on_event_id": {
            "type": "string",
            "description": "Leave out people already on this event (event_id), as its Invite list does.",
        },
        "query": {"type": "string", "description": "Only names containing this text."},
        "limit": {"type": "integer", "description": "1 to 200. Default: 50."},
        "cursor": {"type": "string", "description": "next_cursor from the previous call."},
    },
    "required": [],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "people": [
        {
            "user_id": "Hn7bV2xQ9kLm4TrW8sYc3Pd5Fg61",
            "name": "Maya Chen",
            "past_guest": True,
            "shared_events": 3,
            "last_shared_event": {"event_id": "hK3vQ9xLm2Pa7RtYc4Wd", "title": "Rooftop dinner"},
        }
    ],
    "total": 1,
    "next_cursor": None,
}


@tool(
    name="list_past_guests",
    title="List past guests",
    access="read",
    confirm=False,
    description="People you can invite: your past guests and mutuals.",
    details=(
        "Returns the people Partiful offers on an event's Invite screen: past guests of your events and "
        "mutuals from events you went to, with how many events you shared. Give not_on_event_id to leave "
        "out people already on that event; there is no filter by one past event. query matches part of the "
        "name. user_id goes to invite_guests. A new account has nobody yet, and shared_events or "
        "last_shared_event stay 0 or null when Partiful leaves them out."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /past-guests",
    example_response=EXAMPLE_RESPONSE,
)
async def list_past_guests(ctx: ToolContext, args: dict[str, Any]) -> Any:
    uid, _ = await id_token(ctx)
    contacts: list[Any] = []
    if event_id := args.get("not_on_event_id"):
        data = await call(ctx, "getContactsFilteredByEvent", {"eventId": event_id})
        contacts = _items(data)
    else:
        cursor: str | None = None
        for _ in range(_MAX_PAGES):
            paging: dict[str, Any] = {"maxResults": _PAGE, **({"cursor": cursor} if cursor else {})}
            result = await call(ctx, "getContacts", {}, paging, whole=True)
            contacts += _items(result.get("data"))
            cursor = (result.get("paging") or {}).get("nextCursor")
            if not cursor:
                break
    people = [p for p in (_person(item) for item in contacts) if p and p["user_id"] != uid]
    if text := (args.get("query") or "").strip().lower():
        people = [p for p in people if text in (p["name"] or "").lower()]
    page, size = page_cursor(args.get("cursor")), limit(args, 50, 200)
    return {
        "people": people[(page - 1) * size : page * size],
        "total": len(people),
        "next_cursor": str(page + 1) if page * size < len(people) else None,
    }


def _items(data: Any) -> list[Any]:
    """getContacts answers a list, getContactsFilteredByEvent `{contacts: [...]}`."""
    if isinstance(data, dict):
        data = data.get("contacts") or data.get("users") or []
    return data if isinstance(data, list) else []


def _person(item: Any) -> dict[str, Any] | None:
    """One contact, shaped like getContactsFilteredByEvent's; getContacts was only seen empty, so all is optional."""
    if not isinstance(item, dict):
        return None
    nested = item.get("user")
    user: dict[str, Any] = nested if isinstance(nested, dict) else {}
    user_id = item.get("id") or item.get("userId") or user.get("id")
    if not user_id:
        return None
    event = item.get("sharedEvent")
    shared: dict[str, Any] | None = event if isinstance(event, dict) else None
    return {
        "user_id": user_id,
        "name": item.get("name") or user.get("name"),
        "past_guest": bool(item.get("isPastGuest")),
        "shared_events": int(item.get("sharedEventCount") or 0),
        "last_shared_event": {"event_id": shared.get("id"), "title": shared.get("title")} if shared else None,
    }
