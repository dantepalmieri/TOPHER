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

import os
import re
from second_brain.config import TEAM_WORKSPACE_DIRECTORY_PATH

WRITE_TOOL_NAME = "Write"
EDIT_TOOL_NAME = "Edit"
BASH_TOOL_NAME = "Bash"

# matches a windows drive-letter absolute path, e.g. C:\Users\... or C:/Users/...
ABSOLUTE_WINDOWS_PATH_PATTERN = re.compile(r'[A-Za-z]:[\\/][^\s"\']*')

DENIAL_REASON = (
    "Denied: this path resolves outside your sandboxed workspace directory. You may "
    "only read, write, and run commands within your current working directory - "
    "never reference an absolute path elsewhere."
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
    # generated script file), but it blocks exactly the failure mode this module
    # exists for: an agent using bash to mkdir/write/cd somewhere else entirely via
    # an explicit absolute path, which is what was actually observed during
    # verification. proportionate for this project's actual threat model - a
    # personal single-user assistant, not an adversarial multi-tenant boundary
    mentioned_paths = ABSOLUTE_WINDOWS_PATH_PATTERN.findall(command_text)

    for path_index in range(len(mentioned_paths)):
        current_path = mentioned_paths[path_index]
        if _path_is_within_workspace(current_path) is False:
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
        if _bash_command_stays_within_workspace(command_text) is False:
            return _deny_result(DENIAL_REASON)
        return {}

    return {}
