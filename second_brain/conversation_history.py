# handles reading and writing the persisted conversation history; the only module
# that touches the conversation history file on disk

import json
import os
from second_brain.config import CONVERSATION_HISTORY_FILE_PATH
from second_brain.types import ConversationTurn


def load_conversation_history():
    # loads all previously saved conversation turns from disk, oldest first
    if not os.path.exists(CONVERSATION_HISTORY_FILE_PATH):
        return []

    with open(CONVERSATION_HISTORY_FILE_PATH, "r", encoding="utf-8") as history_file:
        raw_turns = json.load(history_file)

    loaded_turns = []

    for turn_index in range(len(raw_turns)):
        current_raw_turn = raw_turns[turn_index]
        new_turn = ConversationTurn(role=current_raw_turn["role"], content=current_raw_turn["content"])
        loaded_turns.append(new_turn)

    return loaded_turns


def append_turns_to_history(existing_turns, new_turns):
    # appends new turns to the existing history, persists the full history to disk,
    # and returns the combined list so the caller's in-memory history stays in sync
    combined_turns = []

    for turn_index in range(len(existing_turns)):
        combined_turns.append(existing_turns[turn_index])

    for turn_index in range(len(new_turns)):
        combined_turns.append(new_turns[turn_index])

    serializable_turns = []

    for turn_index in range(len(combined_turns)):
        current_turn = combined_turns[turn_index]
        serializable_turns.append({"role": current_turn.role, "content": current_turn.content})

    with open(CONVERSATION_HISTORY_FILE_PATH, "w", encoding="utf-8") as history_file:
        json.dump(serializable_turns, history_file, indent=2)

    return combined_turns
