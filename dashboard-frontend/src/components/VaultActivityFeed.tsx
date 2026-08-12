import type { VaultEvent } from '../types'

interface VaultActivityFeedProps {
  vaultEvents: VaultEvent[]
}

const SECONDS_PER_MINUTE = 60
const MINUTES_PER_HOUR = 60

function formatRelativeTime(isoTimestamp: string): string {
  const eventTimeMilliseconds = new Date(isoTimestamp).getTime()
  const nowMilliseconds = Date.now()
  const elapsedSeconds = Math.floor((nowMilliseconds - eventTimeMilliseconds) / 1000)

  if (elapsedSeconds < SECONDS_PER_MINUTE) {
    return 'just now'
  }

  const elapsedMinutes = Math.floor(elapsedSeconds / SECONDS_PER_MINUTE)
  if (elapsedMinutes < MINUTES_PER_HOUR) {
    return elapsedMinutes + 'm ago'
  }

  const elapsedHours = Math.floor(elapsedMinutes / MINUTES_PER_HOUR)
  return elapsedHours + 'h ago'
}

// only architect/research/analytics ever appear here - developer and testing have
// no vault mcp tools wired up, by design (see the phase 5 plan)
export function VaultActivityFeed({ vaultEvents }: VaultActivityFeedProps) {
  const rows = []
  for (let eventIndex = 0; eventIndex < vaultEvents.length; eventIndex++) {
    const currentEvent = vaultEvents[eventIndex]
    rows.push(
      <li key={currentEvent.event_id} className="vault-event-row">
        <span>{currentEvent.description}</span>
        <span className="text-muted">{formatRelativeTime(currentEvent.occurred_at)}</span>
      </li>,
    )
  }

  let emptyMessage = null
  if (vaultEvents.length === 0) {
    emptyMessage = <p className="text-muted">No vault activity yet.</p>
  }

  return (
    <section className="panel vault-activity-feed">
      <h2 className="panel-title">Vault Activity</h2>
      {emptyMessage}
      <ul className="vault-event-list">{rows}</ul>
    </section>
  )
}
