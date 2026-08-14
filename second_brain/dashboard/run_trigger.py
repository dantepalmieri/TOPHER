# phase 6: the shared "start a run, persist its lifecycle, infer the in-flight agent
# on failure" logic, previously living only in team_cli.py
# (_run_full_pipeline_with_persistence, _infer_in_flight_agent) - refactored here so
# team_cli.py and the dashboard's POST /api/trigger endpoint call one implementation
# instead of duplicating it.
#
# protected (see config.py's SELF_MODIFICATION_PROTECTED_PATHS): this is exactly the
# kind of mode-dispatch logic self_modification_guard.py's design leans on staying
# untouchable - it is what decides whether a run gets the sandboxed workspace/
# boundary or the real project root, so an agent editing this file could quietly make
# every run resolve to the unrestricted mode without ever touching a guard's path checks

import uuid
from second_brain.orchestrator import (
    run_full_team_pipeline,
    handle_research_request,
    ARCHITECT_STAGE_NAME,
    RESEARCH_STAGE_NAME,
    DEVELOPER_STAGE_NAME,
    TESTING_STAGE_NAME,
    ANALYTICS_STAGE_NAME
)
from second_brain.claude.client import ask_claude_about_vault
from second_brain.vault.semantic_search import search_notes_by_semantic_similarity
from second_brain.config import MAXIMUM_NOTES_TO_INCLUDE
from second_brain.types import PipelineStageResult
from second_brain.dashboard import run_store

TEAM_PIPELINE_MODE = "team_pipeline"
SELF_IMPROVE_MODE = "self_improve"
RESEARCH_MODE = "research"
VAULT_QA_MODE = "vault_qa"

VALID_TRIGGER_MODES = {TEAM_PIPELINE_MODE, SELF_IMPROVE_MODE, RESEARCH_MODE, VAULT_QA_MODE}

ASSISTANT_STAGE_NAME = "Topher"

UNKNOWN_MODE_ERROR_TEMPLATE = "Unknown trigger mode '{mode}' - must be one of: {valid_modes}"

_RUN_TYPE_BY_MODE = {
    TEAM_PIPELINE_MODE: run_store.TEAM_PIPELINE_RUN_TYPE,
    SELF_IMPROVE_MODE: run_store.SELF_IMPROVE_RUN_TYPE,
    RESEARCH_MODE: run_store.SOLO_RESEARCH_RUN_TYPE,
    VAULT_QA_MODE: run_store.VAULT_QA_RUN_TYPE
}

PIPELINE_STAGE_ORDER = [
    ARCHITECT_STAGE_NAME, RESEARCH_STAGE_NAME, DEVELOPER_STAGE_NAME, TESTING_STAGE_NAME, ANALYTICS_STAGE_NAME
]


def infer_in_flight_agent(completed_stage_names):
    # the fixed pipeline order plus how many stages finished before a failure
    # unambiguously identifies which agent was running when it happened
    completed_count = len(completed_stage_names)

    if completed_count < len(PIPELINE_STAGE_ORDER):
        return PIPELINE_STAGE_ORDER[completed_count]

    return ANALYTICS_STAGE_NAME


def _run_team_pipeline(run_id, goal, self_improvement_mode, on_stage_complete):
    # runs the full 5-agent pipeline, persisting each stage as it completes - shared
    # by both team_pipeline and self_improve modes, which differ only in the boundary
    # orchestrator.py points developer/testing/analytics at
    completed_stage_names = []

    def _persist_and_forward(stage_result):
        run_store.record_stage_result(run_id, stage_result)
        completed_stage_names.append(stage_result.agent_name)
        if on_stage_complete is not None:
            on_stage_complete(stage_result)

    try:
        run_full_team_pipeline(goal, on_stage_complete=_persist_and_forward, self_improvement_mode=self_improvement_mode)
        run_store.mark_run_finished(run_id, run_store.RUN_STATUS_DONE)
    except (Exception, KeyboardInterrupt) as pipeline_error:
        in_flight_agent = infer_in_flight_agent(completed_stage_names)
        run_store.mark_run_finished(run_id, run_store.RUN_STATUS_ERROR)
        raise RuntimeError(in_flight_agent + " failed: " + str(pipeline_error)) from pipeline_error


