import { useDashboardSocket } from './hooks/useDashboardSocket'
import { TriggerPanel } from './components/TriggerPanel'
import { MessageThread } from './components/MessageThread'
import { HistoryTimeline } from './components/HistoryTimeline'

function App() {
  const { connected, currentRun, pastRuns } = useDashboardSocket()

  let connectionLabel: string
  let connectionDotClassName: string
  if (connected === true) {
    connectionLabel = 'Connected'
    connectionDotClassName = 'connection-dot connection-dot-connected'
  } else {
    connectionLabel = 'Disconnected'
    connectionDotClassName = 'connection-dot connection-dot-disconnected'
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-wordmark">TOPHER</h1>
        <div className="connection-indicator">
          <span className={connectionDotClassName}></span>
          <span className="text-muted">{connectionLabel}</span>
        </div>
      </header>
      <main className="app-grid">
        <TriggerPanel />
        <MessageThread currentRun={currentRun} />
        <HistoryTimeline pastRuns={pastRuns} />
      </main>
    </div>
  )
}

export default App
