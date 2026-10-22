"""Partiful's API, recorded on the dev account (21.10.2026).

Every call is a Firebase callable: POST `api.partiful.com/<function>` with `{"data": {"params": {...}}}`,
answered with `{"result": {"data": ...}}`, and the account's Firebase ID token as `Authorization: Bearer`.
The `_partiful_session` cookie does not authenticate it (401 without the token) and no page on partiful.com
renders the user on the server, so the cookie only tells the core that the browser has signed in.

The ID token lives an hour. The web app keeps the Firebase user, with its refresh token, in IndexedDB
(`firebaseLocalStorageDb`, key `AUTH_USER_KEY`); `id_token` reads that record from the profile's storage for
partiful.com and trades the refresh token at securetoken.googleapis.com. Google answers with the same
refresh token, so nothing has to be written back. Tokens stay in this process's memory, never in Redis.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from partiful_api_mcp.core.errors import AuthExpiredError, ErrorCode, ToolError

if TYPE_CHECKING:
    from partiful_api_mcp.core.context import ToolContext

WEB = "https://partiful.com"
API = "https://api.partiful.com"
# Public web key of Firebase project getpartiful; Google refuses it without a partiful.com referer.
FIREBASE_KEY = "AIzaSyCky6PJ7cHRdBKk5X7gjuWERWaKWBHr4_k"
SECURETOKEN = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_KEY}"
AUTH_USER_KEY = f"firebase:authUser:{FIREBASE_KEY}:[DEFAULT]"
_HEADERS = {"origin": WEB, "referer": f"{WEB}/"}
# A token this close to its end is refreshed first (seconds).
_MARGIN_S = 300
# (browser_id, uid) -> (ID token, expiry as epoch seconds)
_tokens: dict[tuple[str, str], tuple[str, float]] = {}


def firebase_user(ctx: ToolContext) -> dict[str, Any] | None:
    """The signed-in Firebase user from the browser's storage for partiful.com; None when there is none."""
    return auth_user(ctx.profile.local_storage)


def auth_user(local_storage: dict[str, dict[str, str]]) -> dict[str, Any] | None:
    """The Firebase user in a jar's or a tab's `local_storage`; None without a uid and a refresh token."""
    raw = (local_storage.get(WEB) or {}).get(AUTH_USER_KEY)
    if not raw:
        return None
    try:
        user = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return None
    if not isinstance(user, dict) or not user.get("uid") or not (user.get("stsTokenManager") or {}).get("refreshToken"):
        return None
    return user


async def id_token(ctx: ToolContext) -> tuple[str, str]:
    """(uid, ID token) of the account. `AuthExpiredError` when the browser holds no usable Firebase session."""
    user = firebase_user(ctx)
    if user is None:
        raise AuthExpiredError("The app signed this account out. Reconnect it in the console.")
    uid, tokens = user["uid"], user["stsTokenManager"]
    key = (ctx.profile.browser_id, uid)
    now = time.time()
    cached = _tokens.get(key)
    if cached and cached[1] - now > _MARGIN_S:
        return uid, cached[0]
    stored, expires_ms = tokens.get("accessToken"), tokens.get("expirationTime") or 0
    if stored and expires_ms / 1000 - now > _MARGIN_S:
        _tokens[key] = (stored, expires_ms / 1000)
        return uid, stored
    response = await ctx.call(
        "POST",
        SECURETOKEN,
        data=urlencode({"grant_type": "refresh_token", "refresh_token": tokens["refreshToken"]}),
        headers={**_HEADERS, "content-type": "application/x-www-form-urlencoded"},
    )
    answer = response.json()
    if response.status == 400:
        # INVALID_REFRESH_TOKEN, TOKEN_EXPIRED, USER_DISABLED, USER_NOT_FOUND: the session is over.
        raise AuthExpiredError("The app signed this account out. Reconnect it in the console.")
    if response.status != 200 or not answer.get("id_token"):
        raise ToolError("Partiful's sign-in service did not renew the session.", ErrorCode.TARGET_ERROR)
    token = answer["id_token"]
    _tokens[key] = (token, now + int(answer.get("expires_in") or 3600))
    return uid, token


async def call(
    ctx: ToolContext,
    function: str,
    params: dict[str, Any] | None = None,
    paging: dict[str, Any] | None = None,
    *,
    whole: bool = False,
) -> Any:
    """One callable on api.partiful.com; returns `result.data` (`result` with `whole`, for its `paging`).

    `paging` (`cursor`, `maxResults`) goes next to `params`, as the web app sends it. A 401 raises
    `AuthExpiredError` in `ctx.call`.
    """
    _, token = await id_token(ctx)
    data: dict[str, Any] = {"params": params or {}}
    if paging:
        data["paging"] = paging
    response = await ctx.call(
        "POST",
        f"{API}/{function}",
        json={"data": data},
        headers={**_HEADERS, "authorization": f"Bearer {token}"},
    )
    answer = response.json()
    if response.status != 200 or "result" not in answer:
        message = (answer.get("error") or {}).get("message") if isinstance(answer, dict) else None
        raise ToolError(f"Partiful refused {function}: {message or response.status}.", ErrorCode.TARGET_ERROR)
    result = answer["result"] or {}
    return result if whole else result.get("data")
