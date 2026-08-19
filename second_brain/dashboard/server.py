# phase 5: the dashboard backend - serves the built frontend, exposes rest endpoints
# for initial state, and pushes live updates to connected browsers over websocket.
# reads flow through the shared sqlite database in run_store.py, so watching never
# depends on team_cli.py/mcp_server.py being alive.
#
# phase 6: POST /api/trigger is the one place this changes - it starts a real run via
# run_trigger.py, the same shared module team_cli.py calls. the run still executes
# out-of-process from this handler's perspective (asyncio.to_thread), and it still
# reports progress the only way this server ever finds out about anything: by writing
# to run_store, same as team_cli.py or mcp_server.py would. this process can still be
# stopped, started, or crash without corrupting a run already in flight - only the
# live progress view is lost, not the run itself

import asyncio
import os
import contextlib
import dataclasses
import fastapi
import uvicorn
import pydantic
from fastapi.staticfiles import StaticFiles
from second_brain.config import (
    DASHBOARD_SERVER_HOST,
    DASHBOARD_SERVER_PORT,
    DASHBOARD_POLL_INTERVAL_SECONDS,
    PROJECT_ROOT_DIRECTORY
)
from second_brain.dashboard import run_store, run_trigger

DEFAULT_RUNS_LIMIT = 20
FRONTEND_BUILD_DIRECTORY = os.path.join(PROJECT_ROOT_DIRECTORY, "dashboard-frontend", "dist")

RUN_NOT_FOUND_MESSAGE = "No run with this id exists."
EMPTY_GOAL_MESSAGE = "goal must not be empty."

RUN_STARTED_MESSAGE_TYPE = "run_started"
STAGE_COMPLETE_MESSAGE_TYPE = "stage_complete"
RUN_FINISHED_MESSAGE_TYPE = "run_finished"
CURRENT_RUN_SNAPSHOT_MESSAGE_TYPE = "current_run_snapshot"


class ConnectionManager:
    # tracks every currently-connected browser and broadcasts messages to all of them
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message):
        disconnected_connections = []

        for connection_index in range(len(self.active_connections)):
            current_connection = self.active_connections[connection_index]
            try:
                await current_connection.send_json(message)
            except Exception:
                disconnected_connections.append(current_connection)

        for disconnected_index in range(len(disconnected_connections)):
            self.disconnect(disconnected_connections[disconnected_index])


connection_manager = ConnectionManager()

# asyncio only holds a weak reference to a task once it's created - with nothing else
# referencing it, it can be garbage-collected mid-run. this set is that reference; a
# task removes itself once done via add_done_callback below
_background_run_tasks = set()


class TriggerRequest(pydantic.BaseModel):
    goal: str
    mode: str


class TriggerResponse(pydantic.BaseModel):
    run_id: str


async def _poll_and_broadcast_loop():
    # detects new pipeline activity by polling run_store on an interval, and
    # broadcasts anything new to every connected browser. every run_store call is
    # wrapped in asyncio.to_thread so a sqlite query never blocks this event loop,
    # which would otherwise delay delivery to every connected client
    last_run_id = None
    last_stage_count = 0
    last_broadcast_status = None

    while True:
        await asyncio.sleep(DASHBOARD_POLL_INTERVAL_SECONDS)

        current_snapshot = await asyncio.to_thread(run_store.get_current_run_snapshot)

        if current_snapshot is not None:
            if current_snapshot.run_id != last_run_id:
                last_run_id = current_snapshot.run_id
                last_stage_count = 0
                last_broadcast_status = None
                await connection_manager.broadcast({
                    "type": RUN_STARTED_MESSAGE_TYPE,
                    "run_id": current_snapshot.run_id,
                    "run_type": current_snapshot.run_type,
                    "goal": current_snapshot.goal,
                    "started_at": current_snapshot.started_at
                })

            if len(current_snapshot.stages) > last_stage_count:
                new_stage_count = len(current_snapshot.stages)
                for stage_index in range(last_stage_count, new_stage_count):
                    current_stage = current_snapshot.stages[stage_index]
                    await connection_manager.broadcast({
                        "type": STAGE_COMPLETE_MESSAGE_TYPE,
                        "run_id": current_snapshot.run_id,
                        "agent_name": current_stage.agent_name,
                        "output_text": current_stage.output_text
                    })
                last_stage_count = new_stage_count

            status_just_changed = current_snapshot.status != last_broadcast_status
            if status_just_changed and current_snapshot.status != run_store.RUN_STATUS_RUNNING:
                await connection_manager.broadcast({
                    "type": RUN_FINISHED_MESSAGE_TYPE,
                    "run_id": current_snapshot.run_id,
                    "status": current_snapshot.status
                })
            last_broadcast_status = current_snapshot.status


