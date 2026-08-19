import type { RunDetail } from '../types'
import { STATUS_LABELS, STATUS_ICONS, getStatusColorVar } from '../statusDisplay'
import { getRunTypeLabel, RUN_TYPE_IN_PROGRESS_TEXT } from '../runTypeDisplay'

interface NonTeamRunIndicatorProps {
  currentRun: RunDetail
}

// the live message thread only makes sense for a team_conversation run - every
// other run_type (solo_research, ...) is a single stage, so it gets one simple
// line instead
export function NonTeamRunIndicator({ currentRun }: NonTeamRunIndicatorProps) {
  const statusColorVar = getStatusColorVar(currentRun.status)

  let activityText = getRunTypeLabel(currentRun.run_type)
  if (currentRun.status === 'running') {
    const inProgressText = RUN_TYPE_IN_PROGRESS_TEXT[currentRun.run_type]
    if (inProgressText !== undefined) {
      activityText = inProgressText
    }
  }

  return (
    <div className="non-team-run-indicator">
      <div className="non-team-run-indicator-activity">{activityText}</div>
      <div className="text-muted non-team-run-indicator-goal">{currentRun.goal}</div>
      <span className="non-team-run-indicator-status" style={{ color: statusColorVar }}>
        {STATUS_ICONS[currentRun.status]} {STATUS_LABELS[currentRun.status]}
      </span>
    </div>
  )
}
