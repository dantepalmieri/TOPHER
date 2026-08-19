# TOPHER

**T.O.P.H.E.R.** — Totally Open Personal Home Environment Robot. A personal AI
assistant that searches and writes to your Obsidian vault, remembers
conversations, hands off goals to a five-agent team (Architect, Research,
Developer, Testing, Analytics) that plans, investigates, builds, reviews, and
reports on them end to end, and can work on its own codebase directly in a
self-improvement mode that can't touch its own safety wiring. A persistent
dashboard lets you watch and trigger any of this from a browser, including
remotely over your own private network.

Topher (or "Toph") is the assistant's identity across every part of the
project — the core vault assistant and every team agent operate under that
one name, each in their own distinct voice, the same way JARVIS is one
assistant across every system it runs.

## Features

- Semantic search over your Obsidian vault, with citations
- Short-term (per-session) and long-term (distilled, written back into the
  vault) conversation memory
- An MCP server so Claude Code/Desktop can search, read, and write your vault
  directly
- A deep-research agent with live web search, plus your vault
- A five-agent team (Architect → Research → Developer → Testing → Analytics)
  that takes a goal and builds it end to end
- Self-improvement mode: the team can edit and commit directly to Topher's own
  codebase, with a hard, non-overridable boundary around its own guardrails,
  secrets, and git internals
- A live web dashboard to watch every kind of run and trigger new ones,
  reachable over your private network
- A Windows installer with a system tray app, so the whole thing runs in the
  background and can launch on login

## Installation

### Option A: Windows installer

