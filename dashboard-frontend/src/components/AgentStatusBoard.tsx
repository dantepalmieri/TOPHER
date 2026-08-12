import { AGENT_ORDER } from '../agentConfig'
import { AgentStatusCard } from './AgentStatusCard'
import type { AgentCardStatus } from './AgentStatusCard'
import type { RunDetail } from '../types'

interface AgentStatusBoardProps {
  currentRun: RunDetail | null
}

// derives one agent's display status purely from its position in the fixed
// pipeline order and how many stages the current run has completed so far -
// matches second_brain/team_cli.py's own _infer_in_flight_agent logic
function computeAgentStatus(agentIndex: number, currentRun: RunDetail | null): AgentCardStatus {
  if (currentRun === null) {
    return 'idle'
  }

  if (agentIndex < currentRun.stages.length) {
    return 'done'
  }

  if (agentIndex === currentRun.stages.length) {
    if (currentRun.status === 'running') {
      return 'running'
    }
    if (currentRun.status === 'error' || currentRun.status === 'interrupted') {
      return 'error'
    }
  }

  return 'idle'
}

export function AgentStatusBoard({ currentRun }: AgentStatusBoardProps) {
  const cards = []

  for (let agentIndex = 0; agentIndex < AGENT_ORDER.length; agentIndex++) {
    const agentConfig = AGENT_ORDER[agentIndex]
    const status = computeAgentStatus(agentIndex, currentRun)

    let stage
    if (currentRun !== null && agentIndex < currentRun.stages.length) {
      stage = currentRun.stages[agentIndex]
    } else {
      stage = undefined
    }

    cards.push(<AgentStatusCard key={agentConfig.name} agentConfig={agentConfig} status={status} stage={stage} />)
  }

  return (
    <section className="panel agent-status-board">
      <h2 className="panel-title">Agent Status</h2>
      <div className="agent-status-board-grid">{cards}</div>
    </section>
  )
}
