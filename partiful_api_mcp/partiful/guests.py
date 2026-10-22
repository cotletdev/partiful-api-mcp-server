"""The host's guest list: Firestore `events/{eventId}/guests`, one document per guest (recorded 21.10.2026).

No callable gives the host guest ids (`getGuests` refuses a host), so list_guests, approve_guests and
check_in_guests start here. Questionnaire answers sit in `questionnaireResponse.answers`, keyed by
question id of the version the guest answered.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from partiful_api_mcp.partiful import firestore
from partiful_api_mcp.partiful.events import local, questions, status_name

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

# Firestore's page size for the guests collection; an event holds at most about 1,000 invites.
_PAGE = 300
_MAX_PAGES = 10


async def all_guests(ctx: ToolContext, event_id: str) -> list[dict[str, Any]]:
    """Every guest document of the event, oldest RSVP first."""
    out: list[dict[str, Any]] = []
    token: str | None = None
    for _ in range(_MAX_PAGES):
        docs, token = await firestore.list_page(ctx, f"events/{event_id}/guests", _PAGE, token)
        out.extend(docs)
        if not token:
            break
    return sorted(out, key=lambda doc: str(doc.get("rsvpDate") or doc.get("createdAt") or ""))


def checked_in(doc: dict[str, Any]) -> bool:
    """`checkIn` is `{checkedInBy, date}` while the guest is checked in."""
    value = doc.get("checkIn")
    return bool(value.get("date") or value.get("checkedInBy")) if isinstance(value, dict) else value is True


def _answer(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("value", value.get("text", ""))
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


def guest(doc: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """One guest as list_guests returns it."""
    response = doc.get("questionnaireResponse") or {}
    versions = event.get("questionnaireVersions") or []
    version = response.get("questionnaireVersion")
    asked = (
        versions[version].get("questions") or []
        if isinstance(version, int) and 0 <= version < len(versions)
        else questions(event)
    )
    texts = {q.get("id"): q.get("text") for q in asked if isinstance(q, dict)}
    answers = response.get("answers") or {}
    user = doc.get("user")
    return {
        "guest_id": doc["id"],
        "name": doc.get("name"),
        "status": status_name(doc.get("status")),
        "count": int(doc.get("count") or 1),
        "plus_ones": [p.get("name") for p in doc.get("plusOnes") or [] if isinstance(p, dict) and p.get("name")],
        "checked_in": checked_in(doc),
        "rsvp_at": local(doc.get("rsvpDate"), event.get("timezone")),
        "message": doc.get("rsvpMessage") or None,
        "user_id": user.rsplit("/", 1)[-1] if isinstance(user, str) else None,
        "answers": [
            {"question": texts.get(key, key), "answer": _answer(value)}
            for key, value in answers.items()
            if _answer(value)
        ],
    }
