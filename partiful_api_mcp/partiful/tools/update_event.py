"""Update event."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.editing import FIELDS, apply
from partiful_api_mcp.partiful.events import EVENT_ID, detail, event_info, hosted
from partiful_api_mcp.partiful.tools.get_event import EXAMPLE_RESPONSE as EVENT

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"event_id": EVENT_ID, **FIELDS},
    "required": ["event_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {"updated": ["location"], **EVENT, "location": "88 Bleecker St, New York"}


@tool(
    name="update_event",
    title="Update event",
    access="write",
    confirm=False,
    description="Change the details or settings of an event you host.",
    details=(
        "Changes only the fields you give, as the event's Edit page and settings panel do: title, times, time "
        "zone, location, description, RSVP deadline, guest limit, Guest Approval and the Guest Questionnaire. "
        "Fields left out keep their value; a call with no field is refused. Turning Guest Approval on removes "
        "the guest limit and the waitlist, and the first guest limit turns the waitlist on. New questions "
        "replace the questionnaire for guests who RSVP from then on. Returns the event after the change, with "
        "updated listing the fields you gave. Hosts only."
    ),
    input_schema=INPUT_SCHEMA,
    route="PATCH /events/{event_id}",
    example_response=EXAMPLE_RESPONSE,
)
async def update_event(ctx: ToolContext, args: dict[str, Any]) -> Any:
    changes = {key: value for key, value in args.items() if key != "event_id"}
    if not changes:
        raise ToolError("Give at least one field to change.", ErrorCode.INVALID_INPUT)
    old = await hosted(ctx, args["event_id"])
    updated = await apply(ctx, args["event_id"], old, changes)
    return {"updated": updated, **detail(await event_info(ctx, args["event_id"]))}
