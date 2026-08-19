# phase 4: the analytics agent - the data and metrics expert. calculates, organizes, and
# reports on what the rest of the team produced. always sandboxed to workspace/, enforced
# by workspace_guard.py's allowlist.

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, HookMatcher
from second_brain.config import ANALYTICS_AGENT_MODEL_NAME, TEAM_WORKSPACE_DIRECTORY_PATH
from second_brain.agents.team_workspace import ensure_team_workspace_directory_exists
from second_brain.agents.workspace_guard import check_tool_stays_in_workspace
from second_brain.agents.analytics_prompt import ANALYTICS_AGENT_SYSTEM_PROMPT

READ_TOOL_NAME = "Read"
WRITE_TOOL_NAME = "Write"
BASH_TOOL_NAME = "Bash"

ANALYTICS_AGENT_ALLOWED_TOOLS = [READ_TOOL_NAME, WRITE_TOOL_NAME, BASH_TOOL_NAME]


def _build_analytics_agent_options():
    # assembles the sdk options for analytics: read/write/bash for calculations and
    # reports, sandboxed to the shared workspace directory and enforced by its
    # allowlist hook
    agent_options = ClaudeAgentOptions(
        allowed_tools=ANALYTICS_AGENT_ALLOWED_TOOLS,
        system_prompt=ANALYTICS_AGENT_SYSTEM_PROMPT,
        model=ANALYTICS_AGENT_MODEL_NAME,
        cwd=TEAM_WORKSPACE_DIRECTORY_PATH,
        hooks={"PreToolUse": [HookMatcher(hooks=[check_tool_stays_in_workspace])]}
    )

    return agent_options


async def run_analytics_query(analysis_request):
    # runs one analysis request through analytics end-to-end and returns its final
    # report once the sdk reports the run complete
    ensure_team_workspace_directory_exists()
    agent_options = _build_analytics_agent_options()
    final_result_text = ""

    async for message in query(prompt=analysis_request, options=agent_options):
        if isinstance(message, ResultMessage):
            final_result_text = message.result

    return final_result_text


def ask_analytics_agent(analysis_request):
    # synchronous entry point for callers that aren't already running an asyncio event loop
    final_result_text = asyncio.run(run_analytics_query(analysis_request))
    return final_result_text
