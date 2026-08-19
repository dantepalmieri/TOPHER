# sqlite crud round-trips for the dashboard's single source of truth - every
# process that touches the dashboard (cli.py, team_cli.py, research_cli.py,
# mcp_server.py, server.py) goes through these functions

import pytest

from second_brain.dashboard import run_store
from second_brain.types import PipelineStageResult


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    # points run_store at a throwaway sqlite file for every test in this module,
    # instead of the real project-root dashboard.db
    database_path = str(tmp_path / "test_dashboard.db")
    monkeypatch.setattr(run_store, "DASHBOARD_DATABASE_PATH", database_path)
    run_store.initialize_database()


def test_create_run_starts_in_running_status():
    run_store.create_run("run-1", "test goal", run_type=run_store.VAULT_QA_RUN_TYPE)
    run_detail = run_store.get_run_detail("run-1")
    assert run_detail.status == run_store.RUN_STATUS_RUNNING
    assert run_detail.run_type == run_store.VAULT_QA_RUN_TYPE
    assert run_detail.goal == "test goal"
    assert run_detail.finished_at is None


def test_mark_run_finished_updates_status_and_timestamp():
    run_store.create_run("run-2", "another goal")
    run_store.mark_run_finished("run-2", run_store.RUN_STATUS_DONE)
    run_detail = run_store.get_run_detail("run-2")
    assert run_detail.status == run_store.RUN_STATUS_DONE
    assert run_detail.finished_at is not None


def test_record_stage_result_appends_in_order():
    run_store.create_run("run-3", "pipeline goal")
    first_stage = PipelineStageResult(agent_name="Architect", output_text="plan")
    second_stage = PipelineStageResult(agent_name="Developer", output_text="code")
    run_store.record_stage_result("run-3", first_stage)
    run_store.record_stage_result("run-3", second_stage)

    run_detail = run_store.get_run_detail("run-3")
    assert len(run_detail.stages) == 2
    assert run_detail.stages[0].agent_name == "Architect"
    assert run_detail.stages[1].agent_name == "Developer"


def test_get_run_detail_returns_none_for_unknown_run():
    assert run_store.get_run_detail("does-not-exist") is None


def test_list_runs_orders_most_recently_started_first():
    run_store.create_run("run-older", "first")
    run_store.create_run("run-newer", "second")
    run_summaries = run_store.list_runs(limit=10)
    assert run_summaries[0].run_id == "run-newer"
    assert run_summaries[1].run_id == "run-older"


def test_get_current_run_snapshot_matches_most_recent_run():
    run_store.create_run("run-earlier", "first")
    run_store.create_run("run-latest", "second")
    current_snapshot = run_store.get_current_run_snapshot()
    assert current_snapshot.run_id == "run-latest"


def test_record_and_list_vault_events():
    run_store.record_vault_event("created note: Test Note")
    run_store.record_vault_event("appended to note: Test Note")
    vault_events = run_store.list_vault_events(limit=10)
    assert len(vault_events) == 2
    assert vault_events[0].description == "appended to note: Test Note"
    assert vault_events[1].description == "created note: Test Note"


def test_list_new_vault_events_since_only_returns_newer_events():
    run_store.record_vault_event("first event")
    last_seen_id = run_store.get_max_vault_event_id()
    run_store.record_vault_event("second event")
    run_store.record_vault_event("third event")

    new_events = run_store.list_new_vault_events_since(last_seen_id)
    assert len(new_events) == 2
    assert new_events[0].description == "second event"
    assert new_events[1].description == "third event"
