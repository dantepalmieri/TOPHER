import { useEffect, useState } from 'react'
import type { RunDetail } from '../types'
import { AGENT_ORDER } from '../agentConfig'

interface RunDetailPanelProps {
  runId: string
  onClose: () => void
}

function findAgentColorVar(agentName: string): string {
  for (let agentIndex = 0; agentIndex < AGENT_ORDER.length; agentIndex++) {
    if (AGENT_ORDER[agentIndex].name === agentName) {
      return AGENT_ORDER[agentIndex].colorVar
    }
  }
  return ''
}

function stopClickPropagation(event: React.MouseEvent) {
  event.stopPropagation()
}

// the full multi-stage transcript for one past run - fetched on demand rather than
// carried in the history list, since the history list only needs summary fields
export function RunDetailPanel({ runId, onClose }: RunDetailPanelProps) {
  const [runDetail, setRunDetail] = useState<RunDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isUnmounted = false
    setIsLoading(true)

    async function loadRunDetail() {
      const response = await fetch('/api/runs/' + runId)
      const data: RunDetail = await response.json()
      if (isUnmounted === false) {
        setRunDetail(data)
        setIsLoading(false)
      }
    }

    loadRunDetail()

    return function cleanup() {
      isUnmounted = true
    }
  }, [runId])

  let bodyContent
  if (isLoading === true || runDetail === null) {
    bodyContent = <p className="text-muted">Loading transcript...</p>
  } else {
    const stageBlocks = []
    for (let stageIndex = 0; stageIndex < runDetail.stages.length; stageIndex++) {
      const currentStage = runDetail.stages[stageIndex]
      const agentColorVar = findAgentColorVar(currentStage.agent_name)

      stageBlocks.push(
        <div key={stageIndex} className="run-detail-stage">
          <h3 style={{ borderLeft: '3px solid var(' + agentColorVar + ')' }} className="run-detail-stage-heading">
            {currentStage.agent_name}
          </h3>
          <pre className="run-detail-stage-output text-secondary">{currentStage.output_text}</pre>
        </div>,
      )
    }

    bodyContent = (
      <div className="run-detail-body">
        <p className="text-secondary">{runDetail.goal}</p>
        {stageBlocks}
      </div>
    )
  }

  return (
    <div className="run-detail-overlay" onClick={onClose}>
      <div className="panel run-detail-panel" onClick={stopClickPropagation}>
        <div className="run-detail-panel-header">
          <h2 className="panel-title">Run Transcript</h2>
          <button className="run-detail-close-button" onClick={onClose}>
            Close
          </button>
        </div>
        {bodyContent}
      </div>
    </div>
  )
}
