# the only module that touches terminal input/output for the agent team, mirroring
# research_cli.py's i/o-ownership convention for its own entry point

import sys
from second_brain.orchestrator import (
    handle_architect_request,
    handle_research_request,
    handle_developer_request,
    handle_testing_request,
    handle_analytics_request
)
from second_brain.dashboard import run_store, run_trigger

TERMINAL_PROMPT_TEXT = "Team request: "
EXIT_MESSAGE = "Ending team session."
DEFAULT_EXIT_COMMAND = "exit"
EXIT_COMMANDS = {DEFAULT_EXIT_COMMAND, "quit"}

AGENT_PREFIX_SEPARATOR = ":"
ARCHITECT_PREFIX = "architect"
RESEARCH_PREFIX = "research"
DEVELOPER_PREFIX = "developer"
TESTING_PREFIX = "testing"
ANALYTICS_PREFIX = "analytics"

HELP_MESSAGE = (
    "Type a goal to run it through the whole team (Architect -> Research -> Developer "
    "-> Testing -> Analytics), or prefix your message with one agent's name and a colon "
    "to talk to it directly, e.g. 'architect: plan a REST API for a todo app'.\n"
    "Agents: architect, research, developer, testing, analytics."
)


def _prompt_user_for_request():
    # reads a single line of input from the terminal; the only place stdin is touched.
    # a closed stdin is treated as an exit command rather than crashing
    try:
        user_answer = input(TERMINAL_PROMPT_TEXT)
    except EOFError:
        user_answer = DEFAULT_EXIT_COMMAND
    return user_answer


def _is_exit_command(user_answer):
    # matches exit commands regardless of surrounding whitespace or letter case
    lower_case_answer = user_answer.strip().lower()
    return lower_case_answer in EXIT_COMMANDS


def _split_agent_prefix(user_request):
    # splits a leading "agentname:" prefix off the request, if present; returns
    # (agent_prefix, remaining_text) with agent_prefix as None if no known prefix matched
    separator_index = user_request.find(AGENT_PREFIX_SEPARATOR)

    if separator_index == -1:
        return None, user_request

    possible_prefix = user_request[:separator_index].strip().lower()
    remaining_text = user_request[separator_index + 1:].strip()

    if possible_prefix == ARCHITECT_PREFIX:
        return ARCHITECT_PREFIX, remaining_text
    if possible_prefix == RESEARCH_PREFIX:
        return RESEARCH_PREFIX, remaining_text
    if possible_prefix == DEVELOPER_PREFIX:
        return DEVELOPER_PREFIX, remaining_text
    if possible_prefix == TESTING_PREFIX:
        return TESTING_PREFIX, remaining_text
    if possible_prefix == ANALYTICS_PREFIX:
        return ANALYTICS_PREFIX, remaining_text

    return None, user_request


def _print_stage_result(stage_result):
    # prints one pipeline stage's output as soon as it completes, so the user sees
    # progress instead of waiting silently through all five agents
    print("\n=== " + stage_result.agent_name + " ===")
    print(stage_result.output_text)


def _run_full_pipeline_with_persistence(goal):
    # runs the full pipeline via the shared run_trigger module, which persists
    # progress to the dashboard's run_store as it goes. run_store writes are local
    # sqlite, never network, so this never depends on a dashboard server actually
    # being up - the cli works identically either way
    try:
        run_trigger.start_run(goal, run_trigger.TEAM_PIPELINE_MODE, on_stage_complete=_print_stage_result)
    except (Exception, KeyboardInterrupt) as pipeline_error:
        # a plain except Exception would not catch ctrl+c, the single most likely
        # real-world way a run gets abandoned mid-flight for a solo local user
        print("\n" + str(pipeline_error))


def _handle_single_agent_request(agent_prefix, remaining_text):
    # dispatches a prefixed request to exactly one agent and prints its answer
    display_name = agent_prefix.capitalize()
    print("\n" + display_name + " is working...")

    if agent_prefix == ARCHITECT_PREFIX:
        agent_answer = handle_architect_request(remaining_text)
    elif agent_prefix == RESEARCH_PREFIX:
        agent_answer = handle_research_request(remaining_text)
    elif agent_prefix == DEVELOPER_PREFIX:
        agent_answer = handle_developer_request(remaining_text)
    elif agent_prefix == TESTING_PREFIX:
        agent_answer = handle_testing_request(remaining_text)
    else:
        agent_answer = handle_analytics_request(remaining_text)

    print("\n" + agent_answer)


def run_team_cli():
    # main loop: ask for a goal (runs the whole team) or a single-agent request, print
    # results, and repeat until the user exits

    # windows terminals often default to a legacy codepage (e.g. cp1252) that cannot
    # encode characters an agent's answer may contain; reconfiguring stdout to utf-8
    # stops printing from crashing on those answers, matching cli.py's fix
    sys.stdout.reconfigure(encoding="utf-8")
    run_store.initialize_database()

    print(HELP_MESSAGE)
    user_request = _prompt_user_for_request()

    while not _is_exit_command(user_request):
        agent_prefix, remaining_text = _split_agent_prefix(user_request)

        if agent_prefix is None:
            _run_full_pipeline_with_persistence(user_request)
        else:
            _handle_single_agent_request(agent_prefix, remaining_text)

        print()
        user_request = _prompt_user_for_request()

    print(EXIT_MESSAGE)


if __name__ == "__main__":
    run_team_cli()
