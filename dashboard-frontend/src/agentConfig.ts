// the team's fixed pipeline order and per-agent identity color, matching
// second_brain/orchestrator.py's PIPELINE_STAGE_ORDER and this project's README

export interface AgentConfig {
  name: string
  role: string
  colorVar: string
}

export const AGENT_ORDER: AgentConfig[] = [
  { name: 'Architect', role: 'Plans the goal', colorVar: '--agent-architect' },
  { name: 'Research', role: 'Investigates open questions', colorVar: '--agent-research' },
  { name: 'Developer', role: 'Builds it', colorVar: '--agent-developer' },
  { name: 'Testing', role: 'Reviews it', colorVar: '--agent-testing' },
  { name: 'Analytics', role: 'Reports on it', colorVar: '--agent-analytics' },
]
