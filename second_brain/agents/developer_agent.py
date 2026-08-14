# phase 4: the developer agent - builds whatever the plan calls for. the first agent in
# this project with real write/edit/bash access.
#
# phase 6: developer now has two modes. by default (self_improvement_mode=False) it
# stays exactly as before - sandboxed to workspace/, enforced by workspace_guard.py's
# allowlist (cwd alone does not enforce that sandbox, see workspace_guard.py for why).
# in self-improvement mode, cwd becomes the real project root and the hook swaps to
# self_modification_guard.py's denylist instead - never both hooks at once, since
# workspace_guard.py's boundary check would deny everything outside workspace/, which
# is the wrong boundary entirely once cwd is the project root

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, HookMatcher
from second_brain.config import DEVELOPER_AGENT_MODEL_NAME, TEAM_WORKSPACE_DIRECTORY_PATH, PROJECT_ROOT_DIRECTORY
from second_brain.agents.team_workspace import ensure_team_workspace_directory_exists
from second_brain.agents.workspace_guard import check_tool_stays_in_workspace
from second_brain.agents.self_modification_guard import check_self_modification_is_safe
from second_brain.agents.developer_prompt import DEVELOPER_AGENT_SYSTEM_PROMPT

READ_TOOL_NAME = "Read"
WRITE_TOOL_NAME = "Write"
EDIT_TOOL_NAME = "Edit"
BASH_TOOL_NAME = "Bash"
GLOB_TOOL_NAME = "Glob"
GREP_TOOL_NAME = "Grep"

DEVELOPER_AGENT_ALLOWED_TOOLS = [
    READ_TOOL_NAME, WRITE_TOOL_NAME, EDIT_TOOL_NAME, BASH_TOOL_NAME, GLOB_TOOL_NAME, GREP_TOOL_NAME
]


def _build_developer_agent_options(self_improvement_mode):
    # assembles the sdk options for the developer: the full builtin coding toolset,
    # with the boundary and its enforcing hook chosen by mode - never both hooks
    # registered together, since they implement two different, mutually exclusive
    # boundary models (allowlist vs denylist)
    if self_improvement_mode is True:
        agent_cwd = PROJECT_ROOT_DIRECTORY
        pre_tool_use_hook = check_self_modification_is_safe
    else:
        agent_cwd = TEAM_WORKSPACE_DIRECTORY_PATH
        pre_tool_use_hook = check_tool_stays_in_workspace

    agent_options = ClaudeAgentOptions(
        allowed_tools=DEVELOPER_AGENT_ALLOWED_TOOLS,
        system_prompt=DEVELOPER_AGENT_SYSTEM_PROMPT,
        model=DEVELOPER_AGENT_MODEL_NAME,
        cwd=agent_cwd,
        hooks={"PreToolUse": [HookMatcher(hooks=[pre_tool_use_hook])]}
    )

    return agent_options


async def run_developer_query(build_request, self_improvement_mode=False):
    # runs one build request through the developer end-to-end and returns its final
    # changelog-style report once the sdk reports the run complete
    ensure_team_workspace_directory_exists()
    agent_options = _build_developer_agent_options(self_improvement_mode)
    final_result_text = ""

    async for message in query(prompt=build_request, options=agent_options):
        if isinstance(message, ResultMessage):
            final_result_text = message.result

    return final_result_text


def ask_developer(build_request, self_improvement_mode=False):
    # synchronous entry point for callers that aren't already running an asyncio event loop
    final_result_text = asyncio.run(run_developer_query(build_request, self_improvement_mode))
    return final_result_text
