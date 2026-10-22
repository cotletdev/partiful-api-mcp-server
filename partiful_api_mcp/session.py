"""Your session of the app: its cookies from your own Chrome, saved on this machine.

`<cli> connect` reads them from Chrome over the Chrome DevTools Protocol, in one of two ways:

- Chrome 144+ with remote debugging switched on at chrome://inspect/#remote-debugging. Chrome writes
  the port to `DevToolsActivePort` in its profile folder and asks you to allow each connection.
- Any Chrome started with `--remote-debugging-port=9222 --user-data-dir=<folder>`: pass `--cdp http://127.0.0.1:9222`.

An app that keeps its sign-in in the browser's storage (`app.STORAGE_KEYS`) also gets those keys, read in a tab
of `app.STORAGE_ORIGIN`: localStorage, or the Firebase user in IndexedDB. Nothing else from storage is read.

The session file holds cookies and those keys, never your password, and is readable by your user alone (0600).
Names, domains and the session cookie come from `app.py`.
"""

from __future__ import annotations

import json
import os
import platform
import re
import stat
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from partiful_api_mcp import app
from partiful_api_mcp.core.errors import ErrorCode, ToolError


def home() -> Path:
    """Where the session is kept: $<ENV>_MCP_HOME, or ~/.config/<slug>-api-mcp."""
    return Path(os.environ.get(f"{app.ENV}_MCP_HOME") or Path.home() / ".config" / f"{app.SLUG}-api-mcp")


def session_path() -> Path:
    return home() / "session.json"


@dataclass
class Session:
    cookies: list[dict[str, Any]] = field(default_factory=list)
    user_agent: str | None = None
    chrome_major: int | None = None
    locale: str | None = None
    # Where the cookies came from, so a signed-out session can be read again: "auto" or a CDP URL.
    source: str | None = None
    proxy: str | None = None
    # Origin -> {key: value} of the keys in app.STORAGE_KEYS, what tools read as `ctx.profile.local_storage`.
    local_storage: dict[str, dict[str, str]] = field(default_factory=dict)
    # The browser's IANA time zone, for tools that take local times.
    timezone: str | None = None

    @property
    def signed_in(self) -> bool:
        cookies = all(any(c["name"] == name and c.get("value") for c in self.cookies) for name in app.SESSION_COOKIES)
        stored = self.local_storage.get(app.STORAGE_ORIGIN or "", {})
        return cookies and all(stored.get(key) for key in app.STORAGE_KEYS)


def load() -> Session:
    """The saved session, with <ENV>_PROXY from the environment on top."""
    session = Session()
    path = session_path()
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        session = Session(**{k: v for k, v in data.items() if k in Session.__dataclass_fields__})
    if proxy := os.environ.get(f"{app.ENV}_PROXY", "").strip():
        session.proxy = proxy
    return session


def save(session: Session) -> Path:
    path = session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(asdict(session), fh, indent=2)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return path


def chrome_profile_dirs() -> list[Path]:
    """Default Chrome profile folders of this OS, stable channel first."""
    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "Google"
        return [base / "Chrome", base / "Chrome Beta", base / "Chrome Canary"]
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", "")) / "Google"
        return [base / "Chrome" / "User Data", base / "Chrome Beta" / "User Data", base / "Chrome SxS" / "User Data"]
    base = Path.home() / ".config"
    return [base / "google-chrome", base / "google-chrome-beta", base / "chromium"]


def auto_endpoint(profile_dir: str | None = None) -> str:
    """The browser WebSocket URL from DevToolsActivePort, written while remote debugging is on."""
    dirs = [Path(profile_dir).expanduser()] if profile_dir else chrome_profile_dirs()
    for folder in dirs:
        port_file = folder / "DevToolsActivePort"
        if port_file.exists():
            lines = port_file.read_text(encoding="utf-8").split()
            if len(lines) >= 2 and lines[0].isdigit():
                return f"ws://127.0.0.1:{lines[0]}{lines[1]}"
    raise ToolError(
        "Chrome remote debugging is off. Open chrome://inspect/#remote-debugging in Chrome, switch it on, "
        "and run this again. Or start Chrome with --remote-debugging-port=9222 and pass --cdp http://127.0.0.1:9222.",
        ErrorCode.AUTH_REQUIRED,
    )


def _endpoint(cdp: str) -> str:
    """A ws:// URL as given, or the browser WebSocket URL behind an http:// DevTools address."""
    if cdp.startswith(("ws://", "wss://")):
        return cdp
    with urllib.request.urlopen(cdp.rstrip("/") + "/json/version", timeout=10) as resp:
        return json.loads(resp.read())["webSocketDebuggerUrl"]


class _Cdp:
    """A tiny synchronous CDP client: one WebSocket to the browser target."""

    def __init__(self, url: str) -> None:
        from websockets.sync.client import connect

        # Chrome shows "Allow remote debugging?" for this connection; give the user time to click it.
        self._ws = connect(url, open_timeout=60, max_size=64 * 1024 * 1024)
        self._id = 0

    def send(self, method: str, params: dict[str, Any] | None = None, session_id: str | None = None) -> dict[str, Any]:
        self._id += 1
        message: dict[str, Any] = {"id": self._id, "method": method, "params": params or {}}
        if session_id:
            message["sessionId"] = session_id
        self._ws.send(json.dumps(message))
        while True:
            message = json.loads(self._ws.recv(timeout=60))
            if message.get("id") != self._id:
                continue
            if "error" in message:
                raise ToolError(f"Chrome refused {method}: {message['error'].get('message')}", ErrorCode.INTERNAL_ERROR)
            return message.get("result") or {}

    def close(self) -> None:
        self._ws.close()


