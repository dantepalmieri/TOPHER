# phase 5: real enforcement for the team workspace sandbox. cwd on ClaudeAgentOptions
# only sets a starting directory - it does not stop write/edit/bash from reaching
# anywhere the os user account can. confirmed directly during phase 5 verification:
# an agent used bash to create files in an unrelated existing folder outside its
# intended sandbox, and separately the write tool ignored cwd entirely and wrote to
# an absolute path elsewhere when asked to. this module is a claude agent sdk
# pretooluse hook, the sdk's own documented way to gate every tool call regardless of
# allowed_tools - can_use_tool was tried first and confirmed (via CanUseToolShadowedWarning)
# to be silently skipped whenever the tool is already granted in allowed_tools, which
# is exactly this project's setup, so it would have been a silent no-op
#
# phase 6: the original bash check only scanned for absolute windows paths, and never
# resolved relative tokens against the working directory at all. found live, not
# theoretical - during phase 6's own end-to-end verification, developer ran a plain
# team_pipeline goal and used bash with a relative path to edit the real project-root
# requirements.txt and pip-install a package into the shared venv, both fully outside
# workspace/, with nothing here catching it. replaced the absolute-only regex with a
# per-token resolution (same shape as self_modification_guard.py's bash check, mirrored
# back here), plus an explicit deny on package-manager mutation commands (pip/npm
# install/uninstall) - those have no file path in the command at all for any path
# check to catch, since their side effect is mutating the one shared venv/global
# environment every workspace/ run uses, not writing to a particular file

import os
import re
from second_brain.config import TEAM_WORKSPACE_DIRECTORY_PATH

WRITE_TOOL_NAME = "Write"
EDIT_TOOL_NAME = "Edit"
BASH_TOOL_NAME = "Bash"

BASH_TOKEN_PATTERN = re.compile(r'[^\s"\']+')

# pip/npm install or uninstall - mutates the one shared venv/global npm environment
# every workspace/ run uses, a permanent project-wide side effect no path check can
# catch since no file path appears in these commands at all
PACKAGE_MUTATION_COMMAND_PATTERN = re.compile(
    r'\bpip3?\s+(install|uninstall)\b|\bnpm\s+(i|install|uninstall)\b',
    re.IGNORECASE
)

DENIAL_REASON = (
    "Denied: this path resolves outside your sandboxed workspace directory. You may "
    "only read, write, and run commands within your current working directory - "
    "never reference an absolute path elsewhere."
)

PACKAGE_MUTATION_DENIAL_REASON = (
    "Denied: installing or uninstalling packages mutates this project's one shared "
    "venv/npm environment, not anything scoped to your sandbox workspace - that's a "
    "permanent, project-wide side effect no workspace/ run may make unilaterally. "
    "Report the dependency you need in your output instead; the user can install it."
)


def _normalized_workspace_path():
    return os.path.normcase(os.path.normpath(TEAM_WORKSPACE_DIRECTORY_PATH))


def _resolve_against_workspace(path_text):
    # resolves a possibly-relative path the same way the agent's own cwd would
    if os.path.isabs(path_text):
        candidate_path = path_text
    else:
        candidate_path = os.path.join(TEAM_WORKSPACE_DIRECTORY_PATH, path_text)

    return os.path.normcase(os.path.normpath(candidate_path))


def _path_is_within_workspace(path_text):
    normalized_workspace = _normalized_workspace_path()
    normalized_candidate = _resolve_against_workspace(path_text)

    if normalized_candidate == normalized_workspace:
        return True

    workspace_prefix = normalized_workspace + os.sep
    return normalized_candidate.startswith(workspace_prefix)


def _bash_command_stays_within_workspace(command_text):
    # a best-effort heuristic, not an os-level jail - this cannot catch every
    # possible obfuscation (environment variable expansion, indirection through a
    # generated script file), but it resolves every whitespace-separated token as a
    # path (relative tokens against the workspace directory, same as an absolute
    # one) and denies if any of them escapes - proportionate for this project's
    # actual threat model, a personal single-user assistant, not an adversarial
    # multi-tenant boundary
    candidate_tokens = BASH_TOKEN_PATTERN.findall(command_text)

    for token_index in range(len(candidate_tokens)):
        current_token = candidate_tokens[token_index]
        if _path_is_within_workspace(current_token) is False:
            return False

    return True


def _deny_result(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
        }
    }


async def check_tool_stays_in_workspace(hook_input, tool_use_id, context):
    # a claude agent sdk pretooluse hook - registered on developer/testing/analytics,
    # the three agents with real write/edit/bash access to the shared sandbox.
    # returning {} allows the call; returning a deny hookSpecificOutput blocks it
    # before it ever executes
    tool_name = hook_input["tool_name"]
    tool_input = hook_input["tool_input"]

    if tool_name == WRITE_TOOL_NAME or tool_name == EDIT_TOOL_NAME:
        file_path = tool_input.get("file_path", "")
        if _path_is_within_workspace(file_path) is False:
            return _deny_result(DENIAL_REASON)
        return {}

    if tool_name == BASH_TOOL_NAME:
        command_text = tool_input.get("command", "")
        if PACKAGE_MUTATION_COMMAND_PATTERN.search(command_text) is not None:
            return _deny_result(PACKAGE_MUTATION_DENIAL_REASON)
        if _bash_command_stays_within_workspace(command_text) is False:
            return _deny_result(DENIAL_REASON)
        return {}

    return {}
