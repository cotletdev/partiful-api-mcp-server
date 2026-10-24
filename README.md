# Partiful API and MCP server, self-hosted

A **Partiful API** and a **Partiful MCP server** you run on your own computer, in Python, on the session of your own Google Chrome. All 14 Partiful tools we run in production at [Cotlet](https://cotlet.dev/integrations/partiful-api-mcp-server): events, guest lists with questionnaire answers, the Export CSV file, check-in, Guest Approval, invites and Text Blasts.

Partiful has no public API and no official MCP server. This repo gives you both:

- **MCP server** for Claude Code, Claude Desktop, Cursor, Codex and any MCP client, over stdio or HTTP. [Setup](#mcp-server)
- **REST API** on `http://127.0.0.1:8787/api/v1/partiful`, with OpenAPI docs at `/docs`. [Setup](#rest-api)
- **Python**: `call("list_guests", event_id="...")`, plus 9 ready scripts in [`examples/`](examples/).

It is for technical people who want to run it themselves, **for noncommercial use only** ([license](#license)). If you want it running 24/7 on a server, kept working when Partiful changes its site, for a team or a business, use the [hosted version at cotlet.dev](https://cotlet.dev/integrations/partiful-api-mcp-server).

[![Partiful MCP server](https://img.shields.io/badge/Partiful%20MCP-14%20tools-6d4aef)](#all-14-tools)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-141318)](#requirements)
[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial-141318)](LICENSE)
[![MCP Badge](https://lobehub.com/badge/mcp/cotletdev-partiful-api-mcp-server)](https://lobehub.com/mcp/cotletdev-partiful-api-mcp-server)

```bash
git clone https://github.com/cotletdev/partiful-api-mcp-server.git && cd partiful-api-mcp-server
python3 -m venv .venv && . .venv/bin/activate && pip install -e .
partiful-mcp connect                                  # reads your Partiful session from Chrome
partiful-mcp call list_events
claude mcp add partiful -- "$PWD/.venv/bin/partiful-mcp" mcp
```

## Contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Install](#install)
- [Connect your Chrome](#connect-your-chrome)
- [MCP server](#mcp-server)
- [REST API](#rest-api)
- [Python and the example scripts](#python-and-the-example-scripts)
- [All 14 tools](#all-14-tools)
- [Configuration](#configuration)
- [Security and your Partiful account](#security-and-your-partiful-account)
- [Errors](#errors)
- [Self-hosted or hosted](#self-hosted-or-hosted)
- [FAQ](#faq)
- [License](#license)

## How it works

```text
AI agent (MCP) / script (REST, Python) ──▶ partiful-mcp on your computer ──your Partiful sign-in──▶ api.partiful.com
                                                  ▲                                                 Firestore
                      partiful-mcp connect ───────┘ reads it once from your Chrome (DevTools Protocol)
```

1. You sign in to Partiful in your own Chrome, with your phone number and the code Partiful texts you.
2. `partiful-mcp connect` attaches to that Chrome through the Chrome DevTools Protocol. It reads the partiful.com cookies and, from a partiful.com tab, the signed-in user that the Partiful web app keeps in IndexedDB (Firebase, with its refresh token). If no Partiful tab is open, it opens one in the background and closes it again. Both are saved to `~/.config/partiful-api-mcp/session.json`, readable by your user only.
3. Every tool call is a request to the endpoints the Partiful web app calls itself: its functions on `api.partiful.com`, and Firestore for guest lists and event edits. Requests go out with [curl_cffi](https://github.com/lexiforest/curl_cffi), which copies Chrome's TLS fingerprint. No headless browser runs.

Partiful's sign-in token lasts an hour. The server renews it from the saved refresh token at Google's `securetoken.googleapis.com`, the way the web app does, so you connect once and not every hour. When Partiful ends the session, the server reads it from Chrome again, if Chrome is open with remote debugging on.

## Requirements

- Python 3.11 or newer.
- Google Chrome 144 or newer, signed in to Partiful on partiful.com. Any Chrome or Chromium works with a [debugging port](#option-b-a-chrome-with-a-debugging-port).
- macOS, Linux or Windows.
- A Partiful account that hosts the events. Reading and changing an event's guest list, approvals, check-in, invites and Text Blasts work for events you host or cohost. `get_event` opens any event your account can see.

## Install

```bash
git clone https://github.com/cotletdev/partiful-api-mcp-server.git
cd partiful-api-mcp-server
python3 -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -e .
partiful-mcp --version
```

With [uv](https://docs.astral.sh/uv/): `uv venv && uv pip install -e .`, then `uv run partiful-mcp ...`.

Setting it up with an AI agent (Claude Code, Codex, Cursor)? Open it in this folder and ask it to set up the repo: [`AGENTS.md`](AGENTS.md) tells it every step, and it asks you only for the steps in Chrome.

To update: `git pull && pip install -e .`. We copy every change of the hosted Partiful tools into this repo.

## Connect your Chrome

### Option A: your everyday Chrome (recommended)

1. Open `chrome://inspect/#remote-debugging` in Chrome and switch **remote debugging** on. Chrome then accepts DevTools connections from programs on this computer, and asks you before each one.
2. Make sure you are signed in at [partiful.com](https://partiful.com/login).
3. Run:

   ```bash
   partiful-mcp connect
   ```

4. Chrome asks whether to allow the connection. Click **Allow**.

```text
Saved 16 Partiful cookies and 1 sign-in keys to /Users/you/.config/partiful-api-mcp/session.json
Signed in to Partiful as Maya Chen
```

You can switch remote debugging off again afterwards. Leave it on if you want the server to pick up a new session by itself after Partiful signs you out.

`connect` looks for Chrome's `DevToolsActivePort` file in the default profile folder. For Chrome Beta, Canary or a custom profile folder, pass `--profile-dir "<folder>"`.

### Option B: a Chrome with a debugging port

Chrome does not open a debugging port on your default profile, so start a separate one, sign in to Partiful there once, and connect to it:

```bash
# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-partiful"
# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-partiful"
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\.chrome-partiful"

partiful-mcp connect --cdp http://127.0.0.1:9222
```

`--cdp` also takes a `ws://` DevTools URL, for example of a Chrome on another machine reached over an SSH tunnel.

There is no paste-a-cookie option. Partiful's API takes the signed-in user from the browser's IndexedDB, not a cookie, so `connect` needs a running Chrome once. After that the session file works on its own, also on a machine without Chrome.

Check the session at any time:

```bash
partiful-mcp status
```

## MCP server

The MCP server lists every tool with its input schema, a description written for agents, and hints: read tools are marked read-only, and tools that invite, text, approve or delete are marked so your client asks before running them.

### Claude Code

```bash
claude mcp add partiful -- /path/to/partiful-api-mcp-server/.venv/bin/partiful-mcp mcp
# read only:
claude mcp add partiful -- /path/to/partiful-api-mcp-server/.venv/bin/partiful-mcp mcp --read-only
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "partiful": {
      "command": "/path/to/partiful-api-mcp-server/.venv/bin/partiful-mcp",
      "args": ["mcp"]
    }
  }
}
```

### Cursor

`~/.cursor/mcp.json`, the same block as Claude Desktop. A ready copy is in [`mcp.json`](mcp.json).

### Codex

`~/.codex/config.toml`:

```toml
[mcp_servers.partiful]
command = "/path/to/partiful-api-mcp-server/.venv/bin/partiful-mcp"
args = ["mcp"]
```

### Over HTTP

`partiful-mcp serve` also serves MCP over streamable HTTP at `http://127.0.0.1:8787/mcp`, for clients that take a URL:

```bash
partiful-mcp serve
claude mcp add --transport http partiful http://127.0.0.1:8787/mcp
```

Then ask your agent things like:

> *Who is going to Friday's dinner, and what dietary restrictions did they put in the questionnaire?*
>
> *Approve all pending guests to my launch party who answered with a company name, and list the rest for me.*
>
> *Copy last month's book club for November 14 at 7pm and invite the people who came.*
>
> *Text everyone who is Going or Maybe to my rooftop dinner that the door code is 4512.*

## REST API

```bash
partiful-mcp serve                    # http://127.0.0.1:8787, MCP at /mcp, docs at /docs
```

Each tool has its own route under `/api/v1/partiful`, the same paths as the hosted API at cotlet.dev, so code written against one works with the other. Path parts and the query string are arguments, and a JSON body adds the rest.

```bash
curl 'http://127.0.0.1:8787/api/v1/partiful/events?when=past'
curl 'http://127.0.0.1:8787/api/v1/partiful/events/hK3vQ9xLm2Pa7RtYc4Wd/guests?status=going'
curl -X PATCH http://127.0.0.1:8787/api/v1/partiful/events/hK3vQ9xLm2Pa7RtYc4Wd \
  -H 'Content-Type: application/json' \
  -d '{"location": "21 Mercer St, New York"}'
```

Any tool by name, body as its arguments:

```bash
curl -X POST http://127.0.0.1:8787/api/v1/partiful/tools/list_guests -d '{"event_id": "hK3vQ9xLm2Pa7RtYc4Wd"}'
```

- `GET /api/v1/partiful/tools`: every tool with its route, input schema and an example answer.
- `GET /docs`: interactive OpenAPI docs, `GET /openapi.json` the schema, for n8n, Postman or a generated client.
- Answers are JSON. Lists return `next_cursor`; pass it back as `cursor` for the next page.

The server listens on `127.0.0.1` only. To reach it from another device of yours, set a token, and every request then needs `Authorization: Bearer <token>`:

```bash
PARTIFUL_MCP_TOKEN=$(openssl rand -hex 24) partiful-mcp serve --host 0.0.0.0
```

## Python and the example scripts

Straight from Python, no server needed:

```python
from partiful_api_mcp import call
from partiful_api_mcp.scripting import paginate, write_rows

events = call("list_events")["events"]
going = list(paginate("list_guests", {"event_id": events[0]["event_id"], "status": "going"}, "guests"))
write_rows(going, "going.csv")
call("update_event", event_id=events[0]["event_id"], location="21 Mercer St, New York")
```

Or one tool from the shell: `partiful-mcp call list_guests event_id=hK3vQ9xLm2Pa7RtYc4Wd status=pending`, or with a JSON object.

Ready scripts in [`examples/`](examples/). Each prints JSON or text, takes `--out file.csv` or `--out file.json` where it makes sense, and `--help`:

| Script | What it does |
|---|---|
| [`list_events.py`](examples/list_events.py) | Events you host, with date, status and guests per RSVP status. `--when past`. |
| [`export_guest_list.py`](examples/export_guest_list.py) | Saves the same CSV as the Export CSV button. `--status going`. |
| [`export_rsvps.py`](examples/export_rsvps.py) | Guests of one or more events as sheet rows, one column per questionnaire question. |
| [`questionnaire_summary.py`](examples/questionnaire_summary.py) | Each questionnaire answer with how many guests gave it and who, plus who has not answered. |
| [`approve_pending_guests.py`](examples/approve_pending_guests.py) | Approves pending guests whose answers match `--match` keywords, up to `--max`. `--dry-run` first. |
| [`check_in_guests.py`](examples/check_in_guests.py) | Checks guests in by name, or undoes it. |
| [`list_past_guests.py`](examples/list_past_guests.py) | Past guests and mutuals you can invite, `--not-on` an event. |
| [`reinvite_past_guests.py`](examples/reinvite_past_guests.py) | Copies an event to a new date and invites the people who were going. `--dry-run` first. |
| [`text_guests.py`](examples/text_guests.py) | A Text Blast to chosen RSVP statuses, after showing how many people it reaches. |

```bash
python examples/export_guest_list.py --event hK3vQ9xLm2Pa7RtYc4Wd --status going --out rsvps.csv
python examples/approve_pending_guests.py --event hK3vQ9xLm2Pa7RtYc4Wd --match inc --dry-run
```

On a schedule, cron on your own computer works while it is on: `0 8 * * 1 cd ~/partiful-api-mcp-server && .venv/bin/python examples/export_rsvps.py --event <id> --status going --out rsvps.csv`.

## All 14 tools

`event_id` is the id in the event's link: `hK3vQ9xLm2Pa7RtYc4Wd` for `partiful.com/e/hK3vQ9xLm2Pa7RtYc4Wd`. `list_events` returns it. `partiful-mcp tools` prints this list, `partiful-mcp tools --json` adds the input schemas.

### Events

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `list_events` | read | `GET /events` | Events you host, with date, status and guest counts. |
| `get_event` | read | `GET /events/{event_id}` | Full event: title, description, start and end, location, RSVP deadline, guest limit, Guest Approval and waitlist settings, link. |
| `create_event` | write | `POST /events` | New event page. Nobody is invited until you call invite_guests. |
| `update_event` | write | `PATCH /events/{event_id}` | Change the details or settings of an event you host. |
| `duplicate_event` | write | `POST /events/{event_id}/duplicate` | Copy an event with its settings to a new date. The copy has no guests yet. |
| `cancel_event` | write | `POST /events/{event_id}/cancel` | Cancel an event. Partiful notifies the guests. |
| `delete_event` | write | `DELETE /events/{event_id}` | Delete an event you host for everyone, with its guest list. |

### Guest list

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `list_guests` | read | `GET /events/{event_id}/guests` | Guests of an event with RSVP status, check-in and Guest Questionnaire answers. |
| `export_guest_list` | read | `GET /events/{event_id}/guests/export` | The guest list as CSV, the same file as the Export CSV button. |
| `check_in_guests` | write | `POST /events/{event_id}/guests/check-in` | Mark guests as checked in at the door, or undo it. |
| `approve_guests` | write | `POST /events/{event_id}/guests/approve` | Approve pending guests on a Guest Approval event. |

### Invites and Text Blasts

| Tool | Access | REST route | What it does |
|---|---|---|---|
| `list_past_guests` | read | `GET /past-guests` | People you can invite: your past guests and mutuals. |
| `invite_guests` | write | `POST /events/{event_id}/guests/invite` | Invite past guests and mutuals through Partiful, or anyone by email. |
| `send_text_blast` | write | `POST /events/{event_id}/text-blasts` | Text a message to guests by RSVP status. Partiful allows up to 10 Text Blasts per event. |

Not built: inviting phone numbers (Partiful takes phone contacts only in its app), rejecting or removing guests, changing a guest's RSVP, cohosts, comments and photos, replies to a Text Blast, tickets, themes and Discover. Never built, on purpose: your Partiful sign-in, phone number, name and profile, and anything that moves money. Every request passes a guard that refuses those Partiful paths.

## Configuration

| Variable | Default | What it does |
|---|---|---|
| `PARTIFUL_MCP_HOME` | `~/.config/partiful-api-mcp` | Folder of `session.json`. |
| `PARTIFUL_PROXY` | | Proxy for every request to Partiful, e.g. `http://user:pass@host:port`. |
| `PARTIFUL_MCP_READ_ONLY` | | `1` hides and refuses every tool that changes Partiful (same as `--read-only`). |
| `PARTIFUL_MCP_TOKEN` | | Bearer token required by `serve`; needed to listen beyond `127.0.0.1`. |
| `PARTIFUL_MCP_HOST`, `PARTIFUL_MCP_PORT` | `127.0.0.1`, `8787` | Address of `serve`. |

## Security and your Partiful account

- **No codes, no password.** Partiful signs you in with a texted code. This code never asks for it: it reads the session Chrome already holds.
- **The session file is yours.** `session.json` is created with mode 0600 and holds the partiful.com cookies and the Firebase refresh token. Anyone who has it can act as you on Partiful, so keep it out of git and shared folders.
- **Local by default.** `serve` binds to `127.0.0.1` and refuses another address without `PARTIFUL_MCP_TOKEN`.
- **Three hosts only.** Requests and redirects go only to partiful.com, `securetoken.googleapis.com` (token renewal) and `firestore.googleapis.com` (guest lists, event edits).
- **Read-only mode.** `--read-only` or `PARTIFUL_MCP_READ_ONLY=1` exposes the 5 read tools only.
- **Actions reach real people.** Invites, Text Blasts, approvals and cancellations go out to real phones and inboxes at once, and a blast cannot be pulled back. MCP clients ask before running them; a script does not, so try it on a test event first.
- **Do not spam.** Partiful caps Text Blasts at 10 per event and invites at 1,000 per event. You are responsible for what runs in your account.

## Errors

The REST API answers `{"error": "<code>", "message": "..."}`. The MCP server returns the same code and message as a tool error.

| Status | Code | What to do |
|---|---|---|
| 401 | `auth_required`, `auth_expired` | No session, or Partiful signed you out. Sign in to Partiful in Chrome and run `partiful-mcp connect`. |
| 403 | `app_permission_denied` | Only a host of the event can do this. |
| 403 | `scope_denied` | The server runs read-only, or the request would change your Partiful account. |
| 403 | `target_blocked` | Partiful refused the request or showed a bot check. Open partiful.com in Chrome once, then retry. |
| 409 | `captcha_required` | Partiful asks for a CAPTCHA. Solve it in Chrome. |
| 422 | `invalid_input` | An argument is missing or wrong; the message names it. |
| 429 | `rate_limited` | Partiful is limiting the account. Wait a few minutes. |
| 502 | `target_error` | Partiful answered with an error, or changed its site. `git pull` for the latest tools, or [open an issue](https://github.com/cotletdev/partiful-api-mcp-server/issues). |

## Self-hosted or hosted

| | This repo | [Cotlet, hosted](https://cotlet.dev/integrations/partiful-api-mcp-server) |
|---|---|---|
| Tools | the same 14 | the same 14 |
| Runs | on your computer, while it is on | in the cloud, 24/7 |
| Partiful session | your Chrome, cookies and refresh token in a local file | your own Cloud Browser in the EU, profile encrypted with AES-256-GCM |
| When Partiful changes its site | `git pull` once we have fixed it | fixed for you, every tool tested daily |
| Approvals | your MCP client asks per call | invites, Text Blasts and approvals wait for your OK, switchable per tool |
| Works with | MCP clients on your machine, local scripts | Claude.ai and ChatGPT connectors, n8n, Make, Zapier, any HTTP client |
| Who may use it | you, for noncommercial use | teams, businesses, agencies |
| Price | free | free 7-day trial with 2,000 credits, no card; then one-time packs from $29 for 5,000 credits |

On the hosted version a successful Partiful call uses 25 credits, failed calls are free, and the Cloud Browser uses 50 credits a day while it has an app enabled for agents. [Full pricing](https://cotlet.dev/pricing).

## FAQ

**Does Partiful have an official API?**
No. Partiful has no public API, no developer docs and no webhooks, and its help center documents no Zapier or Make connection. Guest data leaves Partiful only as a CSV you export by hand with the Export CSV button. Details: [cotlet.dev/integrations/partiful-api-mcp-server](https://cotlet.dev/integrations/partiful-api-mcp-server).

**Is there a Partiful MCP server for Claude, ChatGPT or Cursor?**
Yes, this one runs on your machine: `partiful-mcp mcp` for Claude Code, Claude Desktop, Cursor and Codex. ChatGPT and Claude.ai connectors need a public HTTPS URL, which the [hosted Partiful MCP server](https://cotlet.dev/integrations/partiful-api-mcp-server) gives you.

**Can I export a Partiful guest list to CSV or Google Sheets?**
Yes: `python examples/export_guest_list.py --event <id> --out guests.csv` saves the Export CSV file, and `examples/export_rsvps.py` gives one row per guest with a column per questionnaire question, for a sheet. Phone numbers and emails are not in either, as in Partiful's own export.

**Can it send Text Blasts?**
Yes, `send_text_blast` to the RSVP statuses you choose. Partiful allows 10 per event and does not say how many are left, and a blast to Invited works only up to 100 people. A sent blast cannot be edited or pulled back.

**Can it invite people by phone number?**
No. Partiful takes phone contacts only in its app. `invite_guests` invites Partiful users from `list_past_guests` and anyone by email.

**Why does it need my Chrome?**
To read your Partiful session without a texted code. Chrome is used once per sign-in, not for each call: the hourly token renewal goes to Google directly.

**What happens when Partiful signs me out?**
Calls fail with `auth_expired`. With Chrome remote debugging on, the server reads the new session on the next call (click Allow when Chrome asks); otherwise sign in on partiful.com and run `partiful-mcp connect` again.

**Can it run on a VPS or in Docker?**
Technically yes: connect once on a machine with Chrome and copy `session.json` to the server, into `PARTIFUL_MCP_HOME`. Partiful then sees your session from a datacenter IP, which looks less like you. For an always-on setup the hosted version keeps your session in your own Cloud Browser on a fixed IP.

**Will my Partiful account get banned?**
Requests carry Chrome's fingerprint and go out one at a time, as you would click. Nobody can promise a platform never acts. Keep to your normal use and do not blast or invite people who did not ask for it.

**Can I use it at work or for my clients?**
No, the license allows noncommercial use only. For a team, a company or client work, use [Cotlet](https://cotlet.dev) or write to [contact@cotlet.dev](mailto:contact@cotlet.dev).

**Is it open source?**
The source is public, the license is not an open source license: noncommercial use only, no business use.

**A tool broke or I need another one.**
[Open an issue](https://github.com/cotletdev/partiful-api-mcp-server/issues) with the tool name and the error message.

## License

[PolyForm Noncommercial License 1.0.0](LICENSE). In short:

- **Allowed:** noncommercial use: you, for your own personal purposes with your own Partiful account, or a charity, school, public research or government body. Changing the code, and sharing it under the same license.
- **Not allowed:** any commercial use, your own business included; client work; selling or offering it, or a service built on it.

---

<p>
  <a href="https://cotlet.dev">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/logo-white.svg">
      <img src="assets/logo.svg" alt="Cotlet" width="120">
    </picture>
  </a>
</p>

Maintained by [Cotlet](https://cotlet.dev) ([@cotletdev](https://x.com/cotletdev)). Partiful is a trademark of its owner. This project is unofficial and not affiliated with, endorsed or sponsored by Partiful.
