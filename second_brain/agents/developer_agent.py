# phase 4: the developer agent - builds whatever the plan calls for. the first agent in
# this project with real write/edit/bash access. always sandboxed to workspace/, enforced
# by workspace_guard.py's allowlist (cwd alone does not enforce that sandbox, see
# workspace_guard.py for why) - it never operates on this assistant's own source.

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, HookMatcher
from second_brain.config import DEVELOPER_AGENT_MODEL_NAME, TEAM_WORKSPACE_DIRECTORY_PATH
from second_brain.agents.team_workspace import ensure_team_workspace_directory_exists
from second_brain.agents.workspace_guard import check_tool_stays_in_workspace
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


def _build_developer_agent_options():
    # assembles the sdk options for the developer: the full builtin coding toolset,
    # sandboxed to the shared workspace directory and enforced by its allowlist hook
    agent_options = ClaudeAgentOptions(
        allowed_tools=DEVELOPER_AGENT_ALLOWED_TOOLS,
        system_prompt=DEVELOPER_AGENT_SYSTEM_PROMPT,
        model=DEVELOPER_AGENT_MODEL_NAME,
        cwd=TEAM_WORKSPACE_DIRECTORY_PATH,
        hooks={"PreToolUse": [HookMatcher(hooks=[check_tool_stays_in_workspace])]}
    )

    return agent_options


async def run_developer_query(build_request):
    # runs one build request through the developer end-to-end and returns its final
    # changelog-style report once the sdk reports the run complete
    ensure_team_workspace_directory_exists()
    agent_options = _build_developer_agent_options()
    final_result_text = ""

    async for message in query(prompt=build_request, options=agent_options):
        if isinstance(message, ResultMessage):
            final_result_text = message.result

    return final_result_text


def ask_developer(build_request):
    # synchronous entry point for callers that aren't already running an asyncio event loop
    final_result_text = asyncio.run(run_developer_query(build_request))
    return final_result_text
