# the only module that touches terminal input/output

import sys
import uuid
from second_brain.vault.semantic_search import search_notes_by_semantic_similarity
from second_brain.claude.client import ask_claude_about_vault
from second_brain.conversation_history import load_conversation_history, append_turns_to_history
from second_brain.assistant_memory import save_session_to_memory
from second_brain.config import MAXIMUM_NOTES_TO_INCLUDE, MAXIMUM_HISTORY_TURNS_FOR_CONTEXT
from second_brain.types import ConversationTurn, PipelineStageResult
from second_brain.dashboard import run_store

ASSISTANT_STAGE_NAME = "Topher"
TERMINAL_PROMPT_TEXT = "Ask your vault: "
NO_MATCHES_MESSAGE = "No matching notes found. Answering from general knowledge only."
SAVING_MEMORY_MESSAGE = "Saving this session to long-term memory..."
EXIT_MESSAGE = "Ending session. Your conversation has been saved."
DEFAULT_EXIT_COMMAND = "exit"
EXIT_COMMANDS = {DEFAULT_EXIT_COMMAND, "quit"}


def _prompt_user_for_question():
    # reads a single line of input from the terminal; the only place stdin is touched.
    # a closed stdin (piped input ending, Ctrl+D/Ctrl+Z) is treated as an exit command
    # rather than crashing, since that is a real and common way this loop ends
    try:
        user_answer = input(TERMINAL_PROMPT_TEXT)
    except EOFError:
        user_answer = DEFAULT_EXIT_COMMAND
    return user_answer


def _print_answer(claude_answer):
    # prints the final answer, its sources, and any vault writes it made along the way;
    # the only place stdout is touched
    print("\nAnswer:\n" + claude_answer.response_text)

    if len(claude_answer.source_notes) > 0:
        print("\nSources: " + ", ".join(claude_answer.source_notes))

    if len(claude_answer.vault_actions) > 0:
        print("\nVault changes:")
        for action_index in range(len(claude_answer.vault_actions)):
            print("- " + claude_answer.vault_actions[action_index])


def _is_exit_command(user_answer):
    # matches exit commands regardless of surrounding whitespace or letter case
    lower_case_answer = user_answer.strip().lower()
    return lower_case_answer in EXIT_COMMANDS


def _most_recent_turns(all_turns):
    # only the most recent turns are replayed to claude each call, to keep token usage
    # bounded; the full history still stays on disk regardless of this window
    start_index = max(0, len(all_turns) - MAXIMUM_HISTORY_TURNS_FOR_CONTEXT)
    recent_turns = []

    for turn_index in range(start_index, len(all_turns)):
        recent_turns.append(all_turns[turn_index])

    return recent_turns


def _find_most_recent_user_turn(conversation_turns):
    # scans the whole history for the last turn the user asked, if any
    most_recent_user_turn = None

    for turn_index in range(len(conversation_turns)):
        current_turn = conversation_turns[turn_index]
        if current_turn.role == "user":
            most_recent_user_turn = current_turn

    return most_recent_user_turn


def _build_search_query(user_question, conversation_turns):
    # follow-up questions are often elliptical ("which one should I start with?"),
    # which alone doesn't give the vector search enough to retrieve the right notes;
    # folding in the previous question gives it that missing context
    most_recent_user_turn = _find_most_recent_user_turn(conversation_turns)

    if most_recent_user_turn is None:
        return user_question

    return most_recent_user_turn.content + " " + user_question


def _ask_with_persistence(user_question, matching_notes, recent_turns):
    # runs one vault_qa turn through claude, persisting it to the dashboard's run_store
    # as a one-stage run - same try/except-and-mark-error shape as team_cli.py's
    # _run_full_pipeline_with_persistence, just for a single stage instead of five.
    # local sqlite writes only, so this behaves identically whether the dashboard
    # server is up or not
    run_id = uuid.uuid4().hex
    run_store.create_run(run_id, user_question, run_type=run_store.VAULT_QA_RUN_TYPE)

    try:
        claude_answer = ask_claude_about_vault(user_question, matching_notes, recent_turns)
        stage_result = PipelineStageResult(agent_name=ASSISTANT_STAGE_NAME, output_text=claude_answer.response_text)
        run_store.record_stage_result(run_id, stage_result)
        run_store.mark_run_finished(run_id, run_store.RUN_STATUS_DONE)
        return claude_answer
    except (Exception, KeyboardInterrupt):
        run_store.mark_run_finished(run_id, run_store.RUN_STATUS_ERROR)
        raise


def run_command_line_assistant():
    # main loop: ask a question, search the vault, get an answer, print it, save it,
    # and repeat until the user exits; conversation history persists across runs too

    # windows terminals often default to a legacy codepage (e.g. cp1252) that cannot
    # encode characters claude's answers may contain, such as emoji; reconfiguring
    # stdout to utf-8 stops printing from crashing on those answers
    sys.stdout.reconfigure(encoding="utf-8")
    run_store.initialize_database()

    conversation_turns = load_conversation_history()
    session_turns = []
    user_question = _prompt_user_for_question()

    while not _is_exit_command(user_question):
        search_query = _build_search_query(user_question, conversation_turns)
        matching_notes = search_notes_by_semantic_similarity(search_query, MAXIMUM_NOTES_TO_INCLUDE)

        if len(matching_notes) == 0:
            print(NO_MATCHES_MESSAGE)

        recent_turns = _most_recent_turns(conversation_turns)
        claude_answer = _ask_with_persistence(user_question, matching_notes, recent_turns)
        _print_answer(claude_answer)

        new_turns = [
            ConversationTurn(role="user", content=user_question),
            ConversationTurn(role="assistant", content=claude_answer.response_text)
        ]
        conversation_turns = append_turns_to_history(conversation_turns, new_turns)

        for turn_index in range(len(new_turns)):
            session_turns.append(new_turns[turn_index])

        print()
        user_question = _prompt_user_for_question()

    if len(session_turns) > 0:
        print(SAVING_MEMORY_MESSAGE)
        save_session_to_memory(session_turns)

    print(EXIT_MESSAGE)


if __name__ == "__main__":
    run_command_line_assistant()
