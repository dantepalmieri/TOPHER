// run_type display labels, shared by HistoryTimeline's badge and MessageThread's
// non-team-conversation indicator, now that runs can come from more than just the
// 5-agent team (second_brain/dashboard/run_store.py's TEAM_CONVERSATION_RUN_TYPE /
// SOLO_RESEARCH_RUN_TYPE)

export const RUN_TYPE_LABELS: Record<string, string> = {
  team_conversation: 'Team Conversation',
  solo_research: 'Research',
}

// the only run_type with a live message thread to show - everything else gets
// NonTeamRunIndicator's single line instead
export const TEAM_CONVERSATION_RUN_TYPES = new Set(['team_conversation'])

// only set for run_types with no message thread to show progress on - shown in
// place of the run_type label while that run is still in flight
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
