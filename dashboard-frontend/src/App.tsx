import { useDashboardSocket } from './hooks/useDashboardSocket'
import { AgentStatusBoard } from './components/AgentStatusBoard'
import { VaultActivityFeed } from './components/VaultActivityFeed'
import { HistoryTimeline } from './components/HistoryTimeline'

function App() {
  const { connected, currentRun, pastRuns, vaultEvents } = useDashboardSocket()

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
        <AgentStatusBoard currentRun={currentRun} />
        <HistoryTimeline pastRuns={pastRuns} />
        <VaultActivityFeed vaultEvents={vaultEvents} />
      </main>
    </div>
  )
}

export default App