Download the latest `TOPHER-Setup-x.y.z.exe` from
[Releases](https://github.com/dantepalmieri/TOPHER/releases) and run it. It
installs to `%LOCALAPPDATA%\Programs\TOPHER` — no admin rights needed — and
adds a Start Menu entry plus an optional "launch on login" shortcut.

On first launch, a small setup window asks for your Anthropic API key (from
[console.anthropic.com](https://console.anthropic.com)) and your Obsidian
vault folder, validates the key live, and writes them to `.env` in the
install directory. After that, Topher runs from a system tray icon:

- **Open Dashboard** — opens `http://127.0.0.1:8420/` in your browser
- **Restart Server** / **Stop Server**
- **View Logs**
- **Settings...** — reopens the setup window to change your key or vault path
- **Start on Login** — toggles the Startup-folder shortcut

Self-improvement mode needs [Git for Windows](https://git-scm.com/download/win)
on `PATH` to commit changes — everything else works without it. The installer
warns you if it's missing but won't block install.

Building the installer yourself, or wiring up the release pipeline, is
covered in [`packaging/`](packaging/) and `.github/workflows/release.yml`.

### Option B: From source

```powershell
git clone https://github.com/dantepalmieri/TOPHER.git
cd TOPHER
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env`:

```
ANTHROPIC_API_KEY=your-api-key-here
OBSIDIAN_VAULT_PATH=C:/Users/you/Documents/YourVaultName
```

- `ANTHROPIC_API_KEY` — from [console.anthropic.com](https://console.anthropic.com)
- `OBSIDIAN_VAULT_PATH` — absolute path to your vault folder. Use forward
  slashes (`C:/Users/...`) even on Windows, to avoid backslash-escaping
  issues in `.env` parsing.
- `HF_TOKEN` — optional, picked up implicitly by `sentence-transformers` when
  downloading the embedding model.

**Windows notes:** use `python`, not `python3` (Windows intercepts `python3`
as a Microsoft Store shortcut). If PowerShell blocks venv activation, run
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

Every command below needs the venv active and must run from the project root
— `second_brain` and its dependencies only exist in the venv, and `-m`
resolves the package relative to your current directory.

## Usage

```powershell
python -m second_brain.cli            # vault Q&A with memory
python -m second_brain.research_cli   # deep research: live web + vault
python -m second_brain.team_cli       # full agent team on a goal
```

`second_brain.cli` is the core assistant: ask about your notes, it searches
the vault semantically, answers with citations, remembers the conversation,
and can create/append vault notes when you ask it to.

`second_brain.research_cli` is for open-ended research — "what's the latest
on X" — that needs live web search rather than just your existing notes.

`second_brain.team_cli` hands a goal to the full team: Architect plans it,
Research investigates open questions, Developer builds it, Testing reviews
it, Analytics reports on the result. Talk to one agent directly instead of
the whole pipeline with an `agentname:` prefix, e.g.
`architect: plan a REST API for a todo app`.

### The dashboard

```powershell
python -m second_brain.dashboard.server   # http://127.0.0.1:8420
```

Build the frontend first if you haven't:

```powershell
cd dashboard-frontend
npm install
npm run build
```

The dashboard shows every run (team pipeline, self-improve, research, vault
Q&A) live, whether started from the "Trigger a Run" panel on the page itself
or from a terminal — both read/write the same local `dashboard.db`, so the
CLIs and the dashboard work independently of each other. Self-Improve mode
gets its own confirmation dialog before it starts, since it's the one mode
that lets the team commit directly to Topher's own codebase.

For frontend development with hot reload, run `npm run dev` in
`dashboard-frontend/` alongside the dashboard server.

### Remote access (private network only)

By default the dashboard only binds to `127.0.0.1`. To reach it from another
device on your own network, set `DASHBOARD_SERVER_HOST` in `.env` to an
address reachable from that network — e.g. a [Tailscale](https://tailscale.com/)
IP (`tailscale ip -4`) — then restart the server and open
`http://<that-address>:8420/` from any device on it.

There is no login system — the private network itself is the entire access
control. Every device that can reach that address can both watch and trigger
runs, including self-improve mode.

### Registering the vault as an MCP server

```powershell
copy .mcp.json.example .mcp.json
```

Fill in `.mcp.json` with your own absolute paths:

```json
{
  "mcpServers": {
    "second-brain-vault": {
      "command": "C:\\path\\to\\TOPHER\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\TOPHER\\run_mcp_server.py"]
    }
  }
}
```

Use the **venv's** `python.exe`, not the system `python`. The same
command/args go in `%APPDATA%\Claude\claude_desktop_config.json` for Claude
Desktop. Exposes 5 tools: `search_vault`, `list_vault_notes`,
`read_vault_note`, `create_vault_note`, `append_to_vault_note`.

## Project layout

```
second_brain/
  identity.py, config.py, types.py   - shared identity text, config, dataclasses
  vault/                              - reading, writing, and semantically searching the vault
  claude/client.py                    - the core assistant's Claude API calls + vault-write tools
  conversation_history.py             - short-term memory
  assistant_memory.py                 - long-term memory, written back into the vault
  agents/                             - the five team agents, plus the sandbox/self-mod guards
  dashboard/                          - run_store.py (sqlite), run_trigger.py, server.py (FastAPI)
  orchestrator.py                     - routes a request to one agent, or the full team pipeline
  cli.py / research_cli.py / team_cli.py   - the three interactive entry points
  mcp_server.py                       - exposes the vault as 5 MCP tools
run_mcp_server.py       - self-locating launcher for mcp_server.py
workspace/              - sandbox directory the team builds in (non-self-improve mode)
dashboard-frontend/     - React + TypeScript + Vite dashboard UI
packaging/              - Windows installer, launcher, and build scripts
tests/                  - pytest suite
```

## Development

```powershell
pip install -r requirements.txt -r requirements-dev.txt
ruff check .
pytest tests/ -v
```

CI (`.github/workflows/ci.yml`) runs lint and tests on every push/PR; a
version tag (`v*.*.*`) triggers `release.yml`, which builds the bundled venv,
the frontend, the frozen launcher, and the installer, then publishes it as a
GitHub Release.
