# phase 4: the architect agent - turns a goal into a scoped plan and hands it to
# research. plans only; no write/edit/bash, so it can never build anything itself.
#
# phase 6 fix: this agent previously set no cwd at all, which the claude agent sdk
# resolves by inheriting the spawning process's own working directory - the real
# project root, in every normal invocation (team_cli.py is documented to run from
# there). combined with unrestricted Read/Glob/Grep, that meant Read(".env") worked
# with nothing stopping it. now cwd is explicit rather than inherited-by-accident,
# and the self-modification guard's read-side checks are always registered here
# regardless of pipeline mode, since architect's job is to see the real project for
# planning purposes but it must never be able to see secrets or safety wiring

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, HookMatcher
from second_brain.config import ARCHITECT_AGENT_MODEL_NAME, PROJECT_ROOT_DIRECTORY
from second_brain.agents.self_modification_guard import check_self_modification_is_safe
from second_brain.agents.architect_prompt import ARCHITECT_AGENT_SYSTEM_PROMPT

READ_TOOL_NAME = "Read"
GLOB_TOOL_NAME = "Glob"
GREP_TOOL_NAME = "Grep"

ARCHITECT_AGENT_ALLOWED_TOOLS = [READ_TOOL_NAME, GLOB_TOOL_NAME, GREP_TOOL_NAME]


def _build_architect_agent_options():
    # assembles the sdk options for the architect: read-only tools, restricted to
    # exactly the tools above - no write/edit/bash
    agent_options = ClaudeAgentOptions(
        allowed_tools=ARCHITECT_AGENT_ALLOWED_TOOLS,
        system_prompt=ARCHITECT_AGENT_SYSTEM_PROMPT,
        model=ARCHITECT_AGENT_MODEL_NAME,
        cwd=PROJECT_ROOT_DIRECTORY,
        hooks={"PreToolUse": [HookMatcher(hooks=[check_self_modification_is_safe])]}
    )

    return agent_options


async def run_architect_query(planning_request):
    # runs one planning request through the architect end-to-end and returns its
    # final plan text once the sdk reports the run complete
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
