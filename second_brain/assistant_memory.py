# distills a conversation session into a short summary and saves it as a note inside
# the vault's Assistant Memory folder, so long-term memory is a readable vault note -
# searchable by the same semantic search as any other note - rather than a hidden file

import datetime
from second_brain.claude.client import summarize_conversation_for_memory
from second_brain.vault.vault_writer import create_or_append_note_in_folder
from second_brain.config import ASSISTANT_MEMORY_FOLDER_NAME

TIME_HEADING_FORMAT = "%H:%M"


def save_session_to_memory(session_turns):
    # summarizes this session's turns and appends the summary to today's memory note;
    # does nothing if the session produced no turns, e.g. the user exited immediately
    if len(session_turns) == 0:
        return None

    summary_text = summarize_conversation_for_memory(session_turns)
    today_date_string = datetime.date.today().isoformat()
    current_time_string = datetime.datetime.now().strftime(TIME_HEADING_FORMAT)
    entry_text = "## " + current_time_string + "\n" + summary_text

    saved_file_path = create_or_append_note_in_folder(ASSISTANT_MEMORY_FOLDER_NAME, today_date_string, entry_text)
    return saved_file_path
