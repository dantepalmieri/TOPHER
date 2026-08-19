// run_type display labels, shared by HistoryTimeline's badge and AgentStatusBoard's
// non-team-pipeline indicator, now that runs can come from more than just the
// 5-agent team (second_brain/dashboard/run_store.py's TEAM_PIPELINE_RUN_TYPE /
// SOLO_RESEARCH_RUN_TYPE)

export const RUN_TYPE_LABELS: Record<string, string> = {
  team_pipeline: 'Team Pipeline',
  solo_research: 'Research',
}

// the only run_type that goes through all 5 agents - the one the 5-card
// AgentStatusBoard applies to; everything else gets NonTeamRunIndicator's single
// line instead
export const FIVE_STAGE_RUN_TYPES = new Set(['team_pipeline'])

// only set for run_types with no 5-agent board to show progress on - shown in place
// of the run_type label while that run is still in flight
export const RUN_TYPE_IN_PROGRESS_TEXT: Record<string, string> = {
  solo_research: 'Research is investigating…',
}

export function getRunTypeLabel(runType: string): string {
  const label = RUN_TYPE_LABELS[runType]
  if (label === undefined) {
    return runType
  }
  return label
}
