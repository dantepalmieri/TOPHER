import type { CSSProperties } from 'react'
import type { AgentConfig } from '../agentConfig'
import type { PipelineStage } from '../types'
import { STATUS_LABELS, STATUS_ICONS, getStatusColorVar } from '../statusDisplay'

export type AgentCardStatus = 'idle' | 'running' | 'done' | 'error'

interface AgentStatusCardProps {
  agentConfig: AgentConfig
  status: AgentCardStatus
  stage: PipelineStage | undefined
}

type CardStyle = CSSProperties & { '--glow-color'?: string }

const SNIPPET_MAXIMUM_LENGTH = 140

function buildOutputSnippet(stage: PipelineStage | undefined): string {
  if (stage === undefined) {
    return ''
  }

  if (stage.output_text.length <= SNIPPET_MAXIMUM_LENGTH) {
    return stage.output_text
  }

  return stage.output_text.slice(0, SNIPPET_MAXIMUM_LENGTH) + '…'
}

// one agent's card in the status board - identity comes from the border/icon color
// (agentConfig.colorVar), state comes from the separate, reserved status palette;
// the two are never the same channel, per the dataviz skill's status-color rule
export function AgentStatusCard({ agentConfig, status, stage }: AgentStatusCardProps) {
  const statusColorVar = getStatusColorVar(status)

  let cardClassName = 'panel agent-card'
  const cardStyle: CardStyle = {
    borderLeft: '3px solid var(' + agentConfig.colorVar + ')',
  }

  if (status === 'running') {
    cardClassName = cardClassName + ' glow'
    cardStyle['--glow-color'] = 'var(' + agentConfig.colorVar + ')'
  } else if (status === 'error') {
    cardClassName = cardClassName + ' glow'
    cardStyle['--glow-color'] = 'var(--status-error)'
  }

  const outputSnippet = buildOutputSnippet(stage)
  let snippetElement = null
  if (outputSnippet !== '') {
    snippetElement = <div className="text-secondary agent-card-snippet">{outputSnippet}</div>
  }

  return (
    <div className={cardClassName} style={cardStyle}>
      <div className="agent-card-header">
        <span className="agent-card-name">{agentConfig.name}</span>
        <span className="agent-card-status" style={{ color: statusColorVar }}>
          {STATUS_ICONS[status]} {STATUS_LABELS[status]}
        </span>
      </div>
      <div className="text-muted agent-card-role">{agentConfig.role}</div>
      {snippetElement}
    </div>
  )
}
