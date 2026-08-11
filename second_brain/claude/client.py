# builds prompts from vault context and calls the Claude API

import anthropic
from second_brain.config import CLAUDE_MODEL_NAME, CLAUDE_MAX_TOKENS, SUMMARIZATION_MAX_TOKENS, OBSIDIAN_VAULT_PATH
from second_brain.types import ClaudeAnswer
from second_brain.vault.vault_reader import find_note_file_path_by_title
from second_brain.vault.vault_writer import create_note, append_to_note

anthropic_client = anthropic.Anthropic()

SUMMARIZATION_INSTRUCTION = (
    "Summarize the conversation above in 2-4 sentences for long-term memory. "
    "Focus on decisions, facts, or preferences worth remembering later - skip "
    "pleasantries and skip anything that's just restating the vault notes themselves."
)

CREATE_NOTE_TOOL_NAME = "create_note"
APPEND_TO_NOTE_TOOL_NAME = "append_to_note"

CREATE_NOTE_TOOL = {
    "name": CREATE_NOTE_TOOL_NAME,
    "description": (
        "Creates a brand-new note in the user's Obsidian vault with the given title "
        "and body text. Fails if a note with this exact title already exists - use "
        "append_to_note instead if you want to add to an existing note."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The title of the new note (used as the filename)."
            },
            "body_text": {
                "type": "string",
                "description": "The full body content of the new note."
            }
        },
        "required": ["title", "body_text"]
    }
}

APPEND_TO_NOTE_TOOL = {
    "name": APPEND_TO_NOTE_TOOL_NAME,
    "description": (
        "Appends text to the end of an existing note in the user's Obsidian vault, "
        "given its title. Fails if no note with this title exists - use create_note "
        "instead if it doesn't exist yet."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The exact title of the existing note to append to."
            },
            "text_to_append": {
                "type": "string",
                "description": "The text to add to the end of the note."
            }
        },
        "required": ["title", "text_to_append"]
    }
}

VAULT_WRITE_TOOLS = [CREATE_NOTE_TOOL, APPEND_TO_NOTE_TOOL]


def _build_prompt_with_context(user_question, context_notes):
    # builds a single prompt string that gives claude the user question plus vault context
    context_section = ""

    for note_index in range(len(context_notes)):
        current_note = context_notes[note_index]
        context_section = context_section + "### Note: " + current_note.title + "\n" + current_note.content + "\n\n"

    introduction_line = (
        "Some of my notes that may be relevant to this question are below. "
        "Use them together with our conversation so far, not instead of it - "
        "if the notes below don't cover something we already discussed, "
        "rely on the earlier turns of this conversation. You also have tools to "
        "create a new note or append to an existing one - only use them when I "
        "clearly ask you to save, record, add, or create something in my notes, "
        "not just because it seems helpful.\n\n"
    )
    question_line = "Question: " + user_question
    full_prompt = introduction_line + context_section + question_line

    return full_prompt


def _extract_source_titles(context_notes):
    # extracts the source titles from a list of notes, for citing what was used
    source_titles = []

    for note_index in range(len(context_notes)):
        source_titles.append(context_notes[note_index].title)

    return source_titles


def _build_message_list(prior_turns, latest_user_content):
    # replays prior conversation turns (plain question/answer text, no vault context)
    # ahead of the latest user message, which carries this turn's vault context
    message_list = []

    for turn_index in range(len(prior_turns)):
        current_turn = prior_turns[turn_index]
        message_list.append({"role": current_turn.role, "content": current_turn.content})

    message_list.append({"role": "user", "content": latest_user_content})

    return message_list


def _extract_response_text(response):
    # extracts the plain text from a claude response's first content block
    first_content_block = response.content[0]
    response_text = ""

    if first_content_block.type == "text":
        response_text = first_content_block.text

    return response_text