@contextlib.asynccontextmanager
async def _lifespan(fastapi_app):
    # runs once at server startup and once at shutdown, around the yield
    await asyncio.to_thread(run_store.initialize_database)
    poll_task = asyncio.create_task(_poll_and_broadcast_loop())
    yield
    poll_task.cancel()


app = fastapi.FastAPI(lifespan=_lifespan)


@app.get("/api/runs")
def get_runs(limit: int = DEFAULT_RUNS_LIMIT):
    # fastapi serializes dataclasses (and lists of them) automatically - no manual
    # dict conversion needed for a plain route return value
    runs = run_store.list_runs(limit)
    return runs


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run_detail = run_store.get_run_detail(run_id)

    if run_detail is None:
        raise fastapi.HTTPException(status_code=404, detail=RUN_NOT_FOUND_MESSAGE)

    return run_detail


async def _execute_run_in_background(run_id, goal, mode):
    # run_trigger.execute_run already persists success/failure to run_store before
    # returning or raising - the poll loop above broadcasts that over the websocket
    # to every connected browser, so there is nothing further to do with the outcome
    # here. this coroutine exists only so /api/trigger's response doesn't block for
    # the run's entire duration
    try:
        await asyncio.to_thread(run_trigger.execute_run, run_id, goal, mode)
    except Exception:
        pass


@app.post("/api/trigger", response_model=TriggerResponse)
async def trigger_run(trigger_request: TriggerRequest):
    goal = trigger_request.goal.strip()
    if goal == "":
        raise fastapi.HTTPException(status_code=400, detail=EMPTY_GOAL_MESSAGE)

    if trigger_request.mode not in run_trigger.VALID_TRIGGER_MODES:
        detail = "mode must be one of: " + ", ".join(sorted(run_trigger.VALID_TRIGGER_MODES))
        raise fastapi.HTTPException(status_code=400, detail=detail)

    run_id = await asyncio.to_thread(run_trigger.create_pending_run, goal, trigger_request.mode)

    background_task = asyncio.create_task(_execute_run_in_background(run_id, goal, trigger_request.mode))
    _background_run_tasks.add(background_task)
    background_task.add_done_callback(_background_run_tasks.discard)

    return TriggerResponse(run_id=run_id)


@app.websocket("/ws")
async def websocket_endpoint(websocket: fastapi.WebSocket):
    await connection_manager.connect(websocket)

    current_snapshot = await asyncio.to_thread(run_store.get_current_run_snapshot)
    if current_snapshot is not None:
        snapshot_message = dataclasses.asdict(current_snapshot)
        snapshot_message["type"] = CURRENT_RUN_SNAPSHOT_MESSAGE_TYPE
        await websocket.send_json(snapshot_message)

    try:
        while True:
            # this dashboard is watch-only - the browser never sends anything
            # meaningful, but awaiting receive is how a disconnect is detected
            await websocket.receive_text()
    except fastapi.WebSocketDisconnect:
        connection_manager.disconnect(websocket)


if os.path.isdir(FRONTEND_BUILD_DIRECTORY):
    # mounted last and at the root path, so it only ever catches requests that
    # didn't match an /api or /ws route registered above
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIRECTORY, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(app, host=DASHBOARD_SERVER_HOST, port=DASHBOARD_SERVER_PORT)
