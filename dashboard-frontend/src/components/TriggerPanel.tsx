import { useState } from 'react'
import type { FormEvent } from 'react'

interface ModeOption {
  value: string
  label: string
  description: string
}

// self_improve is listed last and its confirmation is handled separately below -
// it is the one mode that lets the team commit directly to Topher's own real
// codebase, so triggering it deliberately takes one extra deliberate step
const MODE_OPTIONS: ModeOption[] = [
  {
    value: 'team_pipeline',
    label: 'Team Pipeline',
    description: 'Architect → Research → Developer → Testing → Analytics, sandboxed to workspace/.',
  },
  {
    value: 'research',
    label: 'Research',
    description: 'One research question, live web search.',
  },
  {
    value: 'self_improve',
    label: 'Self-Improve',
    description: "The full team, working on Topher's own real codebase. Can commit directly.",
  },
]

const SELF_IMPROVE_MODE = 'self_improve'
const IDLE_STATUS = 'idle'
const SUBMITTING_STATUS = 'submitting'
const ERROR_STATUS = 'error'

type SubmitStatus = typeof IDLE_STATUS | typeof SUBMITTING_STATUS | typeof ERROR_STATUS

function stopClickPropagation(event: React.MouseEvent) {
  event.stopPropagation()
}

// lets the dashboard do more than watch - triggers a run in any of the four modes
// the backend's run_trigger.py supports. the started run then shows up through the
// existing websocket/AgentStatusBoard/HistoryTimeline machinery with no special
// casing needed there, since it's just another row in run_store
export function TriggerPanel() {
  const [goal, setGoal] = useState('')
  const [mode, setMode] = useState<string>(MODE_OPTIONS[0].value)
  const [status, setStatus] = useState<SubmitStatus>(IDLE_STATUS)
  const [errorMessage, setErrorMessage] = useState('')
  const [isConfirmingSelfImprove, setIsConfirmingSelfImprove] = useState(false)

  async function submitTrigger() {
    setStatus(SUBMITTING_STATUS)
    setErrorMessage('')

    try {
      const response = await fetch('/api/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, mode }),
      })

      if (response.ok === false) {
        const errorBody = await response.json()
        setStatus(ERROR_STATUS)
        setErrorMessage(errorBody.detail)
        return
      }

      setGoal('')
      setStatus(IDLE_STATUS)
    } catch (fetchError) {
      setStatus(ERROR_STATUS)
      setErrorMessage('Could not reach the dashboard server.')
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (goal.trim() === '' || status === SUBMITTING_STATUS) {
      return
    }

    if (mode === SELF_IMPROVE_MODE) {
      setIsConfirmingSelfImprove(true)
      return
    }

    submitTrigger()
  }

  function handleConfirmSelfImprove() {
    setIsConfirmingSelfImprove(false)
    submitTrigger()
  }

  function handleCancelSelfImprove() {
    setIsConfirmingSelfImprove(false)
  }

  let confirmOverlay = null
  if (isConfirmingSelfImprove === true) {
    confirmOverlay = (
      <div className="run-detail-overlay" onClick={handleCancelSelfImprove}>
        <div className="panel trigger-confirm-panel" onClick={stopClickPropagation}>
          <h2 className="panel-title">Confirm Self-Improve Run</h2>
          <p className="text-secondary">
            This lets the team modify Topher's own codebase and commit directly. It cannot touch its own safety
            guardrails, but every other file is fair game. Continue?
          </p>
          <div className="trigger-confirm-actions">
            <button type="button" className="run-detail-close-button" onClick={handleCancelSelfImprove}>
              Cancel
            </button>
            <button type="button" className="trigger-confirm-button" onClick={handleConfirmSelfImprove}>
              Start Self-Improve Run
            </button>
          </div>
        </div>
      </div>
    )
  }

  let statusMessage = null
  if (status === ERROR_STATUS) {
    statusMessage = <p className="trigger-panel-error">{errorMessage}</p>
  } else if (status === SUBMITTING_STATUS) {
    statusMessage = <p className="text-muted">Starting run…</p>
  }

  return (
    <section className="panel trigger-panel">
      <h2 className="panel-title">Trigger a Run</h2>
      <form className="trigger-panel-form" onSubmit={handleSubmit}>
        <textarea
          className="trigger-panel-input"
          placeholder="What should Topher do?"
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          rows={2}
        />
        <div className="trigger-panel-controls">
          <select className="trigger-panel-select" value={mode} onChange={(event) => setMode(event.target.value)}>
            {MODE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button type="submit" className="trigger-panel-submit" disabled={status === SUBMITTING_STATUS}>
            Run
          </button>
        </div>
        <p className="text-muted trigger-panel-mode-description">
          {MODE_OPTIONS.find((option) => option.value === mode)?.description}
        </p>
        {statusMessage}
      </form>
      {confirmOverlay}
    </section>
  )
}
