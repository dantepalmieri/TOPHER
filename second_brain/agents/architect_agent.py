# phase 4: the architect agent - turns a goal into a scoped plan and hands it to
# research. plans only; no write/edit/bash, so it can never build anything itself.
#
# now sandboxed to workspace/ like the rest of the team, enforced by
# workspace_guard.py's allowlist - self-improvement mode (which previously let this
# agent read Topher's own real project for planning context) has been removed, so
# there is no longer a reason for this agent's cwd to be anything but the shared
# sandbox. it plans from the goal and the team's own conversation, not by reading
# this assistant's own source.

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, HookMatcher
from second_brain.config import ARCHITECT_AGENT_MODEL_NAME, TEAM_WORKSPACE_DIRECTORY_PATH
from second_brain.agents.team_workspace import ensure_team_workspace_directory_exists
from second_brain.agents.workspace_guard import check_tool_stays_in_workspace
from second_brain.agents.architect_prompt import ARCHITECT_AGENT_SYSTEM_PROMPT

READ_TOOL_NAME = "Read"
GLOB_TOOL_NAME = "Glob"
GREP_TOOL_NAME = "Grep"

ARCHITECT_AGENT_ALLOWED_TOOLS = [READ_TOOL_NAME, GLOB_TOOL_NAME, GREP_TOOL_NAME]


def _build_architect_agent_options():
    # assembles the sdk options for the architect: read-only tools, restricted to
    # exactly the tools above - no write/edit/bash - sandboxed to the shared
    # workspace directory and enforced by its allowlist hook
    agent_options = ClaudeAgentOptions(
        allowed_tools=ARCHITECT_AGENT_ALLOWED_TOOLS,
        system_prompt=ARCHITECT_AGENT_SYSTEM_PROMPT,
        model=ARCHITECT_AGENT_MODEL_NAME,
        cwd=TEAM_WORKSPACE_DIRECTORY_PATH,
        hooks={"PreToolUse": [HookMatcher(hooks=[check_tool_stays_in_workspace])]}
    )

    return agent_options


async def run_architect_query(planning_request):
    # runs one planning request through the architect end-to-end and returns its
    # final plan text once the sdk reports the run complete
    ensure_team_workspace_directory_exists()
    agent_options = _build_architect_agent_options()
    final_result_text = ""

    async for message in query(prompt=planning_request, options=agent_options):
        if isinstance(message, ResultMessage):
            final_result_text = message.result

    return final_result_text


def ask_architect(planning_request):
    # synchronous entry point for callers that aren't already running an asyncio event loop
    final_result_text = asyncio.run(run_architect_query(planning_request))
    return final_result_text
