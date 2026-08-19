import type { TeamMessage } from '../types'
import { AGENT_ORDER } from '../agentConfig'

interface MessageBubbleProps {
  message: TeamMessage
}

function findAgentColorVar(agentName: string): string {
  for (let agentIndex = 0; agentIndex < AGENT_ORDER.length; agentIndex++) {
    if (AGENT_ORDER[agentIndex].name === agentName) {
      return AGENT_ORDER[agentIndex].colorVar
    }
  }
  return ''
}

// one turn of the live team conversation - identity comes from the sender's
// border color (agentConfig.colorVar, same channel AgentStatusCard used to use),
// with a small badge showing who it explicitly handed off to, or that it ended
// the conversation
export function MessageBubble({ message }: MessageBubbleProps) {
  const agentColorVar = findAgentColorVar(message.sender_agent_name)

  let handoffBadge = null
  if (message.is_done_signal === true) {
    handoffBadge = <span className="message-bubble-badge message-bubble-badge-done">DONE</span>
  } else if (message.recipient_agent_name !== null) {
    handoffBadge = <span className="message-bubble-badge">→ {message.recipient_agent_name}</span>
  }

  return (
    <div className="message-bubble" style={{ borderLeft: '3px solid var(' + agentColorVar + ')' }}>
      <div className="message-bubble-header">
        <span className="message-bubble-sender">{message.sender_agent_name}</span>
        {handoffBadge}
      </div>
      <p className="text-secondary message-bubble-content">{message.content}</p>
    </div>
  )
}
