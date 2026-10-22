"""Firestore REST on project getpartiful, with the same Firebase ID token as the callables (21.10.2026).

The web app reads the host's guest list and writes event edits straight to Firestore; no callable does
either. Security rules let the host read `events/{eventId}` with its `guests` and update the event.
Documents come in Firestore's typed form (`{"stringValue": ...}`): `decode` and `encode` convert.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from partiful_api_mcp.core.errors import ErrorCode, ToolError
from partiful_api_mcp.partiful.client import WEB, id_token

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

DATABASE = "projects/getpartiful/databases/(default)"
DOCUMENTS = f"https://firestore.googleapis.com/v1/{DATABASE}/documents"


@dataclass(frozen=True)
class Ref:
    """A document reference to write, as the web app writes `updatedBy: users/{uid}`."""

    path: str


def decode(value: dict[str, Any]) -> Any:
    """One typed Firestore value as plain JSON; references become their `collection/id` path."""
    if "mapValue" in value:
        return fields(value["mapValue"])
    if "arrayValue" in value:
        return [decode(item) for item in value["arrayValue"].get("values") or []]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "referenceValue" in value:
        return value["referenceValue"].split("/documents/", 1)[-1]
    if "nullValue" in value:
        return None
    for kind in ("stringValue", "booleanValue", "doubleValue", "timestampValue"):
        if kind in value:
            return value[kind]
    return None


def fields(document: dict[str, Any]) -> dict[str, Any]:
    """A document's (or map's) `fields` as a plain dict."""
    return {name: decode(value) for name, value in (document.get("fields") or {}).items()}


def encode(value: Any) -> dict[str, Any]:
    """A plain value in Firestore's typed form. datetime goes as a timestamp."""
    if value is None:
        return {"nullValue": None}
    if isinstance(value, Ref):
        return {"referenceValue": f"{DATABASE}/documents/{value.path}"}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, datetime):
        return {"timestampValue": value.isoformat()}
    if isinstance(value, dict):
        return {"mapValue": {"fields": {key: encode(item) for key, item in value.items()}}}
    if isinstance(value, list):
        return {"arrayValue": {"values": [encode(item) for item in value]}}
    return {"stringValue": str(value)}


async def _request(ctx: ToolContext, method: str, url: str, body: Any = None) -> Any:
    _, token = await id_token(ctx)
    response = await ctx.call(
        method,
        url,
        json=body,
        headers={"origin": WEB, "referer": f"{WEB}/", "authorization": f"Bearer {token}"},
    )
    answer = response.json()
    if response.status == 404:
        raise ToolError("Partiful has no such event.", ErrorCode.INVALID_INPUT)
    if response.status == 403:
        raise ToolError("Only a host of this event can do that.", ErrorCode.APP_PERMISSION_DENIED)
    if response.status != 200:
        raise ToolError("Partiful did not answer the request.", ErrorCode.TARGET_ERROR)
    return answer


async def get(ctx: ToolContext, path: str) -> dict[str, Any]:
    """One document's fields, with `id`."""
    document = await _request(ctx, "GET", f"{DOCUMENTS}/{path}")
    return {"id": document["name"].rsplit("/", 1)[-1], **fields(document)}


async def list_page(
    ctx: ToolContext, path: str, size: int, token: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    """One page of a collection: documents with `id`, and the next page token."""
    query = {"pageSize": size, **({"pageToken": token} if token else {})}
    answer = await _request(ctx, "GET", f"{DOCUMENTS}/{path}?{urlencode(query)}")
    docs = [{"id": doc["name"].rsplit("/", 1)[-1], **fields(doc)} for doc in answer.get("documents") or []]
    return docs, answer.get("nextPageToken") or None


async def update(
    ctx: ToolContext,
    path: str,
    changes: dict[str, Any],
    remove: tuple[str, ...] = (),
    append: dict[str, list[Any]] | None = None,
) -> None:
    """Sets top-level fields of an existing document in one `commit`, as the web app's `Write` does.

    A name in `remove` is in the mask but not in the body, which deletes the field. `append` adds array
    items server-side (`arrayUnion`), so the stored items are never read back and rewritten.
    """
    write: dict[str, Any] = {
        "update": {
            "name": f"{DATABASE}/documents/{path}",
            "fields": {name: encode(value) for name, value in changes.items()},
        },
        "updateMask": {"fieldPaths": [*changes, *remove]},
        "currentDocument": {"exists": True},
    }
    if append:
        write["updateTransforms"] = [
            {"fieldPath": name, "appendMissingElements": {"values": [encode(item) for item in items]}}
            for name, items in append.items()
        ]
    await _request(ctx, "POST", f"{DOCUMENTS}:commit", {"writes": [write]})
