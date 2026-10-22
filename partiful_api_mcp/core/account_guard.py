"""Tools never change your account in the app: password, email, sign-in, two-factor, profile.

Checked on every request a tool makes, before it leaves. Reads stay allowed ("who am I" is a profile GET);
any other method to an account path is refused. The common paths are matched for every app, `app.ACCOUNT_PATHS`
adds the app's own.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from partiful_api_mcp import app
from partiful_api_mcp.core.errors import ErrorCode, ToolError

_READS = frozenset({"GET", "HEAD", "OPTIONS"})
_COMMON = re.compile(
    r"passw|two[-_]?factor|2fa|(^|[/_-])(mfa|totp|otp)([/_-]|$)|recovery[-_]?code|"
    r"(change|update|verify)[-_]?email|email[-_]?(change|update)|"
    r"(delete|deactivate|close)[-_]?account|account[-_/](delete|deactivate|close)|"
    r"(^|/)(log[-_]?out|sign[-_]?out|log[-_]?in|sign[-_]?in)([/?]|$)"
)
# Case-insensitive: the path is lowercased, the app's patterns keep its own spelling (getLoginToken).
_APP = [re.compile(pattern, re.IGNORECASE) for pattern in app.ACCOUNT_PATHS]


def check_account_write(method: str, url: str) -> None:
    if method.upper() in _READS:
        return
    path = urlsplit(url).path.lower()
    if _COMMON.search(path) or any(pattern.search(path) for pattern in _APP):
        raise ToolError(
            f"This server never changes your {app.NAME} account (password, email, sign-in, profile).",
            ErrorCode.SCOPE_DENIED,
        )
