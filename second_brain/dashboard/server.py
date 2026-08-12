# phase 5: the dashboard backend - serves the built frontend, exposes rest endpoints
# for initial state, and pushes live updates to connected browsers over websocket.
# never talks to team_cli.py/mcp_server.py directly - everything flows through the
# shared sqlite database in run_store.py, so this process can be stopped, started, or
# crash without affecting the actual assistant

import asyncio
import os
import contextlib
import dataclasses
import fastapi
import uvicorn
from fastapi.staticfiles import StaticFiles
from second_brain.config import (
    DASHBOARD_SERVER_HOST,
    DASHBOARD_SERVER_PORT,
    DASHBOARD_POLL_INTERVAL_SECONDS,
    PROJECT_ROOT_DIRECTORY
)
from second_brain.dashboard import run_store

DEFAULT_RUNS_LIMIT = 20
DEFAULT_VAULT_EVENTS_LIMIT = 50
FRONTEND_BUILD_DIRECTORY = os.path.join(PROJECT_ROOT_DIRECTORY, "dashboard-frontend", "dist")

RUN_NOT_FOUND_MESSAGE = "No run with this id exists."

RUN_STARTED_MESSAGE_TYPE = "run_started"
STAGE_COMPLETE_MESSAGE_TYPE = "stage_complete"
RUN_FINISHED_MESSAGE_TYPE = "run_finished"
VAULT_EVENT_MESSAGE_TYPE = "vault_event"
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


async def _poll_and_broadcast_loop():
    # detects new pipeline activity and vault events by polling run_store on an
    # interval, and broadcasts anything new to every connected browser. every
    # run_store call is wrapped in asyncio.to_thread so a sqlite query never blocks
    # this event loop, which would otherwise delay delivery to every connected client
    last_run_id = None
    last_stage_count = 0
    last_broadcast_status = None
    last_seen_vault_event_id = await asyncio.to_thread(run_store.get_max_vault_event_id)

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

        new_vault_events = await asyncio.to_thread(run_store.list_new_vault_events_since, last_seen_vault_event_id)
        for event_index in range(len(new_vault_events)):
            current_event = new_vault_events[event_index]
            await connection_manager.broadcast({
                "type": VAULT_EVENT_MESSAGE_TYPE,
                "description": current_event.description,
                "occurred_at": current_event.occurred_at
            })
            last_seen_vault_event_id = current_event.event_id


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


@app.get("/api/vault-events")
def get_vault_events(limit: int = DEFAULT_VAULT_EVENTS_LIMIT):
    vault_events = run_store.list_vault_events(limit)
    return vault_events


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
