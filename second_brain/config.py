# central configuration values for the second-brain assistant
# keeping these in one place avoids magic numbers/strings scattered through the code

import os
from dotenv import load_dotenv

# located relative to this file rather than the process's working directory, so .env
# loads correctly no matter what directory this project is launched from
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

# the team talks as a real, bounded conversation rather than a fixed 5-step relay:
# each agent's reply can hand off to a specific teammate or declare the goal DONE
# (see conversation_protocol.py). this cap guarantees the loop always terminates
# even if nobody ever says DONE. each turn is a full claude code cli subprocess
# call against the user's Pro/Max subscription usage-limit window, not metered
# per-token billing - the old fixed pipeline made exactly 5 such calls per goal,
# this can make up to double that in the worst case, so this number is a real
# cost/usage tradeoff, not an arbitrary safety margin
MAXIMUM_CONVERSATION_TURNS = 10

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
