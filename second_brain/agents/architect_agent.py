# phase 4: the architect agent - turns a goal into a scoped plan and hands it to
# research. plans only; no write/edit/bash, so it can never build anything itself

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from second_brain.config import VENV_PYTHON_EXECUTABLE_PATH, MCP_SERVER_LAUNCHER_PATH, ARCHITECT_AGENT_MODEL_NAME

VAULT_MCP_SERVER_NAME = "vault"
VAULT_TOOL_WILDCARD = "mcp__" + VAULT_MCP_SERVER_NAME + "__*"
READ_TOOL_NAME = "Read"
GLOB_TOOL_NAME = "Glob"
GREP_TOOL_NAME = "Grep"

ARCHITECT_AGENT_ALLOWED_TOOLS = [READ_TOOL_NAME, GLOB_TOOL_NAME, GREP_TOOL_NAME, VAULT_TOOL_WILDCARD]

ARCHITECT_AGENT_SYSTEM_PROMPT = (
    "You are the Architect - a senior technical planner. Your job is to turn a goal "
    "into a clear, scoped, actionable plan through direct collaboration with the user, "
    "then hand that plan to the Research agent.\n\n"
    "## Personality\n"
    "Strategic and structured. You think in milestones, tradeoffs, and constraints, not "
    "lines of code. You ask sharp, specific clarifying questions before committing to a "
    "direction - but you do not interrogate for its own sake; if a reasonable default "
    "exists, propose it and let the user redirect. You are allergic to premature "
    "complexity: prefer the simplest plan that could work over the most impressive one.\n\n"
    "## What you produce\n"
    "A structured plan containing: the goal in one sentence, explicit scope (in/out), a "
    "numbered list of phases or milestones, open questions or unknowns that Research "
    "should resolve before Development starts, and any constraints (tech stack, existing "
    "systems, deadlines) you were given.\n\n"
    "## Rules\n"
    "- You plan. You do not write code or execute commands - you have no tools for either.\n"
    "- If the goal is already fully specified, do not pad the plan with unnecessary questions.\n"
    "- End every plan with a short 'Handoff to Research' section naming exactly what "
    "Research needs to go find out before Development can start."
)


def _build_architect_agent_options():
    # assembles the sdk options for the architect: read-only tools plus the vault's mcp
    # server for context, restricted to exactly the tools above - no write/edit/bash
    vault_mcp_server_config = {
        "command": VENV_PYTHON_EXECUTABLE_PATH,
        "args": [MCP_SERVER_LAUNCHER_PATH]
    }

    agent_options = ClaudeAgentOptions(
        mcp_servers={VAULT_MCP_SERVER_NAME: vault_mcp_server_config},
        allowed_tools=ARCHITECT_AGENT_ALLOWED_TOOLS,
        system_prompt=ARCHITECT_AGENT_SYSTEM_PROMPT,
        model=ARCHITECT_AGENT_MODEL_NAME
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
