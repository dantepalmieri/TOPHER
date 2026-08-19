# phase 3: the research agent, the second brain's first subagent. built on the claude
# agent sdk (not a raw api client) so it gets a built-in web search tool for free.

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from second_brain.config import RESEARCH_AGENT_MODEL_NAME
from second_brain.agents.research_prompt import RESEARCH_AGENT_SYSTEM_PROMPT

WEB_SEARCH_TOOL_NAME = "WebSearch"
WEB_FETCH_TOOL_NAME = "WebFetch"

RESEARCH_AGENT_ALLOWED_TOOLS = [WEB_SEARCH_TOOL_NAME, WEB_FETCH_TOOL_NAME]


def _build_research_agent_options():
    # assembles the sdk options for the research agent: web search/fetch and the
    # agent's system prompt, restricted to exactly the tools above
    agent_options = ClaudeAgentOptions(
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
