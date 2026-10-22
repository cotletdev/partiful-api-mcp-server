"""Who is signed in: Partiful's own answer for the account (callable getCurrentUser), for "Signed in as ..."."""

from __future__ import annotations

from typing import TYPE_CHECKING

from partiful_api_mcp.core.errors import AuthExpiredError
from partiful_api_mcp.partiful.client import call, id_token

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext


async def whoami(ctx: ToolContext) -> str | None:
    """None only when Partiful says signed out; any other failure raises (detection tries again later)."""
    try:
        uid, _ = await id_token(ctx)
        data = await call(ctx, "getCurrentUser", {"targetUserId": uid})
    except AuthExpiredError:
        return None
    user = (data or {}).get("user") or {}
    return user.get("name") or user.get("phoneNumber") or None
