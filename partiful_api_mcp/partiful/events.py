"""Events and guests as the tools return them (recorded 21.10.2026).

Partiful keeps start, end and RSVP deadline in UTC with the event's IANA zone next to them; a cloned event
has `startDate: "TBD"` until it gets a date. Guest statuses are Partiful's own, mapped to the catalog's
names below.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.partiful.client import WEB, call, id_token

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

# Catalog status -> Partiful's guest statuses (getEventInfo `guestStatusCounts`, guest `status`).
STATUSES: dict[str, tuple[str, ...]] = {
    "going": ("GOING", "APPROVED"),
    "maybe": ("MAYBE",),
    "cant_go": ("DECLINED",),
    "invited": ("READY_TO_SEND", "SENDING", "SENT", "SEND_ERROR", "DELIVERY_ERROR"),
    "waitlist": ("WAITLIST", "WAITLISTED_FOR_APPROVAL"),
    "pending": ("PENDING_APPROVAL",),
}
# The rest, shown in list_guests but not counted in `guests`.
_OTHER = {
    "INTERESTED": "interested",
    "WITHDRAWN": "withdrawn",
    "REJECTED": "rejected",
    "RESPONDED_TO_FIND_A_TIME": "responded_to_poll",
}
STATUS_NAMES = list(STATUSES)

EVENT_ID: dict[str, Any] = {"type": "string", "description": "event_id from list_events."}
GUEST_IDS: dict[str, Any] = {
    "type": "array",
    "items": {"type": "string"},
    "minItems": 1,
    "maxItems": 500,
    "description": "guest_id values from list_guests.",
}


def status_name(status: str | None) -> str:
    """Partiful's guest status as the catalog name."""
    for name, values in STATUSES.items():
        if status in values:
            return name
    return _OTHER.get(status or "", (status or "unknown").lower())


def counts(item: dict[str, Any]) -> dict[str, int]:
    """Guests per catalog status from `guestStatusCounts`."""
    raw = item.get("guestStatusCounts") or {}
    return {name: sum(int(raw.get(value) or 0) for value in values) for name, values in STATUSES.items()}


def zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ToolError("timezone must be an IANA name such as America/New_York.", ErrorCode.INVALID_INPUT) from exc


def moment(value: str, tz: ZoneInfo, field: str) -> datetime:
    """An input time as an aware datetime; without an offset it is read in the event's zone."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ToolError(f"{field} must be ISO 8601, e.g. 2026-11-14T19:00-05:00.", ErrorCode.INVALID_INPUT) from exc
    return parsed.replace(tzinfo=tz) if parsed.tzinfo is None else parsed


def utc_iso(value: datetime) -> str:
    """The form createEvent takes: UTC with milliseconds."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def local(value: Any, tz_name: str | None) -> str | None:
    """A stored UTC time in the event's zone with its offset; None for none or TBD."""
    if not isinstance(value, str) or not value[:1].isdigit():
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    try:
        tz = ZoneInfo(tz_name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("UTC")
    return parsed.astimezone(tz).isoformat(timespec="seconds")


def url(event_id: str) -> str:
    return f"{WEB}/e/{event_id}"


def status(item: dict[str, Any]) -> str:
    return {"PUBLISHED": "active", "CANCELED": "canceled", "UNSAVED": "draft"}.get(item.get("status") or "", "active")


def summary(item: dict[str, Any]) -> dict[str, Any]:
    """One event in list_events."""
    tz = item.get("timezone")
    return {
        "event_id": item.get("id"),
        "title": item.get("title"),
        "start_at": local(item.get("startDate"), tz),
        "end_at": local(item.get("endDate"), tz),
        "timezone": tz,
        "location": item.get("location"),
        "status": status(item),
        "guests": counts(item),
        "url": url(item.get("id") or ""),
    }


def questions(item: dict[str, Any]) -> list[dict[str, Any]]:
    """The current Guest Questionnaire: `questionnaire`, else the last of `questionnaireVersions`."""
    current = item.get("questionnaire")
    if not current and item.get("questionnaireVersions") and item.get("questionnaireEnabled", True):
        current = item["questionnaireVersions"][-1]
    return [q for q in (current or {}).get("questions") or [] if isinstance(q, dict)]


def detail(item: dict[str, Any]) -> dict[str, Any]:
    """One event in get_event and the write tools' answers."""
    tz = item.get("timezone")
    return {
        **summary(item),
        "description": item.get("description"),
        "rsvp_deadline": local(item.get("rsvpDeadline"), tz),
        "max_guests": item.get("maxCapacity"),
        "waitlist": bool(item.get("enableWaitlist")),
        "guest_approval": item.get("guestAction") == "APPLY",
        "questions": [q.get("text") for q in questions(item)],
        "visibility": item.get("visibility"),
        "short_url": item.get("publicShortUrl"),
    }


async def event_info(ctx: ToolContext, event_id: str) -> dict[str, Any]:
    """getEventInfo's event, with its id."""
    data = await call(ctx, "getEventInfo", {"eventId": event_id})
    item = (data or {}).get("event")
    if not item:
        raise ToolError("Partiful has no such event.", ErrorCode.INVALID_INPUT)
    return {**item, "id": item.get("id") or event_id}


async def hosted(ctx: ToolContext, event_id: str) -> dict[str, Any]:
    """The event, refused unless this account hosts it."""
    uid, _ = await id_token(ctx)
    item = await event_info(ctx, event_id)
    if uid not in (item.get("ownerIds") or []):
        raise ToolError("Only a host of this event can do that.", ErrorCode.APP_PERMISSION_DENIED)
    return item
