# central configuration values for the second-brain assistant
# keeping these in one place avoids magic numbers/strings scattered through the code

import os
from dotenv import load_dotenv

# located relative to this file rather than the process's working directory, so .env
# loads correctly no matter what directory this project is launched from (e.g. an MCP
# client spawning second_brain.mcp_server as a subprocess from its own working directory)
THIS_FILE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIRECTORY = os.path.dirname(THIS_FILE_DIRECTORY)
ENV_FILE_PATH = os.path.join(PROJECT_ROOT_DIRECTORY, ".env")

load_dotenv(ENV_FILE_PATH)

# the venv python this project's own dependencies are installed into - used to spawn
# the dashboard server as a subprocess from the packaged launcher (tray_app.py)
VENV_PYTHON_EXECUTABLE_PATH = os.path.join(PROJECT_ROOT_DIRECTORY, "venv", "Scripts", "python.exe")

# phase 3: research agent, built on the claude agent sdk, with a live web search tool
RESEARCH_AGENT_MODEL_NAME = "sonnet"

# phase 4: the rest of the agent team. developer/testing/analytics get real filesystem
# and command-execution tools (unlike research, which is read-only web search), so
# they are scoped to this dedicated sandbox directory rather than the project's own
# source or an arbitrary path - nothing they do can touch this assistant's own code
TEAM_WORKSPACE_DIRECTORY_PATH = os.path.join(PROJECT_ROOT_DIRECTORY, "workspace")

ARCHITECT_AGENT_MODEL_NAME = "sonnet"
DEVELOPER_AGENT_MODEL_NAME = "sonnet"
TESTING_AGENT_MODEL_NAME = "sonnet"
ANALYTICS_AGENT_MODEL_NAME = "sonnet"

# phase 5: the dashboard - a localhost-only web ui that watches the team work live.
# the cli/agents and the dashboard server never talk to each other directly; both
# sides read/write this sqlite database instead, so the assistant works identically
# whether the dashboard is running or not. never move this project into a cloud-synced
# folder (onedrive/dropbox) - wal mode's sidecar files do not tolerate sync-driven
# file locking
DASHBOARD_DATABASE_PATH = os.path.join(PROJECT_ROOT_DIRECTORY, "dashboard.db")
DASHBOARD_SERVER_HOST = os.environ.get("DASHBOARD_SERVER_HOST", "127.0.0.1")
DASHBOARD_SERVER_PORT = 8420
DASHBOARD_POLL_INTERVAL_SECONDS = 0.5
DASHBOARD_STALE_RUN_THRESHOLD_MINUTES = 25

# phase 6: self-modification - the team may work on the project's own real source
# (not just workspace/) in self-improvement mode. these relative paths are resolved
# and protected by self_modification_guard.py - never editable, readable, or
# bash-referenceable by any agent, in any mode, no matter what it's asked to do or
# how the request is phrased. deliberately broader than "secrets": anything
# gitignored is invisible to the "it's a reviewable git diff" argument this whole
# capability leans on, so gitignored paths (conversation_history.json, dashboard.db,
# venv/) belong here too, not just credentials
SELF_MODIFICATION_PROTECTED_PATHS = [
    "second_brain/agents/workspace_guard.py",
    "second_brain/agents/self_modification_guard.py",
    "second_brain/agents/architect_agent.py",
    "second_brain/agents/research_agent.py",
    "second_brain/agents/developer_agent.py",
    "second_brain/agents/testing_agent.py",
    "second_brain/agents/analytics_agent.py",
    "second_brain/config.py",
    "second_brain/orchestrator.py",
    "second_brain/dashboard/run_trigger.py",
    ".env",
    ".mcp.json",
    ".git",
    ".claude",
    "conversation_history.json",
    "dashboard.db",
    "venv"
]
