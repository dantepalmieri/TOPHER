// shared types matching the backend's dataclasses (second_brain/types.py) and the
// websocket message shapes second_brain/dashboard/server.py sends

export type RunStatus = 'running' | 'done' | 'error' | 'interrupted' | 'max_turns_reached'

export interface PipelineStage {
  agent_name: string
  output_text: string
}

export interface TeamMessage {
  message_id: number
  run_id: string
  turn_number: number
  sender_agent_name: string
  recipient_agent_name: string | null
  content: string
  is_done_signal: boolean
  created_at: string
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
  messages: TeamMessage[]
}

export type CurrentRunSnapshotMessage = RunDetail & { type: 'current_run_snapshot' }

export interface RunStartedMessage {
  type: 'run_started'
  run_id: string
  run_type: string
  goal: string
  started_at: string
}

export interface StageCompleteMessage {
  type: 'stage_complete'
  run_id: string
  agent_name: string
  output_text: string
}

export interface MessageAddedMessage {
  type: 'message_added'
  run_id: string
  turn_number: number
  sender_agent_name: string
  recipient_agent_name: string | null
  content: string
  is_done_signal: boolean
  created_at: string
}

export interface RunFinishedMessage {
  type: 'run_finished'
  run_id: string
  status: RunStatus
}

export type DashboardMessage =
  | CurrentRunSnapshotMessage
  | RunStartedMessage
  | StageCompleteMessage
  | MessageAddedMessage
  | RunFinishedMessage
