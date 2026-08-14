import { useState } from 'react'
import type { RunSummary } from '../types'
import { STATUS_LABELS, STATUS_ICONS, getStatusColorVar } from '../statusDisplay'
import { getRunTypeLabel } from '../runTypeDisplay'
import { RunDetailPanel } from './RunDetailPanel'

interface HistoryTimelineProps {
  pastRuns: RunSummary[]
}

const GOAL_PREVIEW_MAXIMUM_LENGTH = 80

function buildGoalPreview(goal: string): string {
  if (goal.length <= GOAL_PREVIEW_MAXIMUM_LENGTH) {
    return goal
  }
  return goal.slice(0, GOAL_PREVIEW_MAXIMUM_LENGTH) + '…'
}

function formatStartedAt(isoTimestamp: string): string {
  const startedDate = new Date(isoTimestamp)
  return startedDate.toLocaleString()
}

export function HistoryTimeline({ pastRuns }: HistoryTimelineProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)

  function handleRowClick(runId: string) {
    setSelectedRunId(runId)
  }

  function handleCloseDetailPanel() {
    setSelectedRunId(null)
  }

  const rows = []
  for (let runIndex = 0; runIndex < pastRuns.length; runIndex++) {
    const currentRun = pastRuns[runIndex]
    const statusColorVar = getStatusColorVar(currentRun.status)

    rows.push(
      <li key={currentRun.run_id} className="history-row" onClick={() => handleRowClick(currentRun.run_id)}>
        <span className="history-row-goal-line">
          <span className="history-row-badge text-muted">{getRunTypeLabel(currentRun.run_type)}</span>
          <span className="history-row-goal">{buildGoalPreview(currentRun.goal)}</span>
        </span>
        <span className="history-row-meta">
          <span className="text-muted">{formatStartedAt(currentRun.started_at)}</span>
          <span style={{ color: statusColorVar }}>
            {STATUS_ICONS[currentRun.status]} {STATUS_LABELS[currentRun.status]}
          </span>
        </span>
      </li>,
    )
  }

  let emptyMessage = null
  if (pastRuns.length === 0) {
    emptyMessage = <p className="text-muted">No runs yet.</p>
  }

  let detailPanel = null
  if (selectedRunId !== null) {
    detailPanel = <RunDetailPanel runId={selectedRunId} onClose={handleCloseDetailPanel} />
  }

  return (
    <section className="panel history-timeline">
      <h2 className="panel-title">History</h2>
      {emptyMessage}
      <ul className="history-row-list">{rows}</ul>
      {detailPanel}
    </section>
  )
}
