// shared status label/icon/color lookup, used by both the agent status board and
// the history timeline - the two use overlapping but not identical status sets
// (agent cards never show "interrupted"), so this covers the union of both

export type DisplayStatus = 'idle' | 'running' | 'done' | 'error' | 'interrupted'

export const STATUS_LABELS: Record<DisplayStatus, string> = {
  idle: 'Idle',
  running: 'Running',
  done: 'Done',
  error: 'Error',
  interrupted: 'Interrupted',
}

export const STATUS_ICONS: Record<DisplayStatus, string> = {
  idle: '○',
  running: '◐',
  done: '●',
  error: '✕',
  interrupted: '!',
}

export function getStatusColorVar(status: DisplayStatus): string {
  if (status === 'idle') {
    return 'var(--status-idle)'
  }
  if (status === 'running') {
    return 'var(--status-running)'
  }
  if (status === 'done') {
    return 'var(--status-done)'
  }
  if (status === 'interrupted') {
    return 'var(--status-interrupted)'
  }
  return 'var(--status-error)'
}
