# AGENTS.md

You are an AI agent in a clone of this repo. It is a self-hosted Partiful API and MCP server: 14 tools that work in the user's own Partiful account, through the session of their own Google Chrome. Your usual job is one of three: set it up for the user, use its tools for them, or change its code. Human docs: `README.md`.

## Before you start

- The license allows noncommercial use only (PolyForm Noncommercial 1.0.0, `LICENSE`). If the user is setting this up for a company, a team or clients, say so and point to the hosted version at https://cotlet.dev/integrations/partiful-api-mcp-server. Do not continue the setup for that use.
- Every tool acts as the user on Partiful. Tools with access `write` create, change, cancel or delete events, check in, approve, invite and send Text Blasts, and real people get the texts and emails.

## Set it up for the user

Do the steps yourself. Ask the user only for what needs their hands in Chrome.

1. Check Python: `python3 --version` must be 3.11 or newer.
2. Install in the repo root:

   ```bash
   python3 -m venv .venv && .venv/bin/pip install -e .
   .venv/bin/partiful-mcp --version
   ```

   On Windows the path is `.venv\Scripts\partiful-mcp`. With uv: `uv venv && uv pip install -e .`.
3. Ask the user to do two things in Chrome. You cannot open `chrome://` pages for them.
   - Open `chrome://inspect/#remote-debugging` and switch remote debugging on.
   - Be signed in at https://partiful.com (phone number and the texted code; you never ask for the code).
4. Run `.venv/bin/partiful-mcp connect`. Tell the user to click **Allow** when Chrome asks about the connection. If no partiful.com tab is open, `connect` opens one in the background and closes it. Success prints `Signed in to Partiful as <name>`.
5. Check: `.venv/bin/partiful-mcp status`, then `.venv/bin/partiful-mcp call list_events`.
6. Add the MCP server to the user's client. Use the absolute path of `.venv/bin/partiful-mcp`:
   - Claude Code: `claude mcp add partiful -- <abs path>/.venv/bin/partiful-mcp mcp`
   - Claude Desktop, Cursor, Codex: the config blocks in `README.md`, section "MCP server".
   - Add `--read-only` after `mcp` if the user only wants to read.
   The client loads new MCP servers on its next start. Tell the user.

If step 4 fails:

| Message | What to do |
|---|---|
| `Chrome remote debugging is off` | Step 3 is not done, or Chrome is Beta, Canary or a custom profile: pass `--profile-dir "<profile folder>"`. |
| `Could not connect to Chrome` | The user did not click Allow, or Chrome is closed. Run `connect` again. |
| `This Chrome is not signed in to Partiful` | The user signs in at partiful.com in that Chrome, then run `connect` again. |
| No Chrome on this machine (a server) | Run `connect` on a machine with Chrome, then the user copies `session.json` into `PARTIFUL_MCP_HOME` on the server. A pasted cookie does not work: the session lives in Chrome's IndexedDB. |

## Use the tools

- With the MCP server added, call its tools. Without it: `.venv/bin/partiful-mcp call <tool> key=value ...`, or one JSON object as the argument.
- `.venv/bin/partiful-mcp tools` lists every tool with access and route. `tools --json` adds the input schemas.
- Start with `list_events`. Its `event_id` values (the id in `partiful.com/e/<id>`) are what most tools take. `list_guests` gives the `guest_id` values for `approve_guests` and `check_in_guests`, `list_past_guests` the `user_id` values for `invite_guests`.
- Lists return `next_cursor`. Pass it back as `cursor` for the next page.
- Before a `write` tool that reaches people (`invite_guests`, `send_text_blast`, `approve_guests`, `cancel_event`), show the user what you will send and to whom, and get their OK. A Text Blast cannot be pulled back, and Partiful allows 10 per event.
- For a script or a cron job, use `partiful_api_mcp.scripting` (`call`, `paginate`, `write_rows`) and the scripts in `examples/` as models.
- For a REST API (n8n, other languages): `.venv/bin/partiful-mcp serve`, routes under `http://127.0.0.1:8787/api/v1/partiful`, docs at `/docs`.

Errors come as `<code>: <message>`. `auth_expired` means Partiful signed the session out: the user signs in again in Chrome and you run `connect`. `app_permission_denied` means the account does not host that event. More codes: `README.md`, section "Errors".

## Keep secrets out

- `~/.config/partiful-api-mcp/session.json` holds the user's Partiful cookies and Firebase refresh token, full access to their account. Never print, log, commit or copy its content.
- `serve` listens on 127.0.0.1. Never start it on another address without `PARTIFUL_MCP_TOKEN`.

## Change the code

| Path | What | Edit? |
|---|---|---|
| `partiful_api_mcp/partiful/` | the Partiful tools, one file per tool in `tools/`; callables and token renewal in `client.py`, Firestore in `firestore.py` | Yes for a local fix, but the next `git pull` brings our version of these files. Report the bug at https://github.com/cotletdev/partiful-api-mcp-server/issues |
| `partiful_api_mcp/app.py` | app name, domains, session cookie and storage keys, account paths, REST prefix | Rarely |
| `partiful_api_mcp/core/` | `@tool` declaration, errors, account guard, the HTTP client with the session (`context.py`) | Yes |
| `partiful_api_mcp/session.py` | reading cookies and the IndexedDB sign-in from Chrome over CDP, the session file | Yes |
| `partiful_api_mcp/runner.py`, `api.py`, `mcp_server.py`, `cli.py` | tool registry, REST API, MCP server, command line | Yes |
| `examples/` | scripts for common jobs | Yes |

A new tool is a new file in `partiful_api_mcp/partiful/tools/` with a `@tool(...)` declaration (name, access, input schema, `route`). The registry finds it, and the REST API, the MCP server and the CLI show it without other changes.

There is no test suite. After a change, run `.venv/bin/partiful-mcp tools` and one read tool against the user's account.
