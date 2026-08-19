# the shared "start a run, persist its lifecycle" logic, previously living only in
# team_cli.py - refactored here so team_cli.py and the dashboard's POST /api/trigger
# endpoint call one implementation instead of duplicating it.

import uuid
from second_brain.orchestrator import run_team_conversation, handle_research_request, RESEARCH_STAGE_NAME
from second_brain.types import PipelineStageResult
from second_brain.dashboard import run_store

TEAM_CONVERSATION_MODE = "team_conversation"
RESEARCH_MODE = "research"

VALID_TRIGGER_MODES = {TEAM_CONVERSATION_MODE, RESEARCH_MODE}

UNKNOWN_MODE_ERROR_TEMPLATE = "Unknown trigger mode '{mode}' - must be one of: {valid_modes}"

_RUN_TYPE_BY_MODE = {
    TEAM_CONVERSATION_MODE: run_store.TEAM_CONVERSATION_RUN_TYPE,
    RESEARCH_MODE: run_store.SOLO_RESEARCH_RUN_TYPE
}


def _run_team_conversation(run_id, goal, on_message):
    # runs the team's bounded conversation loop, persisting each message as it's
    # posted. finishes as RUN_STATUS_DONE if an agent said DONE, or
    # RUN_STATUS_MAX_TURNS if the turn cap was hit without that ever happening -
    # both are a completed run, neither is an error
    def _persist_and_forward(message):
        run_store.record_message(
            run_id, message.turn_number, message.sender_agent_name,
            message.recipient_agent_name, message.content, message.is_done_signal
        )
        if on_message is not None:
            on_message(message)

    try:
        _, reached_done = run_team_conversation(goal, on_message=_persist_and_forward)
        if reached_done is True:
            run_store.mark_run_finished(run_id, run_store.RUN_STATUS_DONE)
        else:
            run_store.mark_run_finished(run_id, run_store.RUN_STATUS_MAX_TURNS)
    except (Exception, KeyboardInterrupt) as conversation_error:
        run_store.mark_run_finished(run_id, run_store.RUN_STATUS_ERROR)
        raise conversation_error


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
    # right shape for the given mode. synchronous and blocking - callers already on
    # an event loop must wrap this in asyncio.to_thread themselves, the same pattern
    # already proven for this project's sqlite polling. re-raises on failure after
    # persisting the error status, so a caller can still report what happened.
    # on_stage_complete doubles as the team-conversation on_message callback - both
    # shapes carry the same thing callers actually want: "something new happened,
    # here it is"
    _require_valid_mode(mode)

    if mode == TEAM_CONVERSATION_MODE:
        _run_team_conversation(run_id, goal, on_stage_complete)
    else:
        _run_research(run_id, goal, on_stage_complete)


def start_run(goal, mode, on_stage_complete=None):
    # convenience wrapper for callers with no event loop of their own (team_cli.py):
    # creates the run and runs it to completion in one blocking call before returning
    run_id = create_pending_run(goal, mode)
    execute_run(run_id, goal, mode, on_stage_complete)
    return run_id
