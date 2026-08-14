# phase 4: the testing agent - security, correctness, and quality review. deliberately
# has no write/edit access: it reports what is wrong, it does not fix it itself.
#
# phase 6: same two-mode pattern as developer_agent.py - sandboxed to workspace/ by
# default (workspace_guard.py's allowlist), or the real project root with
# self_modification_guard.py's denylist when self_improvement_mode is True. never both
# hooks at once - see developer_agent.py's header comment for why

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, HookMatcher
from second_brain.config import TESTING_AGENT_MODEL_NAME, TEAM_WORKSPACE_DIRECTORY_PATH, PROJECT_ROOT_DIRECTORY
from second_brain.agents.team_workspace import ensure_team_workspace_directory_exists
from second_brain.agents.workspace_guard import check_tool_stays_in_workspace
from second_brain.agents.self_modification_guard import check_self_modification_is_safe
from second_brain.agents.testing_prompt import TESTING_AGENT_SYSTEM_PROMPT

READ_TOOL_NAME = "Read"
BASH_TOOL_NAME = "Bash"
GLOB_TOOL_NAME = "Glob"
GREP_TOOL_NAME = "Grep"
WEB_SEARCH_TOOL_NAME = "WebSearch"

TESTING_AGENT_ALLOWED_TOOLS = [READ_TOOL_NAME, BASH_TOOL_NAME, GLOB_TOOL_NAME, GREP_TOOL_NAME, WEB_SEARCH_TOOL_NAME]


def _build_testing_agent_options(self_improvement_mode):
    # assembles the sdk options for testing: read-only inspection tools plus bash (to
    # actually run tests/linters) and web search (to check known cves), with the
    # boundary and its enforcing hook chosen by mode
    if self_improvement_mode is True:
        agent_cwd = PROJECT_ROOT_DIRECTORY
        pre_tool_use_hook = check_self_modification_is_safe
    else:
        agent_cwd = TEAM_WORKSPACE_DIRECTORY_PATH
        pre_tool_use_hook = check_tool_stays_in_workspace

    agent_options = ClaudeAgentOptions(
        allowed_tools=TESTING_AGENT_ALLOWED_TOOLS,
        system_prompt=TESTING_AGENT_SYSTEM_PROMPT,
        model=TESTING_AGENT_MODEL_NAME,
        cwd=agent_cwd,
        hooks={"PreToolUse": [HookMatcher(hooks=[pre_tool_use_hook])]}
    )

    return agent_options


async def run_testing_query(review_request, self_improvement_mode=False):
    # runs one review request through testing end-to-end and returns its final report
    # once the sdk reports the run complete
    ensure_team_workspace_directory_exists()
    agent_options = _build_testing_agent_options(self_improvement_mode)
    final_result_text = ""

    async for message in query(prompt=review_request, options=agent_options):
        if isinstance(message, ResultMessage):
            final_result_text = message.result

    return final_result_text


def ask_testing_agent(review_request, self_improvement_mode=False):
    # synchronous entry point for callers that aren't already running an asyncio event loop
    final_result_text = asyncio.run(run_testing_query(review_request, self_improvement_mode))
    return final_result_text
