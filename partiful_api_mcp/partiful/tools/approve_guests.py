"""Approve guests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import call
from partiful_api_mcp.partiful.events import EVENT_ID, GUEST_IDS, hosted
from partiful_api_mcp.partiful.guests import all_guests

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "event_id": EVENT_ID,
        "guest_ids": {**GUEST_IDS, "description": "Pending guest_id values from list_guests (status pending)."},
        "all": {"type": "boolean", "description": "Approve everyone who is pending instead. Default: false."},
    },
    "required": ["event_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {"event_id": "pL8wN2aDk4Fh7JsMq9Xe", "approved": 2, "still_pending": 1}


async def _pending(ctx: ToolContext, args: dict[str, Any]) -> list[str]:
    """The guest ids to approve; anything not pending on a Guest Approval event is refused."""
    event = await hosted(ctx, args["event_id"])
    if event.get("guestAction") != "APPLY":
        raise ToolError("This event does not use Guest Approval.", ErrorCode.INVALID_INPUT)
    pending = {doc["id"] for doc in await all_guests(ctx, args["event_id"]) if doc.get("status") == "PENDING_APPROVAL"}
    if args.get("all"):
        if not pending:
            raise ToolError("Nobody is pending on this event.", ErrorCode.INVALID_INPUT)
        return sorted(pending)
    ids = list(dict.fromkeys(args.get("guest_ids") or []))
    if not ids:
        raise ToolError("Give guest_ids or all true.", ErrorCode.INVALID_INPUT)
    if wrong := [guest_id for guest_id in ids if guest_id not in pending]:
        raise ToolError(f"Not pending on this event: {', '.join(wrong)}.", ErrorCode.INVALID_INPUT)
    return ids


async def check_approve(ctx: ToolContext, args: dict[str, Any]) -> None:
    """Before approval: ids that are not pending fail now."""
    await _pending(ctx, args)


@tool(
    name="approve_guests",
    title="Approve guests",
    access="write",
    confirm=True,
    description="Approve pending guests on a Guest Approval event.",
    details=(
        "Moves the given pending guests, or all of them, to Approved, as Approve on the host's guest list "
        "does. Partiful tells each approved guest by text or email. Ids that are not pending are refused "
        "before the call waits for your approval. Returns how many were approved and how many still wait. "
        "Hosts only. By default you confirm each call; you can switch that off for this tool."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /events/{event_id}/guests/approve",
    example_response=EXAMPLE_RESPONSE,
    check=check_approve,
)
async def approve_guests(ctx: ToolContext, args: dict[str, Any]) -> Any:
    ids = await _pending(ctx, args)
    if args.get("all"):
        await call(ctx, "approveAllGuests", {"eventId": args["event_id"], "fromStatus": "PENDING_APPROVAL"})
    else:
        await call(ctx, "updateGuestStatuses", {"eventId": args["event_id"], "guestIds": ids, "toStatus": "APPROVED"})
    # Not getEventInfo's counts: they are cached and still showed the approved guest as pending (21.10.2026).
    after = await all_guests(ctx, args["event_id"])
    left = sum(1 for doc in after if doc.get("status") == "PENDING_APPROVAL")
    return {"event_id": args["event_id"], "approved": len(ids), "still_pending": left}
