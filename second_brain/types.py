# shared data structures used across the dashboard

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PipelineStageResult:
    agent_name: str
    output_text: str


@dataclass
class TeamMessage:
    message_id: int
    run_id: str
    turn_number: int
    sender_agent_name: str
    recipient_agent_name: Optional[str]
    content: str
    is_done_signal: bool
    created_at: str


@dataclass
class RunSummary:
    run_id: str
    run_type: str
    goal: str
    started_at: str
    finished_at: str
    status: str


@dataclass
class RunDetail:
    run_id: str
    run_type: str
    goal: str
    started_at: str
    finished_at: str
    status: str
    stages: List[PipelineStageResult]
    messages: List[TeamMessage]