def _call_claude(message_list, max_tokens):
    # sends a message list to claude and extracts the plain text of its reply
    response = anthropic_client.messages.create(
        model=CLAUDE_MODEL_NAME,
        max_tokens=max_tokens,
        messages=message_list
    )
    response_text = _extract_response_text(response)
    return response_text


def _execute_create_note(tool_input):
    # creates a note, reporting a failed duplicate title back to claude as a tool
    # error instead of letting the exception crash the conversation
    note_title = tool_input["title"]
    body_text = tool_input["body_text"]

    try:
        created_file_path = create_note(note_title, body_text)
    except FileExistsError as file_exists_error:
        return str(file_exists_error), True

    result_text = "Created note '" + note_title + "' at " + created_file_path
    return result_text, False


def _execute_append_to_note(tool_input):
    # resolves a note title to its file path before appending, so claude never
    # has to know or guess a raw filesystem path
    note_title = tool_input["title"]
    text_to_append = tool_input["text_to_append"]
    file_path = find_note_file_path_by_title(OBSIDIAN_VAULT_PATH, note_title)

    if file_path is None:
        result_text = "No note titled '" + note_title + "' exists in the vault."
        return result_text, True

    append_to_note(file_path, text_to_append)
    result_text = "Appended to note '" + note_title + "'"
    return result_text, False


def _execute_vault_write_tool(tool_name, tool_input):
    # dispatches a single tool_use block to the matching vault_writer operation
    if tool_name == CREATE_NOTE_TOOL_NAME:
        result_text, is_error = _execute_create_note(tool_input)
    else:
        result_text, is_error = _execute_append_to_note(tool_input)

    return result_text, is_error


def _execute_tool_use_blocks(content_blocks, vault_actions):
    # executes every tool_use block in an assistant response, records a human-readable
    # description of each in vault_actions, and returns the tool_result content to
    # send back to claude
    tool_result_content = []

    for block_index in range(len(content_blocks)):
        current_block = content_blocks[block_index]

        if current_block.type == "tool_use":
            result_text, is_error = _execute_vault_write_tool(current_block.name, current_block.input)
            vault_actions.append(result_text)
            new_tool_result = {
                "type": "tool_result",
                "tool_use_id": current_block.id,
                "content": result_text,
                "is_error": is_error
            }
            tool_result_content.append(new_tool_result)

    return tool_result_content


def _run_conversation_with_tools(message_list):
    # runs the claude conversation loop, executing any vault-write tool calls claude
    # makes along the way, until claude produces a final text answer
    vault_actions = []
    keep_looping = True
    response = None

    while keep_looping:
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL_NAME,
            max_tokens=CLAUDE_MAX_TOKENS,
            tools=VAULT_WRITE_TOOLS,
            messages=message_list
        )

        if response.stop_reason == "tool_use":
            message_list.append({"role": "assistant", "content": response.content})
            tool_result_content = _execute_tool_use_blocks(response.content, vault_actions)
            message_list.append({"role": "user", "content": tool_result_content})
        else:
            keep_looping = False

    response_text = _extract_response_text(response)
    return response_text, vault_actions


def ask_claude_about_vault(user_question, context_notes, prior_turns):
    # sends the conversation so far plus this turn's vault context to claude, letting
    # it create/append vault notes via tool calls if appropriate, and returns the
    # final answer plus sources used and any vault writes performed
    prompt_text = _build_prompt_with_context(user_question, context_notes)
    message_list = _build_message_list(prior_turns, prompt_text)
    response_text, vault_actions = _run_conversation_with_tools(message_list)

    claude_answer = ClaudeAnswer(
        response_text=response_text,
        source_notes=_extract_source_titles(context_notes),
        vault_actions=vault_actions
    )

    return claude_answer


def summarize_conversation_for_memory(session_turns):
    # distills a conversation session into a short summary for long-term memory,
    # rather than storing the raw back-and-forth verbatim
    message_list = _build_message_list(session_turns, SUMMARIZATION_INSTRUCTION)
    summary_text = _call_claude(message_list, SUMMARIZATION_MAX_TOKENS)
    return summary_text
