# shared data structures used across the vault and claude modules

from dataclasses import dataclass
from typing import List


@dataclass
class NoteMatch:
    file_path: str
    title: str
    content: str
    match_score: float


@dataclass
class ClaudeAnswer:
    response_text: str
    source_notes: List[str]
    vault_actions: List[str]


@dataclass
class ConversationTurn:
    role: str
    content: str


@dataclass
class PipelineStageResult:
    agent_name: str
    output_text: str
