# the shared sandbox directory that developer/testing/analytics operate in - kept
# separate from this project's own source, so nothing the team builds, runs, or
# tests can touch code outside its own workspace

import os
from second_brain.config import TEAM_WORKSPACE_DIRECTORY_PATH


def ensure_team_workspace_directory_exists():
    # creates the sandbox directory on first use; a no-op if it already exists
    os.makedirs(TEAM_WORKSPACE_DIRECTORY_PATH, exist_ok=True)
