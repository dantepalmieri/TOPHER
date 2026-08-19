# phase 4: the analytics agent - the data and metrics expert. calculates, organizes, and
# reports on what the rest of the team produced. shares the sandbox workspace (via cwd)
#
# phase 6: same two-mode pattern as developer_agent.py/testing_agent.py - sandboxed to
# workspace/ by default, or the real project root with self_modification_guard.py's
# denylist when self_improvement_mode is True. never both hooks at once

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, HookMatcher
from second_brain.config import (
    ANALYTICS_AGENT_MODEL_NAME,
    TEAM_WORKSPACE_DIRECTORY_PATH,
    PROJECT_ROOT_DIRECTORY
)
from second_brain.agents.team_workspace import ensure_team_workspace_directory_exists
from second_brain.agents.workspace_guard import check_tool_stays_in_workspace
from second_brain.agents.self_modification_guard import check_self_modification_is_safe
from second_brain.agents.analytics_prompt import ANALYTICS_AGENT_SYSTEM_PROMPT

READ_TOOL_NAME = "Read"
WRITE_TOOL_NAME = "Write"
BASH_TOOL_NAME = "Bash"

ANALYTICS_AGENT_ALLOWED_TOOLS = [READ_TOOL_NAME, WRITE_TOOL_NAME, BASH_TOOL_NAME]


def _build_analytics_agent_options(self_improvement_mode):
    # assembles the sdk options for analytics: read/write/bash for calculations and
    # reports, with the boundary and its enforcing hook chosen by mode
    if self_improvement_mode is True:
        agent_cwd = PROJECT_ROOT_DIRECTORY
        pre_tool_use_hook = check_self_modification_is_safe
    else:
        agent_cwd = TEAM_WORKSPACE_DIRECTORY_PATH
        pre_tool_use_hook = check_tool_stays_in_workspace

    agent_options = ClaudeAgentOptions(
        allowed_tools=ANALYTICS_AGENT_ALLOWED_TOOLS,
        system_prompt=ANALYTICS_AGENT_SYSTEM_PROMPT,
        model=ANALYTICS_AGENT_MODEL_NAME,
        cwd=agent_cwd,
        hooks={"PreToolUse": [HookMatcher(hooks=[pre_tool_use_hook])]}
    )

    return agent_options


async def run_analytics_query(analysis_request, self_improvement_mode=False):
    # runs one analysis request through analytics end-to-end and returns its final
    # report once the sdk reports the run complete
    ensure_team_workspace_directory_exists()
    agent_options = _build_analytics_agent_options(self_improvement_mode)
    final_result_text = ""

    async for message in query(prompt=analysis_request, options=agent_options):
        if isinstance(message, ResultMessage):
            final_result_text = message.result

    return final_result_text


def ask_analytics_agent(analysis_request, self_improvement_mode=False):
    # synchronous entry point for callers that aren't already running an asyncio event loop
    final_result_text = asyncio.run(run_analytics_query(analysis_request, self_improvement_mode))
    return final_result_text
