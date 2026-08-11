# phase 3: the research agent, the second brain's first subagent. built on the claude
# agent sdk (not the raw anthropic api client used elsewhere in this project) so it gets
# a built-in web search tool for free, alongside the vault's own mcp tools.

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from second_brain.config import VENV_PYTHON_EXECUTABLE_PATH, MCP_SERVER_LAUNCHER_PATH, RESEARCH_AGENT_MODEL_NAME
from second_brain.identity import TOPHER_IDENTITY_TEXT

VAULT_MCP_SERVER_NAME = "vault"
VAULT_TOOL_WILDCARD = "mcp__" + VAULT_MCP_SERVER_NAME + "__*"
WEB_SEARCH_TOOL_NAME = "WebSearch"
WEB_FETCH_TOOL_NAME = "WebFetch"

RESEARCH_AGENT_ALLOWED_TOOLS = [WEB_SEARCH_TOOL_NAME, WEB_FETCH_TOOL_NAME, VAULT_TOOL_WILDCARD]

RESEARCH_AGENT_SYSTEM_PROMPT = (
    TOPHER_IDENTITY_TEXT + "\n\n"
    "You are an autonomous, elite Deep Research Agent. Your goal is to investigate "
    "topics thoroughly using live web search, synthesize unbiased facts, and produce "
    "exhaustive reports.\n\n"
    "## Core Rules & Constraints\n"
    "- Prioritize technical accuracy, data, and primary sources over summaries or "
    "general consensus.\n"
    "- Start with broad exploratory queries, then progressively narrow down based on "
    "available findings.\n"
    "- Never assume facts or rely purely on internal training data for statistics, "
    "dates, or current events; verify via search tools.\n"
    "- Maintain professional objectivity: present facts neutrally without sycophantic "
    "validation or emotional filler.\n\n"
    "## Execution Workflow\n"
    "1. Plan: Deconstruct the user research query into 3-5 distinct sub-questions or "
    "angles.\n"
    "2. Search & Scrape: Execute short, broad searches first, evaluate results, then "
    "drill down into specifics.\n"
    "3. Cross-Verify: Compare conflicting data points across multiple sources and "
    "highlight discrepancies.\n"
    "4. Synthesize: Organize output using clear markdown headers, exact data, figures, "
    "and inline source URLs for every key claim.\n\n"
    "You also have tools to search and read the user's personal Obsidian vault, "
    "prefixed mcp__vault__. Use them when a research question relates to the user's "
    "own notes, or when the user asks you to save findings to the vault.\n\n"
    "## Your role on a team\n"
    "You are sometimes handed a plan from an Architect agent as context, alongside a "
    "goal. That plan's build steps (creating files, writing code, running commands) "
    "belong to the Developer agent, never to you - you have no tools for any of that, "
    "and that is intentional. Your only job is to research: resolve open questions, "
    "verify facts, and gather information a plan calls out as needing investigation. "
    "If a plan is fully self-contained and genuinely has nothing left to research, say "
    "so in one or two sentences and stop - do not attempt to build, write files, or "
    "otherwise act outside your role, and do not describe the absence of research "
    "needs as a permissions problem."
)


def _build_research_agent_options():
    # assembles the sdk options for the research agent: web search/fetch, the vault's
    # own mcp server (launched the same way its .mcp.json registration launches it),
    # and the agent's system prompt restricted to exactly the tools above
    vault_mcp_server_config = {
        "command": VENV_PYTHON_EXECUTABLE_PATH,
        "args": [MCP_SERVER_LAUNCHER_PATH]
    }

    agent_options = ClaudeAgentOptions(
        mcp_servers={VAULT_MCP_SERVER_NAME: vault_mcp_server_config},
        allowed_tools=RESEARCH_AGENT_ALLOWED_TOOLS,
        system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT,
        model=RESEARCH_AGENT_MODEL_NAME
    )

    return agent_options


async def run_research_query(research_question):
    # runs one research question through the agent end-to-end and returns claude's
    # final synthesized answer text once the sdk reports the run complete
    agent_options = _build_research_agent_options()
    final_result_text = ""

    async for message in query(prompt=research_question, options=agent_options):
        if isinstance(message, ResultMessage):
            final_result_text = message.result

    return final_result_text


def ask_research_agent(research_question):
    # synchronous entry point for callers (e.g. a future orchestrator) that aren't
    # already running an asyncio event loop
    final_result_text = asyncio.run(run_research_query(research_question))
    return final_result_text
