import { MessageBubble } from './MessageBubble'
import { NonTeamRunIndicator } from './NonTeamRunIndicator'
import type { RunDetail } from '../types'
import { TEAM_CONVERSATION_RUN_TYPES } from '../runTypeDisplay'

interface MessageThreadProps {
  currentRun: RunDetail | null
}

// the live team conversation - a chat-log-style list of MessageBubble, replacing
// the old fixed 5-card AgentStatusBoard now that the team no longer follows a
// fixed schedule. runs with no message thread to show (solo_research, ...) fall
// back to NonTeamRunIndicator's single line, same as the board it replaces did
export function MessageThread({ currentRun }: MessageThreadProps) {
  if (currentRun === null || !TEAM_CONVERSATION_RUN_TYPES.has(currentRun.run_type)) {
    if (currentRun === null) {
      return (
        <section className="panel message-thread">
          <h2 className="panel-title">Team Conversation</h2>
          <p className="text-muted">No run yet.</p>
        </section>
      )
    }

    return (
      <section className="panel message-thread">
        <h2 className="panel-title">Team Conversation</h2>
        <NonTeamRunIndicator currentRun={currentRun} />
      </section>
    )
  }

  const bubbles = []
  for (let messageIndex = 0; messageIndex < currentRun.messages.length; messageIndex++) {
    bubbles.push(<MessageBubble key={currentRun.messages[messageIndex].turn_number} message={currentRun.messages[messageIndex]} />)
  }

  let bodyContent
  if (bubbles.length === 0) {
    bodyContent = <p className="text-muted">Waiting for Architect to open the conversation…</p>
  } else {
    bodyContent = <div className="message-thread-list">{bubbles}</div>
  }

  return (
    <section className="panel message-thread">
      <h2 className="panel-title">Team Conversation</h2>
      {bodyContent}
    </section>
  )
}
