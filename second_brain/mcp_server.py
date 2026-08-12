# exposes the vault access layer as MCP tools, so Claude Desktop, Claude Code, and a
# future orchestrator can all search, read, and write the vault through one shared
# layer instead of each reimplementing filesystem access

from mcp.server.fastmcp import FastMCP
from second_brain.vault.vault_reader import list_note_files, read_note_content, get_note_title
from second_brain.vault.vault_writer import create_note, append_to_note
from second_brain.vault.semantic_search import search_notes_by_semantic_similarity
from second_brain.config import OBSIDIAN_VAULT_PATH, MAXIMUM_NOTES_TO_INCLUDE
from second_brain.dashboard import run_store

NO_MATCHES_MESSAGE = "No matching notes found."
NOTE_LIST_SEPARATOR = " — "

vault_server = FastMCP("second-brain-vault")

# phase 5: this is the dashboard's vault-activity instrumentation point, deliberately
# not vault_writer.py - only the vault mcp tools defined below are reachable by the
# team's agents (architect/research/analytics), so instrumenting here captures exactly
# "the team's vault activity" without coupling vault_writer.py, a foundational module
# used everywhere, to a dashboard feature it should stay unaware of
run_store.initialize_database()


def _report_vault_event(description):
    # a dashboard db hiccup must never be able to break an actual vault write - the
    # tool functions below always return based on the real write outcome, never this
    try:
        run_store.record_vault_event(description)
    except Exception:
        pass


def _format_matching_notes(matching_notes):
    # formats semantic search results into one readable string for a tool response
    if len(matching_notes) == 0:
        return NO_MATCHES_MESSAGE

    combined_output = ""

    for note_index in range(len(matching_notes)):
        current_note = matching_notes[note_index]
        combined_output = combined_output + "### " + current_note.title + "\n" + current_note.content + "\n\n"

    return combined_output


@vault_server.tool()
def search_vault(question: str) -> str:
    """Searches the Obsidian vault for notes semantically related to a question and
    returns their titles and full content. Prefer this over read_vault_note when you
    don't already know the exact note you need."""
    matching_notes = search_notes_by_semantic_similarity(question, MAXIMUM_NOTES_TO_INCLUDE)
    formatted_notes = _format_matching_notes(matching_notes)
    return formatted_notes


@vault_server.tool()
def list_vault_notes() -> str:
    """Lists every note in the Obsidian vault as a title and its file path. Use the
    returned file path with read_vault_note or append_to_vault_note."""
    all_note_file_paths = list_note_files(OBSIDIAN_VAULT_PATH)

    if len(all_note_file_paths) == 0:
        return NO_MATCHES_MESSAGE

    combined_output = ""

    for file_index in range(len(all_note_file_paths)):
        current_file_path = all_note_file_paths[file_index]
        note_title = get_note_title(current_file_path)
        combined_output = combined_output + note_title + NOTE_LIST_SEPARATOR + current_file_path + "\n"

    return combined_output


@vault_server.tool()
def read_vault_note(file_path: str) -> str:
    """Reads the full content of one note in the Obsidian vault, given its file path
    as returned by list_vault_notes or search_vault."""
    note_content = read_note_content(file_path)
    return note_content


@vault_server.tool()
def create_vault_note(title: str, body_text: str) -> str:
    """Creates a brand-new note in the Obsidian vault with the given title and body
    text. Fails if a note with that title already exists, rather than overwriting it."""
    created_file_path = create_note(title, body_text)
    _report_vault_event("Created note '" + title + "'")
    return "Created note at " + created_file_path


@vault_server.tool()
def append_to_vault_note(file_path: str, text_to_append: str) -> str:
    """Appends text to the end of an existing note in the Obsidian vault, given its
    file path as returned by list_vault_notes or search_vault."""
    append_to_note(file_path, text_to_append)
    _report_vault_event("Appended to note at '" + file_path + "'")
    return "Appended to note at " + file_path


if __name__ == "__main__":
    vault_server.run(transport="stdio")
