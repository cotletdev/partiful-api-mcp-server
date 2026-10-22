"""Invite guests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.core.tools import tool
from partiful_api_mcp.partiful.client import call
from partiful_api_mcp.partiful.events import EVENT_ID, counts, event_info, hosted

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

# Partiful's limits per event (help.partiful.com, 21.10.2026).
_MAX_INVITES = 1000
_MAX_EMAILS = 500

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "event_id": EVENT_ID,
        "user_ids": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": _MAX_INVITES,
            "description": "user_id values from list_past_guests.",
        },
        "emails": {
            "type": "array",
            "maxItems": _MAX_EMAILS,
            "items": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string", "minLength": 1, "description": "Shown on the invite."},
                },
                "required": ["email", "name"],
                "additionalProperties": False,
            },
            "description": "People to invite by email, with the name the invite greets.",
        },
        "message": {"type": "string", "maxLength": 480, "description": "Personal note sent with the invites."},
    },
    "required": ["event_id"],
    "additionalProperties": False,
}

EXAMPLE_RESPONSE: dict[str, Any] = {
    "event_id": "bK7dR3nMp5Gc9TzXy1Qf",
    "invited": 2,
    "by_email": 1,
    "invited_total": 31,
}


async def check_invite(ctx: ToolContext, args: dict[str, Any]) -> None:
    """Before approval: nobody to invite or someone else's event fails now."""
    if not args.get("user_ids") and not args.get("emails"):
        raise ToolError("Give user_ids or emails.", ErrorCode.INVALID_INPUT)
    event = await hosted(ctx, args["event_id"])
    if event.get("status") == "CANCELED":
        raise ToolError("This event is canceled.", ErrorCode.INVALID_INPUT)


@tool(
    name="invite_guests",
    title="Invite guests",
    access="write",
    confirm=True,
    description="Invite past guests and mutuals through Partiful, or anyone by email.",
    details=(
        "Sends invites as the host's Invite screen does, so they reach real people: Partiful users from "
        "list_past_guests get Partiful's invite, people in emails get an email with the event link and your "
        "note. There is no way to invite a phone number: Partiful takes phone contacts only in its app. "
        "Email invitees still sign in with a phone number to RSVP. Partiful allows 1,000 invites per event, "
        "500 of them by email. A canceled event is refused. invited_total is the event's Invited count after "
        "the call. Hosts only. By default you confirm each call; you can switch that off for this tool."
    ),
    input_schema=INPUT_SCHEMA,
    route="POST /events/{event_id}/guests/invite",
    example_response=EXAMPLE_RESPONSE,
    check=check_invite,
)
async def invite_guests(ctx: ToolContext, args: dict[str, Any]) -> Any:
    await check_invite(ctx, args)
    users = list(dict.fromkeys(args.get("user_ids") or []))
    emails = [{"guestName": e["name"].strip(), "emailAddress": e["email"].strip()} for e in args.get("emails") or []]
    await call(
        ctx,
        "addInvitedGuestsAsHost",
        {
            "eventId": args["event_id"],
            "userIdsToInvite": users,
            "invitationMessage": (args.get("message") or "").strip(),
            "otherMutualsCount": 0,
            "phoneContactsToInvite": [],
            "emailsToInvite": emails,
        },
    )
    after = await event_info(ctx, args["event_id"])
    return {
        "event_id": args["event_id"],
        "invited": len(users) + len(emails),
        "by_email": len(emails),
        "invited_total": counts(after)["invited"],
    }
