# shared data structures used across the dashboard

from dataclasses import dataclass
from typing import List


@dataclass
class PipelineStageResult:
    agent_name: str
    output_text: str


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
