// shared types matching the backend's dataclasses (second_brain/types.py) and the
// websocket message shapes second_brain/dashboard/server.py sends

export type RunStatus = 'running' | 'done' | 'error' | 'interrupted'

export interface PipelineStage {
  agent_name: string
  output_text: string
}

export interface RunSummary {
  run_id: string
  run_type: string
  goal: string
  started_at: string
  finished_at: string | null
  status: RunStatus
}

export interface RunDetail extends RunSummary {
  stages: PipelineStage[]
}

export interface VaultEvent {
  event_id: number
  description: string
  occurred_at: string
}

export type CurrentRunSnapshotMessage = RunDetail & { type: 'current_run_snapshot' }

export interface RunStartedMessage {
  type: 'run_started'
  run_id: string
  goal: string
  started_at: string
}

export interface StageCompleteMessage {
  type: 'stage_complete'
  run_id: string
  agent_name: string
  output_text: string
}

export interface RunFinishedMessage {
  type: 'run_finished'
  run_id: string
  status: RunStatus
}

export interface VaultEventMessage {
  type: 'vault_event'
  description: string
  occurred_at: string
}

export type DashboardMessage =
  | CurrentRunSnapshotMessage
  | RunStartedMessage
  | StageCompleteMessage
  | RunFinishedMessage
  | VaultEventMessage