def _run_research(run_id, goal, on_stage_complete):
    try:
        research_findings = handle_research_request(goal)
        stage_result = PipelineStageResult(agent_name=RESEARCH_STAGE_NAME, output_text=research_findings)
        run_store.record_stage_result(run_id, stage_result)
        if on_stage_complete is not None:
            on_stage_complete(stage_result)
        run_store.mark_run_finished(run_id, run_store.RUN_STATUS_DONE)
    except (Exception, KeyboardInterrupt) as research_error:
        run_store.mark_run_finished(run_id, run_store.RUN_STATUS_ERROR)
        raise RuntimeError(RESEARCH_STAGE_NAME + " failed: " + str(research_error)) from research_error


def _run_vault_qa(run_id, goal, on_stage_complete):
    # a dashboard-triggered vault question is one-shot: it searches fresh and answers
    # with no prior conversation turns, and - unlike cli.py's interactive session -
    # is never folded into conversation_history.json's long-term memory, since that
    # file represents a terminal conversation thread, not a one-off dashboard ask
    try:
        matching_notes = search_notes_by_semantic_similarity(goal, MAXIMUM_NOTES_TO_INCLUDE)
        claude_answer = ask_claude_about_vault(goal, matching_notes, [])
        stage_result = PipelineStageResult(agent_name=ASSISTANT_STAGE_NAME, output_text=claude_answer.response_text)
        run_store.record_stage_result(run_id, stage_result)
        if on_stage_complete is not None:
            on_stage_complete(stage_result)
        run_store.mark_run_finished(run_id, run_store.RUN_STATUS_DONE)
    except (Exception, KeyboardInterrupt) as vault_qa_error:
        run_store.mark_run_finished(run_id, run_store.RUN_STATUS_ERROR)
        raise RuntimeError(ASSISTANT_STAGE_NAME + " failed: " + str(vault_qa_error)) from vault_qa_error


def _require_valid_mode(mode):
    if mode not in VALID_TRIGGER_MODES:
        raise ValueError(UNKNOWN_MODE_ERROR_TEMPLATE.format(mode=mode, valid_modes=sorted(VALID_TRIGGER_MODES)))


def create_pending_run(goal, mode):
    # inserts the run row and returns its id immediately, before any agent work
    # happens - the fast half of start_run (one sqlite insert), split out so a
    # caller on an event loop (the dashboard's POST /api/trigger handler) can hand
    # a run_id back to the browser right away and run execute_run separately in a
    # background thread, rather than the http response blocking for the run's
    # entire duration
    _require_valid_mode(mode)
    run_id = uuid.uuid4().hex
    run_store.create_run(run_id, goal, run_type=_RUN_TYPE_BY_MODE[mode])
    return run_id


def execute_run(run_id, goal, mode, on_stage_complete=None):
    # runs the actual agent work for an already-created run row, dispatching to the
    # right pipeline shape for the given mode. synchronous and blocking - callers
    # already on an event loop must wrap this in asyncio.to_thread themselves, the
    # same pattern already proven for this project's sqlite polling. re-raises on
    # failure after persisting the error status, so a caller can still report what
    # happened
    _require_valid_mode(mode)

    if mode == TEAM_PIPELINE_MODE:
        _run_team_pipeline(run_id, goal, False, on_stage_complete)
    elif mode == SELF_IMPROVE_MODE:
        _run_team_pipeline(run_id, goal, True, on_stage_complete)
    elif mode == RESEARCH_MODE:
        _run_research(run_id, goal, on_stage_complete)
    else:
        _run_vault_qa(run_id, goal, on_stage_complete)


def start_run(goal, mode, on_stage_complete=None):
    # convenience wrapper for callers with no event loop of their own (team_cli.py):
    # creates the run and runs it to completion in one blocking call before returning
    run_id = create_pending_run(goal, mode)
    execute_run(run_id, goal, mode, on_stage_complete)
    return run_id
