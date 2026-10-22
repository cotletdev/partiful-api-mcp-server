"""Everything the server knows about Partiful outside `partiful/`: names, domains and where the session lives.

The rest of the package reads these values and never names the app itself.
"""

from __future__ import annotations

NAME = "Partiful"
SLUG = "partiful"
# The command and the prefix of every environment variable (PARTIFUL_MCP_HOME, PARTIFUL_MCP_TOKEN ...).
CLI = "partiful-mcp"
ENV = "PARTIFUL"
# Requests may reach only these hosts and their subdomains. Their cookies are read from Chrome.
# securetoken.googleapis.com renews the sign-in token, firestore.googleapis.com holds guest lists and event edits.
DOMAINS = ("partiful.com", "securetoken.googleapis.com", "firestore.googleapis.com")
# Present only while signed in.
SESSION_COOKIES = ("_partiful_session",)
LOGIN_URL = "https://partiful.com/login"
# A final URL with one of these means the app signed the session out.
LOGGED_OUT_MARKERS = ("/login",)
# The web app keeps the signed-in user (Firebase, with its refresh token) in this origin's IndexedDB.
# `connect` reads these keys from a tab of the origin; without them the session is not signed in.
STORAGE_ORIGIN = "https://partiful.com"
STORAGE_PAGE = "https://partiful.com/events"
STORAGE_KEYS = ("firebase:authUser:AIzaSyCky6PJ7cHRdBKk5X7gjuWERWaKWBHr4_k:[DEFAULT]",)
# A 401 or 403 whose body has one of these asks for a fresh sign-in. Partiful has none.
RELOGIN_MARKERS: tuple[str, ...] = ()
# Paths of the app's sign-in, sign-out and the user's own record: tools may read them, never write to them.
ACCOUNT_PATHS = (
    r"^/api/(login|logout)$",
    r"^/(sendAuthCode|sendAuthCodeTrusted|getLoginToken|setConsentMetadata)$",
    r"^/(updateUser|deleteUser|deactivateUser|updateUserReference)$",
)
# REST routes live under this path, the same as on cotlet.dev.
API_PREFIX = "/api/v1/partiful"
# Prepended to the MCP server's instructions: where an agent starts.
AGENT_START = "Start with list_events: its `event_id` values are what every other tool takes."
