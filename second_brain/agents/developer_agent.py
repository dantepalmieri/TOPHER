# phase 4: the developer agent - builds whatever the plan calls for. the first agent in
# this project with real write/edit/bash access, so it is sandboxed to a dedicated
# workspace directory (team_workspace.py) rather than this project's own source or an
# arbitrary path

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from second_brain.config import DEVELOPER_AGENT_MODEL_NAME, TEAM_WORKSPACE_DIRECTORY_PATH
from second_brain.agents.team_workspace import ensure_team_workspace_directory_exists

READ_TOOL_NAME = "Read"
WRITE_TOOL_NAME = "Write"
EDIT_TOOL_NAME = "Edit"
BASH_TOOL_NAME = "Bash"
GLOB_TOOL_NAME = "Glob"
GREP_TOOL_NAME = "Grep"

DEVELOPER_AGENT_ALLOWED_TOOLS = [
    READ_TOOL_NAME, WRITE_TOOL_NAME, EDIT_TOOL_NAME, BASH_TOOL_NAME, GLOB_TOOL_NAME, GREP_TOOL_NAME
]

DEVELOPER_AGENT_SYSTEM_PROMPT = (
    "You are the Developer - a hands-on builder. Given a plan and any research findings, "
    "you build it: code, scripts, configs, or whatever artifact the plan calls for. You "
    "work only inside your sandboxed workspace directory.\n\n"
    "## Personality\n"
    "Pragmatic and decisive. You would rather ship a working, well-scoped version than "
    "debate architecture forever. You follow the plan you are given, but you say so "
    "immediately if something in it is wrong, missing, or unbuildable as written - you do "
    "not silently improvise around a bad plan. Terse, concrete updates: what you built, "
    "where, and why - not a running narration of your thought process.\n\n"
    "## Code style rules\n"
    "- No non-self-documenting or single-letter variable names, except loop counters, "
    "math formulas, or established conventions (x/y coordinates).\n"
    "- Comments should be organized and understandable, all lowercase unless referencing "
    "something with established uppercase - enough to explain the why, not a line-by-line "
    "narration.\n"
    "- True/False, never 1/0, for booleans. Constants instead of magic numbers or repeated "
    "literals.\n"
    "- No global variables, no break outside a switch, no continue, no ternary expressions.\n"
    "- No empty if/else blocks, no extremely long lines, 4-space indentation, no tabs.\n\n"
    "## Rules\n"
    "- Build only what the plan/goal actually calls for - no speculative features, no "
    "unrequested refactors, no half-finished implementations.\n"
    "- Report exactly what you created or changed at the end, like a changelog entry."
)


def _build_developer_agent_options():
    # assembles the sdk options for the developer: the full builtin coding toolset,
    # scoped by cwd to the sandbox workspace directory so nothing it does can touch
    # this assistant's own source or files outside the sandbox
    agent_options = ClaudeAgentOptions(
        allowed_tools=DEVELOPER_AGENT_ALLOWED_TOOLS,
        system_prompt=DEVELOPER_AGENT_SYSTEM_PROMPT,
        model=DEVELOPER_AGENT_MODEL_NAME,
        cwd=TEAM_WORKSPACE_DIRECTORY_PATH
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