# Run in a tab of app.STORAGE_ORIGIN: the wanted keys from localStorage, then from the Firebase user store in
# IndexedDB (records {fbase_key, value}), and the browser's time zone. Values are JSON strings.
_STORAGE_JS = """async (keys) => {
  const out = {};
  for (const key of keys) { const v = localStorage.getItem(key); if (v) out[key] = v; }
  const missing = keys.filter((key) => !(key in out));
  const names = indexedDB.databases ? (await indexedDB.databases()).map((d) => d.name) : [];
  if (missing.length && names.includes("firebaseLocalStorageDb")) {
    const db = await new Promise((ok, no) => {
      const open = indexedDB.open("firebaseLocalStorageDb");
      open.onsuccess = () => ok(open.result);
      open.onerror = () => no(open.error);
    });
    try {
      if (db.objectStoreNames.contains("firebaseLocalStorage")) {
        const rows = await new Promise((ok, no) => {
          const read = db.transaction("firebaseLocalStorage").objectStore("firebaseLocalStorage").getAll();
          read.onsuccess = () => ok(read.result);
          read.onerror = () => no(read.error);
        });
        for (const row of rows) {
          if (row && missing.includes(row.fbase_key)) out[row.fbase_key] = JSON.stringify(row.value);
        }
      }
    } finally {
      db.close();
    }
  }
  return {storage: out, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone};
}"""


def _system_timezone() -> str | None:
    """This machine's IANA zone from $TZ or the /etc/localtime link; None when neither names one."""
    if (tz := os.environ.get("TZ", "").lstrip(":")) and "/" in tz:
        return tz
    try:
        target = os.path.realpath("/etc/localtime")
    except OSError:
        return None
    return target.split("zoneinfo/", 1)[1] if "zoneinfo/" in target else None


def _read_storage(client: _Cdp) -> tuple[dict[str, dict[str, str]], str | None]:
    """The app's sign-in keys and the time zone, from an open tab of the app or a background tab opened for it."""
    origin = app.STORAGE_ORIGIN
    targets = client.send("Target.getTargets").get("targetInfos") or []
    page = next(
        (t for t in targets if t.get("type") == "page" and (t.get("url") or "").startswith(origin + "/")),
        None,
    )
    opened = None
    if page is None:
        opened = client.send("Target.createTarget", {"url": app.STORAGE_PAGE, "background": True})["targetId"]
        page = {"targetId": opened}
    try:
        session_id = client.send("Target.attachToTarget", {"targetId": page["targetId"], "flatten": True})["sessionId"]
        expression = f"({_STORAGE_JS})({json.dumps(list(app.STORAGE_KEYS))})"
        answer: dict[str, Any] = {}
        # A tab opened just now may not have its origin yet; ask again while it loads, for up to 20 s.
        for _ in range(20):
            result = client.send(
                "Runtime.evaluate",
                {"expression": expression, "awaitPromise": True, "returnByValue": True},
                session_id,
            )
            answer = (result.get("result") or {}).get("value") or {}
            if answer.get("storage") or opened is None:
                break
            time.sleep(1)
    finally:
        if opened:
            client.send("Target.closeTarget", {"targetId": opened})
    storage = answer.get("storage") or {}
    return ({origin: storage} if storage else {}), answer.get("timezone")


def from_chrome(cdp: str | None = None, profile_dir: str | None = None) -> Session:
    """Read the app's cookies of a running Chrome. Nothing is changed in the browser."""
    url = _endpoint(cdp) if cdp else auto_endpoint(profile_dir)
    try:
        client = _Cdp(url)
    except Exception as exc:
        raise ToolError(
            f"Could not connect to Chrome at {urlsplit(url).netloc} ({type(exc).__name__}). "
            "Is Chrome open, and did you click Allow in its remote debugging prompt?",
            ErrorCode.AUTH_REQUIRED,
        ) from exc
    try:
        version = client.send("Browser.getVersion")
        cookies = client.send("Storage.getCookies").get("cookies") or []
        local_storage, timezone = _read_storage(client) if app.STORAGE_KEYS else ({}, None)
    finally:
        client.close()
    mine = [
        {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path") or "/"}
        for c in cookies
        if any(c.get("domain", "").lstrip(".").endswith(domain) for domain in app.DOMAINS)
    ]
    user_agent = version.get("userAgent")
    match = re.search(r"Chrome/(\d+)", user_agent or "") or re.search(r"/(\d+)\.", version.get("product", ""))
    session = Session(
        cookies=mine,
        user_agent=user_agent,
        chrome_major=int(match.group(1)) if match else None,
        source=cdp or "auto",
        local_storage=local_storage,
        timezone=timezone or _system_timezone(),
    )
    if not session.signed_in:
        raise ToolError(
            f"This Chrome is not signed in to {app.NAME}. Sign in at {app.LOGIN_URL}, then run this again.",
            ErrorCode.AUTH_REQUIRED,
        )
    return session


def refresh(session: Session) -> Session | None:
    """Read the session again from where it came from; None when there is no source."""
    if not session.source:
        return None
    fresh = from_chrome(None if session.source == "auto" else session.source)
    fresh.proxy = session.proxy
    save(fresh)
    return fresh
