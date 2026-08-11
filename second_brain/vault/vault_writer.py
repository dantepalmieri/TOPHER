# handles all filesystem writes: creating new notes and appending to existing ones

import os
import re
from second_brain.config import OBSIDIAN_VAULT_PATH, NOTE_FILE_EXTENSION

INVALID_FILENAME_CHARACTERS_PATTERN = r'[\\/:*?"<>|]'
REPLACEMENT_CHARACTER = "-"


def _sanitize_title(note_title):
    # replaces characters that aren't valid in a filename with a safe placeholder
    sanitized_title = re.sub(INVALID_FILENAME_CHARACTERS_PATTERN, REPLACEMENT_CHARACTER, note_title)
    return sanitized_title


def _write_new_note_file(target_file_path, body_text):
    # writes a brand-new note file, refusing to overwrite one that already exists there
    if os.path.exists(target_file_path):
        raise FileExistsError("a note with this title already exists: " + os.path.basename(target_file_path))

    with open(target_file_path, "w", encoding="utf-8") as note_file:
        note_file.write(body_text)


def create_note(note_title, body_text):
    # creates a brand-new note file in the vault root with the given title and body text
    sanitized_title = _sanitize_title(note_title)
    target_file_path = os.path.join(OBSIDIAN_VAULT_PATH, sanitized_title + NOTE_FILE_EXTENSION)
    _write_new_note_file(target_file_path, body_text)
    return target_file_path


def append_to_note(file_path, text_to_append):
    # appends text to the end of an existing note, adding a blank-line separator first
    separator = "\n\n"

    with open(file_path, "a", encoding="utf-8") as note_file:
        note_file.write(separator + text_to_append)


def create_or_append_note_in_folder(folder_name, note_title, text_to_add):
    # writes a new note inside a named vault subfolder (creating the subfolder first
    # if needed), or appends to it if a note with this title already exists there;
    # used for notes meant to accumulate over time, like daily assistant memory entries
    target_directory = os.path.join(OBSIDIAN_VAULT_PATH, folder_name)
    os.makedirs(target_directory, exist_ok=True)
    sanitized_title = _sanitize_title(note_title)
    target_file_path = os.path.join(target_directory, sanitized_title + NOTE_FILE_EXTENSION)

    if os.path.exists(target_file_path):
        append_to_note(target_file_path, text_to_add)
    else:
        _write_new_note_file(target_file_path, text_to_add)

    return target_file_path
