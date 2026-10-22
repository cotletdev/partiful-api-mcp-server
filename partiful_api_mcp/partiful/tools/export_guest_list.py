"""Export guest list."""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import API, WEB, id_token
from partiful_api_mcp.partiful.events import EVENT_ID, STATUS_NAMES, STATUSES, hosted

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "event_id": EVENT_ID,
        "statuses": {
            "type": "array",
            "items": {"type": "string", "enum": STATUS_NAMES},
            "description": "RSVP statuses to include: going, maybe, cant_go, invited, waitlist, pending. Default: all.",
        },
    },
    "required": ["event_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "event_id": "hK3vQ9xLm2Pa7RtYc4Wd",
    "statuses": ["going"],
    "rows": 1,
    "filename": "rooftop-dinner-guests.csv",
    "csv": (
        "Name,Status,Checked in,Check-in Time,RSVP date,Dietary restrictions\r\n"
        "Maya Chen,Going,No,,2026-11-02 18:21:18-05:00,Vegetarian\r\n"
    ),
}


@tool(
    name="export_guest_list",
    title="Export guest list",
    access="read",
    confirm=False,
    description="The guest list as CSV, the same file as the Export CSV button.",
    details=(
        "Returns the file the host's Export CSV button downloads, for the chosen RSVP statuses. Columns are "
        "Partiful's: Name, Status, Checked in, Check-in Time, RSVP date, then one column per Guest Questionnaire "
        "question. Status is Partiful's label, for example Approved on a Guest Approval event. The file text "
        "comes back in csv, not as a link, with rows (guests in the file) and a suggested filename. The file "
        "has no guest ids, emails or phone numbers; for guest ids use list_guests. Hosts only."
    ),
    input_schema=INPUT_SCHEMA,
    route="GET /events/{event_id}/guests/export",
    example_response=EXAMPLE_RESPONSE,
)
async def export_guest_list(ctx: ToolContext, args: dict[str, Any]) -> Any:
    event = await hosted(ctx, args["event_id"])
    names = list(dict.fromkeys(args.get("statuses") or STATUS_NAMES))
    query: list[tuple[str, str]] = [("eventId", args["event_id"])]
    query += [("statuses", value) for name in names for value in STATUSES[name]]
    query.append(("questionnaire", "true"))
    uid, token = await id_token(ctx)
    response = await ctx.call(
        "GET",
        f"{API}/getGuestsCsv?" + "&".join(f"{key}={value}" for key, value in query),
        headers={"origin": WEB, "referer": f"{WEB}/", "authorization": f"Bearer {token}", "x-user-id": uid},
    )
    if response.status != 200:
        raise ToolError("Partiful did not export the guest list.", ErrorCode.TARGET_ERROR)
    text = response.text
    rows = max(0, len(list(csv.reader(io.StringIO(text)))) - 1) if text.strip() else 0
    slug = "-".join("".join(c if c.isalnum() else " " for c in (event.get("title") or "event").lower()).split())
    return {
        "event_id": args["event_id"],
        "statuses": names,
        "rows": rows,
        "filename": f"{slug or 'event'}-guests.csv",
        "csv": text,
    }
