# handles all filesystem reads: listing notes and reading their content

import os
from second_brain.config import NOTE_FILE_EXTENSION


def list_note_files(directory_path):
    # recursively collects every markdown file path inside the vault directory
    collected_file_paths = []
    directory_entries = list(os.scandir(directory_path))

    for entry_index in range(len(directory_entries)):
        current_entry = directory_entries[entry_index]
        full_entry_path = os.path.join(directory_path, current_entry.name)

        is_hidden_directory = current_entry.name.startswith(".")

        if current_entry.is_dir() and not is_hidden_directory:
            # skips Obsidian's own folders (.obsidian config, .trash deleted notes)
            nested_file_paths = list_note_files(full_entry_path)
            for nested_index in range(len(nested_file_paths)):
                collected_file_paths.append(nested_file_paths[nested_index])
        elif current_entry.name.endswith(NOTE_FILE_EXTENSION):
            collected_file_paths.append(full_entry_path)

    return collected_file_paths


def read_note_content(file_path):
    # reads the raw text content of a single note file
    with open(file_path, "r", encoding="utf-8") as note_file:
        raw_content = note_file.read()
    return raw_content


def get_note_title(file_path):
    # derives a note's display title from its file path (filename without extension)
    note_title = os.path.splitext(os.path.basename(file_path))[0]
    return note_title


def find_note_file_path_by_title(directory_path, note_title):
    # finds a note's file path by matching its title case-insensitively; returns
    # None if no note in the vault has this title
    all_note_file_paths = list_note_files(directory_path)
    lower_case_target_title = note_title.lower()

    for file_index in range(len(all_note_file_paths)):
        current_file_path = all_note_file_paths[file_index]
        current_title = get_note_title(current_file_path)
        if current_title.lower() == lower_case_target_title:
            return current_file_path

    return None
