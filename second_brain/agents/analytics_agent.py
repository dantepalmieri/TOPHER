# phase 4: the analytics agent - the data and metrics expert. calculates, organizes, and
# reports on what the rest of the team produced. shares the sandbox workspace (via cwd)
# plus the vault's mcp tools, since organizing often means writing findings back to notes

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from second_brain.config import (
    ANALYTICS_AGENT_MODEL_NAME,
    TEAM_WORKSPACE_DIRECTORY_PATH,
    VENV_PYTHON_EXECUTABLE_PATH,
    MCP_SERVER_LAUNCHER_PATH
)
from second_brain.agents.team_workspace import ensure_team_workspace_directory_exists

VAULT_MCP_SERVER_NAME = "vault"
VAULT_TOOL_WILDCARD = "mcp__" + VAULT_MCP_SERVER_NAME + "__*"
READ_TOOL_NAME = "Read"
WRITE_TOOL_NAME = "Write"
BASH_TOOL_NAME = "Bash"

ANALYTICS_AGENT_ALLOWED_TOOLS = [READ_TOOL_NAME, WRITE_TOOL_NAME, BASH_TOOL_NAME, VAULT_TOOL_WILDCARD]

ANALYTICS_AGENT_SYSTEM_PROMPT = (
    "You are Analytics - the data and metrics expert. You calculate, organize, and make "
    "sense of numbers and structured information: measuring progress against a plan, "
    "analyzing what the rest of the team produced, and keeping it organized.\n\n"
    "## Personality\n"
    "Precise and quantitative. You default to tables, exact figures, and clearly labeled "
    "units over prose summaries. You show your work for any calculation - the formula or "
    "method, not just the result - and you flag plainly when you do not have enough data "
    "to answer accurately, rather than estimating and presenting it as fact.\n\n"
    "## Rules\n"
    "- Never present an estimate as a measured fact - label projections and assumptions "
    "explicitly.\n"
    "- Use your bash tool for actual calculations rather than doing arithmetic in your "
    "head - visible, checkable work beats a guessed number.\n"
    "- When organizing information (findings, results, notes), impose clear structure: "
    "headers, tables, and consistent units."
)


def _build_analytics_agent_options():
    # assembles the sdk options for analytics: read/write/bash for calculations and
    # reports, scoped by cwd to the sandbox workspace, plus the vault's mcp tools for
    # organizing findings back into notes
    vault_mcp_server_config = {
        "command": VENV_PYTHON_EXECUTABLE_PATH,
        "args": [MCP_SERVER_LAUNCHER_PATH]
    }

    agent_options = ClaudeAgentOptions(
        mcp_servers={VAULT_MCP_SERVER_NAME: vault_mcp_server_config},
        allowed_tools=ANALYTICS_AGENT_ALLOWED_TOOLS,
        system_prompt=ANALYTICS_AGENT_SYSTEM_PROMPT,
        model=ANALYTICS_AGENT_MODEL_NAME,
        cwd=TEAM_WORKSPACE_DIRECTORY_PATH
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
