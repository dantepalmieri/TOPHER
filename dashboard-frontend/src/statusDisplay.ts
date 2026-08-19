// shared status label/icon/color lookup, used by both the message thread and the
// history timeline - the two use overlapping but not identical status sets, so
// this covers the union of both

export type DisplayStatus = 'idle' | 'running' | 'done' | 'error' | 'interrupted' | 'max_turns_reached'

export const STATUS_LABELS: Record<DisplayStatus, string> = {
  idle: 'Idle',
  running: 'Running',
  done: 'Done',
  error: 'Error',
  interrupted: 'Interrupted',
  max_turns_reached: 'Stopped (turn limit)',
}

export const STATUS_ICONS: Record<DisplayStatus, string> = {
  idle: '○',
  running: '◐',
  done: '●',
  error: '✕',
  interrupted: '!',
  max_turns_reached: '◼',
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
  if (status === 'interrupted' || status === 'max_turns_reached') {
    return 'var(--status-interrupted)'
  }
  return 'var(--status-error)'
}
