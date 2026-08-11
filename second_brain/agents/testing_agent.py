# phase 4: the testing agent - security, correctness, and quality review. deliberately
# has no write/edit access: it reports what is wrong, it does not fix it itself. shares
# developer's sandbox workspace (via cwd) so it can actually inspect real output, not a
# description of it

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from second_brain.config import TESTING_AGENT_MODEL_NAME, TEAM_WORKSPACE_DIRECTORY_PATH
from second_brain.agents.team_workspace import ensure_team_workspace_directory_exists

READ_TOOL_NAME = "Read"
BASH_TOOL_NAME = "Bash"
GLOB_TOOL_NAME = "Glob"
GREP_TOOL_NAME = "Grep"
WEB_SEARCH_TOOL_NAME = "WebSearch"

TESTING_AGENT_ALLOWED_TOOLS = [READ_TOOL_NAME, BASH_TOOL_NAME, GLOB_TOOL_NAME, GREP_TOOL_NAME, WEB_SEARCH_TOOL_NAME]

TESTING_AGENT_SYSTEM_PROMPT = (
    "You are Testing - a security and quality assurance expert. Your job is to find what "
    "is wrong before anyone else does: vulnerabilities, bugs, memory leaks, and anything "
    "that could fail in production.\n\n"
    "## Personality\n"
    "Skeptical by default - you assume code is broken or exploitable until you have "
    "verified otherwise. Direct and unsparing in what you report, but constructive: every "
    "finding comes with why it matters and, where obvious, how to fix it. You do not "
    "soften bad news to be polite, and you do not pad a clean report with manufactured "
    "nitpicks just to seem thorough.\n\n"
    "## What you check\n"
    "Security vulnerabilities (injection, unsafe deserialization, secrets in code, auth "
    "gaps), correctness bugs, resource and memory leaks, missing or swallowed error "
    "handling, and - when relevant - known vulnerabilities in dependencies (use web "
    "search to check).\n\n"
    "## Rules\n"
    "- You review and report. You do not fix issues yourself - you have no write or edit "
    "tools, and that is intentional: fixing is Developer's job on the next pass.\n"
    "- Rank findings by severity; lead with the worst one.\n"
    "- If you find nothing wrong after a genuine check, say so plainly - do not invent "
    "problems to look thorough."
)


def _build_testing_agent_options():
    # assembles the sdk options for testing: read-only inspection tools plus bash (to
    # actually run tests/linters) and web search (to check known cves), scoped by cwd
    # to the same sandbox workspace developer builds in
    agent_options = ClaudeAgentOptions(
        allowed_tools=TESTING_AGENT_ALLOWED_TOOLS,
        system_prompt=TESTING_AGENT_SYSTEM_PROMPT,
        model=TESTING_AGENT_MODEL_NAME,
        cwd=TEAM_WORKSPACE_DIRECTORY_PATH
    )

    return agent_options


async def run_testing_query(review_request):
    # runs one review request through testing end-to-end and returns its final report
    # once the sdk reports the run complete
    ensure_team_workspace_directory_exists()
    agent_options = _build_testing_agent_options()
    final_result_text = ""

    async for message in query(prompt=review_request, options=agent_options):
        if isinstance(message, ResultMessage):
            final_result_text = message.result

    return final_result_text


def ask_testing_agent(review_request):
    # synchronous entry point for callers that aren't already running an asyncio event loop
    final_result_text = asyncio.run(run_testing_query(review_request))
    return final_result_text
