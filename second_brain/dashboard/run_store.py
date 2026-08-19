# phase 5: owns all sqlite access for the dashboard - the single source of truth for
# pipeline run history. every process that touches the dashboard (team_cli.py, the
# dashboard server itself) goes through this module rather than opening its own
# connection, so the concurrency handling lives in one place

import sqlite3
import datetime
from second_brain.config import DASHBOARD_DATABASE_PATH, DASHBOARD_STALE_RUN_THRESHOLD_MINUTES
from second_brain.types import PipelineStageResult, RunSummary, RunDetail

BUSY_TIMEOUT_MILLISECONDS = 5000

RUN_STATUS_RUNNING = "running"
RUN_STATUS_DONE = "done"
RUN_STATUS_ERROR = "error"
RUN_STATUS_INTERRUPTED = "interrupted"

TEAM_PIPELINE_RUN_TYPE = "team_pipeline"
SOLO_RESEARCH_RUN_TYPE = "solo_research"


def _open_connection():
    # opens a short-lived connection with the pragmas every caller needs; the caller
    # closes it as soon as its operation is done, to keep the write-lock window small.
    # busy_timeout matters even under wal mode, since wal only lets readers proceed
    # without blocking - a second concurrent writer still waits or fails outright
    # with no timeout set
    connection = sqlite3.connect(DASHBOARD_DATABASE_PATH)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = " + str(BUSY_TIMEOUT_MILLISECONDS))
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    # creates every table if it doesn't already exist; safe to call from every
    # process that touches the database, as many times as it wants
    connection = _open_connection()

    connection.execute(
        "CREATE TABLE IF NOT EXISTS runs ("
        "run_id TEXT PRIMARY KEY, "
        "run_type TEXT NOT NULL, "
        "goal TEXT NOT NULL, "
        "started_at TEXT NOT NULL, "
        "finished_at TEXT, "
        "status TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS stages ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "run_id TEXT NOT NULL, "
        "agent_name TEXT NOT NULL, "
        "output_text TEXT NOT NULL, "
        "completed_at TEXT NOT NULL)"
    )
    connection.commit()
    connection.close()


def _current_timestamp():
    # one iso-8601, timezone-aware timestamp format used everywhere in this module,
    # so staleness comparisons never have to guess an offset
    current_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return current_timestamp


def _is_timestamp_stale(timestamp_text):
    # true once a "running" run's most recent activity is older than the configured
    # threshold - used to display an abandoned run (killed cli, crash) as interrupted
    # instead of a spinner that never stops
    activity_time = datetime.datetime.fromisoformat(timestamp_text)
    current_time = datetime.datetime.now(datetime.timezone.utc)
    elapsed_minutes = (current_time - activity_time).total_seconds() / 60
    return elapsed_minutes > DASHBOARD_STALE_RUN_THRESHOLD_MINUTES


def _get_stages_for_run(connection, run_id):
    # every completed stage for one run, in completion order
    stage_rows = connection.execute(
        "SELECT agent_name, output_text FROM stages WHERE run_id = ? ORDER BY id ASC",
        (run_id,)
    ).fetchall()

    stages = []
    for stage_index in range(len(stage_rows)):
        current_stage_row = stage_rows[stage_index]
        stages.append(PipelineStageResult(
            agent_name=current_stage_row["agent_name"],
            output_text=current_stage_row["output_text"]
        ))

    return stages


def _resolve_run_status(connection, run_row):
    # a running run whose most recent activity has gone stale displays as
    # "interrupted" rather than a live-looking run forever - a read-time heuristic,
    # not a change to the stored status, since nothing can reliably run cleanup when
    # a cli process is killed
    if run_row["status"] != RUN_STATUS_RUNNING:
        return run_row["status"]

    latest_stage_row = connection.execute(
        "SELECT completed_at FROM stages WHERE run_id = ? ORDER BY id DESC LIMIT 1",
        (run_row["run_id"],)
    ).fetchone()

    if latest_stage_row is None:
        most_recent_activity = run_row["started_at"]
    else:
        most_recent_activity = latest_stage_row["completed_at"]

    if _is_timestamp_stale(most_recent_activity):
        return RUN_STATUS_INTERRUPTED

    return RUN_STATUS_RUNNING


def create_run(run_id, goal, run_type=TEAM_PIPELINE_RUN_TYPE):
    # inserts a new run row with status "running"
    connection = _open_connection()
    connection.execute(
        "INSERT INTO runs (run_id, run_type, goal, started_at, finished_at, status) VALUES (?, ?, ?, ?, NULL, ?)",
        (run_id, run_type, goal, _current_timestamp(), RUN_STATUS_RUNNING)
    )
    connection.commit()
    connection.close()


def record_stage_result(run_id, stage_result):
    # inserts one completed pipeline stage
    connection = _open_connection()
    connection.execute(
        "INSERT INTO stages (run_id, agent_name, output_text, completed_at) VALUES (?, ?, ?, ?)",
        (run_id, stage_result.agent_name, stage_result.output_text, _current_timestamp())
    )
    connection.commit()
    connection.close()


def mark_run_finished(run_id, status):
    # marks a run as finished (done or error) with a finish timestamp
    connection = _open_connection()
    connection.execute(
        "UPDATE runs SET status = ?, finished_at = ? WHERE run_id = ?",
        (status, _current_timestamp(), run_id)
    )
    connection.commit()
    connection.close()


def list_runs(limit):
    # every run, most recently started first, with read-time staleness resolved
    connection = _open_connection()
    run_rows = connection.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?",
        (limit,)
    ).fetchall()

    run_summaries = []
    for row_index in range(len(run_rows)):
        current_row = run_rows[row_index]
        run_summaries.append(RunSummary(
            run_id=current_row["run_id"],
            run_type=current_row["run_type"],
            goal=current_row["goal"],
            started_at=current_row["started_at"],
            finished_at=current_row["finished_at"],
            status=_resolve_run_status(connection, current_row)
        ))

    connection.close()
    return run_summaries


def get_run_detail(run_id):
    # one run's full detail, including every stage's complete output - returns
    # None if no run with this id exists
    connection = _open_connection()
    run_row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()

    if run_row is None:
        connection.close()
        return None

    run_detail = RunDetail(
        run_id=run_row["run_id"],
        run_type=run_row["run_type"],
        goal=run_row["goal"],
        started_at=run_row["started_at"],
        finished_at=run_row["finished_at"],
        status=_resolve_run_status(connection, run_row),
        stages=_get_stages_for_run(connection, run_row["run_id"])
    )

    connection.close()
    return run_detail


def get_current_run_snapshot():
    # the single most recently started run, full detail (whether it's still running,
    # finished, or gone stale) - used to give a freshly connected browser immediate
    # state, and by the dashboard server's poll loop to detect new stages/status
    # changes without needing per-row change tracking on the runs table
    connection = _open_connection()
    run_row = connection.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()

    if run_row is None:
        connection.close()
        return None

    run_detail = RunDetail(
        run_id=run_row["run_id"],
        run_type=run_row["run_type"],
        goal=run_row["goal"],
        started_at=run_row["started_at"],
        finished_at=run_row["finished_at"],
        status=_resolve_run_status(connection, run_row),
        stages=_get_stages_for_run(connection, run_row["run_id"])
    )

    connection.close()
    return run_detail
