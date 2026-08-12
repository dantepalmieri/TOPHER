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

OBSIDIAN_VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH", "")
CLAUDE_MODEL_NAME = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS = 1500
MAXIMUM_NOTES_TO_INCLUDE = 5
NOTE_FILE_EXTENSION = ".md"

# local sentence-transformers model used to embed notes and questions for semantic search
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
VAULT_COLLECTION_NAME = "vault_notes"

# conversation memory: persisted in full on disk, but only the most recent turns are
# replayed to claude each call to keep token usage bounded; must stay an even number,
# since turns are always appended in user/assistant pairs. also located relative to
# this file, for the same reason ENV_FILE_PATH is
CONVERSATION_HISTORY_FILE_PATH = os.path.join(PROJECT_ROOT_DIRECTORY, "conversation_history.json")
MAXIMUM_HISTORY_TURNS_FOR_CONTEXT = 20

# long-term memory: unlike CONVERSATION_HISTORY_FILE_PATH (a raw replay buffer outside
# the vault), each session gets distilled into a short summary and saved as a note inside
# the vault itself, so it's readable/editable like any other note and picked up by the
# same semantic search automatically
ASSISTANT_MEMORY_FOLDER_NAME = "Assistant Memory"
SUMMARIZATION_MAX_TOKENS = 300

# phase 3: research agent, built on the claude agent sdk rather than the raw api client
# above. it launches the vault mcp server itself (same launcher/venv the .mcp.json
# registration uses) so it can search/read the vault alongside live web search
VENV_PYTHON_EXECUTABLE_PATH = os.path.join(PROJECT_ROOT_DIRECTORY, "venv", "Scripts", "python.exe")
MCP_SERVER_LAUNCHER_PATH = os.path.join(PROJECT_ROOT_DIRECTORY, "run_mcp_server.py")
RESEARCH_AGENT_MODEL_NAME = "sonnet"

# phase 4: the rest of the agent team. developer/testing/analytics get real filesystem
# and command-execution tools (unlike research, which is read-only outside the vault),
# so they are scoped to this dedicated sandbox directory rather than the project's own
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
DASHBOARD_SERVER_HOST = "127.0.0.1"
DASHBOARD_SERVER_PORT = 8420
DASHBOARD_POLL_INTERVAL_SECONDS = 0.5
DASHBOARD_STALE_RUN_THRESHOLD_MINUTES = 25
