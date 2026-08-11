# the only module that touches terminal input/output for the research agent, mirroring
# cli.py's i/o-ownership convention for its own separate entry point

import sys
from second_brain.orchestrator import handle_research_request

TERMINAL_PROMPT_TEXT = "Research question: "
SEARCHING_MESSAGE = "Researching..."
EXIT_MESSAGE = "Ending research session."
DEFAULT_EXIT_COMMAND = "exit"
EXIT_COMMANDS = {DEFAULT_EXIT_COMMAND, "quit"}


def _prompt_user_for_question():
    # reads a single line of input from the terminal; the only place stdin is touched.
    # a closed stdin (piped input ending, Ctrl+D/Ctrl+Z) is treated as an exit command
    # rather than crashing, matching cli.py's behavior
    try:
        user_answer = input(TERMINAL_PROMPT_TEXT)
    except EOFError:
        user_answer = DEFAULT_EXIT_COMMAND
    return user_answer


def _is_exit_command(user_answer):
    # matches exit commands regardless of surrounding whitespace or letter case
    lower_case_answer = user_answer.strip().lower()
    return lower_case_answer in EXIT_COMMANDS


def run_research_cli():
    # main loop: ask a research question, run it through the orchestrator, print the
    # answer, and repeat until the user exits

    # windows terminals often default to a legacy codepage (e.g. cp1252) that cannot
    # encode characters claude's answers may contain; reconfiguring stdout to utf-8
    # stops printing from crashing on those answers, matching cli.py's fix
    sys.stdout.reconfigure(encoding="utf-8")

    user_question = _prompt_user_for_question()

    while not _is_exit_command(user_question):
        print(SEARCHING_MESSAGE)
        research_answer = handle_research_request(user_question)
        print("\n" + research_answer)
        print()
        user_question = _prompt_user_for_question()

    print(EXIT_MESSAGE)


if __name__ == "__main__":
    run_research_cli()
