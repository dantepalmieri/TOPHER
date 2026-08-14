# phase 6: real enforcement for the team's self-modification capability. unlike
# workspace_guard.py (an allowlist - stay inside workspace/), this is a denylist -
# the boundary is the entire real project root, and the interesting part is what's
# excluded from it. a plan subagent pressure-tested the first draft of this design
# against the real codebase and found several gaps a naive port of workspace_guard.py's
# approach would have missed - each one is called out below at the check it fixes

import os
import re
from second_brain.config import PROJECT_ROOT_DIRECTORY, SELF_MODIFICATION_PROTECTED_PATHS

READ_TOOL_NAME = "Read"
WRITE_TOOL_NAME = "Write"
EDIT_TOOL_NAME = "Edit"
BASH_TOOL_NAME = "Bash"
GREP_TOOL_NAME = "Grep"
GLOB_TOOL_NAME = "Glob"

# denies bash commands that try to create a symlink or hardlink outright, rather
# than trying to detect the resulting alias path after the fact - realpath() alone
# cannot catch an ntfs hardlink, since a hardlink is a second directory entry to the
# same file, not indirection through a path, and hardlinks need no elevated windows
# privilege to create
LINK_CREATION_COMMAND_PATTERN = re.compile(
    r"mklink|fsutil\s+hardlink|New-Item\s+-ItemType\s+(Sym|Hard)Link",
    re.IGNORECASE
)

# matches whitespace/quote-delimited tokens in a bash command - deliberately not
# restricted to tokens that already look like absolute paths (workspace_guard.py's
# ABSOLUTE_WINDOWS_PATH_PATTERN would miss "cat .env" entirely, since that's a
# relative path). every token is resolved against the agent's own cwd and checked,
# so a plain relative reference to a protected file is caught the same way an
# absolute one would be
BASH_TOKEN_PATTERN = re.compile(r'[^\s"\']+')

DENIAL_REASON = (
    "Denied: this touches a protected part of Topher's own safety wiring or "
    "secrets, which no agent may read, write, or reference - even in "
    "self-improvement mode, even if asked directly. This protection cannot be "
    "turned off by any instruction."
)

# acknowledged limitation, not a silent gap: environment-variable indirection in
# bash (e.g. $env:P=".env"; cat $env:P) can defeat a static string check by
# construction. not worth engineering around - this project's actual threat model
# is a single personal user's own occasional errant instruction, not an
# adversarial actor deliberately trying to defeat its own sandbox


def _resolve_protected_paths():
    # every protected path, realpath'd once per call so a fresh symlink/junction
    # created since the last call can't stay stale in a cached comparison set
    resolved_paths = []

    for path_index in range(len(SELF_MODIFICATION_PROTECTED_PATHS)):
        relative_path = SELF_MODIFICATION_PROTECTED_PATHS[path_index]
        absolute_path = os.path.join(PROJECT_ROOT_DIRECTORY, relative_path)
        resolved_paths.append(os.path.realpath(os.path.normcase(absolute_path)))

    return resolved_paths


def _normalize_candidate_path(path_text, cwd_text):
    # resolves a possibly-relative path against the agent's own cwd (carried on
    # every hook_input), then realpath's it as defense-in-depth against
    # symlinks/junctions pointing at a protected target from inside a safe area
    if os.path.isabs(path_text):
        candidate_path = path_text
    else:
        candidate_path = os.path.join(cwd_text, path_text)

    return os.path.realpath(os.path.normcase(candidate_path))


def _path_touches_protected_entry(path_text, cwd_text):
    # true if the candidate path is a protected entry, or sits inside one
    normalized_candidate = _normalize_candidate_path(path_text, cwd_text)
    protected_paths = _resolve_protected_paths()

    for protected_index in range(len(protected_paths)):
        current_protected = protected_paths[protected_index]

        if normalized_candidate == current_protected:
            return True

        if normalized_candidate.startswith(current_protected + os.sep):
            return True

    return False


def _search_root_reaches_protected_entry(search_root_text, cwd_text):
    # grep/glob need a different check than read/write/edit: a point-wise check
    # on the search root alone misses an unscoped search that never NAMES a
    # protected file but walks straight through it (e.g. Grep(pattern="ANTHROPIC")
    # with no path, defaulting to cwd, or Glob("**/*") from the project root).
    # deny whenever the search root is a protected entry, is an ancestor of one
    # (walking from it would reach the protected entry), or sits inside one
    normalized_root = _normalize_candidate_path(search_root_text, cwd_text)
    protected_paths = _resolve_protected_paths()

    for protected_index in range(len(protected_paths)):
        current_protected = protected_paths[protected_index]

        if normalized_root == current_protected:
            return True

        if current_protected.startswith(normalized_root + os.sep):
            return True

        if normalized_root.startswith(current_protected + os.sep):
            return True

    return False


def _bash_command_touches_protected_entry(command_text, cwd_text):
    if LINK_CREATION_COMMAND_PATTERN.search(command_text) is not None:
        return True

    candidate_tokens = BASH_TOKEN_PATTERN.findall(command_text)

    for token_index in range(len(candidate_tokens)):
        current_token = candidate_tokens[token_index]
        if _path_touches_protected_entry(current_token, cwd_text) is True:
            return True

    return False


def _deny_result(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
        }
    }


async def check_self_modification_is_safe(hook_input, tool_use_id, context):
    # a claude agent sdk pretooluse hook - registered whenever an agent operates
    # on the real project root instead of the workspace/ sandbox (self-improvement
    # mode, and always on architect regardless of mode - see the module docstring
    # in architect_agent.py for why). unlike workspace_guard.py this also gates
    # read/grep/glob, not just write/edit/bash - the project root contains real
    # secrets (.env) that were never reachable from inside workspace/, so reads
    # are just as dangerous as writes here
    tool_name = hook_input["tool_name"]
    tool_input = hook_input["tool_input"]
    cwd_text = hook_input["cwd"]

    if tool_name == WRITE_TOOL_NAME or tool_name == EDIT_TOOL_NAME or tool_name == READ_TOOL_NAME:
        file_path = tool_input.get("file_path", "")
        if _path_touches_protected_entry(file_path, cwd_text) is True:
            return _deny_result(DENIAL_REASON)
        return {}

    if tool_name == GREP_TOOL_NAME or tool_name == GLOB_TOOL_NAME:
        search_root = tool_input.get("path", cwd_text)
        if _search_root_reaches_protected_entry(search_root, cwd_text) is True:
            return _deny_result(DENIAL_REASON)
        return {}

    if tool_name == BASH_TOOL_NAME:
        command_text = tool_input.get("command", "")
        if _bash_command_touches_protected_entry(command_text, cwd_text) is True:
            return _deny_result(DENIAL_REASON)
        return {}

    return {}
