# TOPHER

**T.O.P.H.E.R.** — Totally Open Personal Home Environment Robot. A personal
multi-agent assistant: hand it a goal and a five-agent team (Architect,
Research, Developer, Testing, Analytics) works it as a live conversation,
each agent handing off to whoever should act next, sandboxed to its own
workspace directory. A dashboard lets you watch and trigger any of this from
a browser, including remotely over your own private network.

Topher (or "Toph") is the assistant's identity across every part of the
project — every team agent operates under that one name, each in their own
distinct voice, the same way JARVIS is one assistant across every system it
runs.

## Features

- A five-agent team (Architect, Research, Developer, Testing, Analytics)
  that works a goal as a real, bounded conversation — each agent hands off to
  a specific teammate or declares the goal done, not a fixed step order
- A deep-research agent with live web search, for one-off questions outside
  the full team conversation
- A live web dashboard showing the conversation as it happens, plus history
  for past runs, reachable over your private network
- Authenticates through your existing Claude Pro or Max subscription (via the
  Claude Code CLI's own login) — no API key, no metered per-token billing
- A Windows installer with a system tray app, so the whole thing runs in the
  background and can launch on login

## Installation

Whichever option you pick below, TOPHER needs the
[Claude Code CLI](https://claude.com/claude-code) logged in on this machine
first — if you already use Claude Code, you're already logged in and can
skip this. Otherwise, install it and run:

```powershell
claude login
```

authenticated by your Claude Pro or Max subscription. Every agent
authenticates through that login; there's no API key to configure.

### Option A: Windows installer

No release has been published yet — until the first `v*.*.*` tag is cut,
build the installer yourself (see [`packaging/`](packaging/) and
`.github/workflows/release.yml` for the full pipeline) or use Option B below.

Once a release exists: download the latest `TOPHER-Setup-x.y.z.exe` from
[Releases](https://github.com/dantepalmieri/TOPHER/releases) and run it. It
installs to `%LOCALAPPDATA%\Programs\TOPHER` — no admin rights needed — and
adds a Start Menu entry plus an optional "launch on login" shortcut.

If `claude login` hasn't been run yet, the tray app tells you so on first
launch instead of starting the server. Once you're logged in, reopen TOPHER
and it runs from a system tray icon:

- **Open Dashboard** — opens `http://localhost:8420/` in your browser
- **Restart Server** / **Stop Server**
- **View Logs**
- **Start on Login** — toggles the Startup-folder shortcut

### Option B: From source

```powershell
git clone https://github.com/dantepalmieri/TOPHER.git
cd TOPHER
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows notes:** use `python`, not `python3` (Windows intercepts `python3`
as a Microsoft Store shortcut). If PowerShell blocks venv activation, run
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

Every command below needs the venv active and must run from the project root
— `second_brain` and its dependencies only exist in the venv, and `-m`
resolves the package relative to your current directory.

## Usage

```powershell
python -m second_brain.research_cli   # deep research: live web search
python -m second_brain.team_cli       # full agent team on a goal
```

`second_brain.research_cli` is for open-ended research — "what's the latest
on X" — a single agent with live web search.

`second_brain.team_cli` hands a goal to the full team as a live conversation,
starting with Architect. Talk to one agent directly instead of the whole
team with an `agentname:` prefix, e.g.
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

The dashboard shows every run (team conversation, research) live, whether
started from the "Trigger a Run" panel on the page itself or from a
terminal — both read/write the same local `dashboard.db`, so the CLIs and
the dashboard work independently of each other.

For frontend development with hot reload, run `npm run dev` in
`dashboard-frontend/` alongside the dashboard server.

### Remote access (private network only)

By default the dashboard only binds to `127.0.0.1`. To reach it from another
device on your own network, set `DASHBOARD_SERVER_HOST` in a `.env` file at
the project root to an address reachable from that network — e.g. a
[Tailscale](https://tailscale.com/) IP (`tailscale ip -4`) — then restart the
server and open `http://<that-address>:8420/` from any device on it.

There is no login system — the private network itself is the entire access
control. Every device that can reach that address can both watch and
trigger runs.

## Project layout

```
second_brain/
  identity.py, config.py, types.py   - shared identity text, config, dataclasses
  agents/                             - the five team agents, their prompts, and the
                                        shared workspace sandbox guard
  dashboard/                          - run_store.py (sqlite), run_trigger.py, server.py (FastAPI)
  orchestrator.py                     - the team conversation loop and single-agent routing
  research_cli.py / team_cli.py       - the two interactive entry points
workspace/              - sandbox directory the team builds in
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
