import { useState } from 'react'
import type { FormEvent } from 'react'

interface ModeOption {
  value: string
  label: string
  description: string
}

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
]

const IDLE_STATUS = 'idle'
const SUBMITTING_STATUS = 'submitting'
const ERROR_STATUS = 'error'

type SubmitStatus = typeof IDLE_STATUS | typeof SUBMITTING_STATUS | typeof ERROR_STATUS

// lets the dashboard do more than watch - triggers a run in either mode the
// backend's run_trigger.py supports. the started run then shows up through the
// existing websocket/AgentStatusBoard/HistoryTimeline machinery with no special
// casing needed there, since it's just another row in run_store
export function TriggerPanel() {
  const [goal, setGoal] = useState('')
  const [mode, setMode] = useState<string>(MODE_OPTIONS[0].value)
  const [status, setStatus] = useState<SubmitStatus>(IDLE_STATUS)
  const [errorMessage, setErrorMessage] = useState('')

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

    submitTrigger()
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
    </section>
  )
}
