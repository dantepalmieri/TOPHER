import { useEffect, useState } from 'react'
import type { DashboardMessage, RunDetail, RunSummary, VaultEvent } from '../types'

const RECONNECT_DELAY_MILLISECONDS = 2000
const INITIAL_RUNS_LIMIT = 20
const INITIAL_VAULT_EVENTS_LIMIT = 50

interface DashboardState {
  connected: boolean
  currentRun: RunDetail | null
  pastRuns: RunSummary[]
  vaultEvents: VaultEvent[]
}

function buildRunSummaryFromStartedMessage(message: {
  run_id: string
  run_type: string
  goal: string
  started_at: string
}): RunSummary {
  return {
    run_id: message.run_id,
    run_type: message.run_type,
    goal: message.goal,
    started_at: message.started_at,
    finished_at: null,
    status: 'running',
  }
}

function copyStagesWithOneAppended(
  existingStages: RunDetail['stages'],
  newStage: RunDetail['stages'][number],
): RunDetail['stages'] {
  const updatedStages: RunDetail['stages'] = []
  for (let stageIndex = 0; stageIndex < existingStages.length; stageIndex++) {
    updatedStages.push(existingStages[stageIndex])
  }
  updatedStages.push(newStage)
  return updatedStages
}

function copyRunsWithOnePrepended(existingRuns: RunSummary[], newRun: RunSummary): RunSummary[] {
  const updatedRuns: RunSummary[] = [newRun]
  for (let runIndex = 0; runIndex < existingRuns.length; runIndex++) {
    updatedRuns.push(existingRuns[runIndex])
  }
  return updatedRuns
}

function copyRunsWithStatusUpdated(existingRuns: RunSummary[], runId: string, newStatus: RunSummary['status']): RunSummary[] {
  const updatedRuns: RunSummary[] = []
  for (let runIndex = 0; runIndex < existingRuns.length; runIndex++) {
    const currentRun = existingRuns[runIndex]
    if (currentRun.run_id === runId) {
      updatedRuns.push({ ...currentRun, status: newStatus })
    } else {
      updatedRuns.push(currentRun)
    }
  }
  return updatedRuns
}

function copyVaultEventsWithOnePrepended(existingEvents: VaultEvent[], newEvent: VaultEvent): VaultEvent[] {
  const updatedEvents: VaultEvent[] = [newEvent]
  for (let eventIndex = 0; eventIndex < existingEvents.length; eventIndex++) {
    updatedEvents.push(existingEvents[eventIndex])
  }
  return updatedEvents
}

// owns the websocket connection to the dashboard backend plus the initial rest
// fetches for state that existed before this browser tab connected. rest gives
// the starting point; the websocket delivers every change after that as a delta
export function useDashboardSocket(): DashboardState {
  const [connected, setConnected] = useState(false)
  const [currentRun, setCurrentRun] = useState<RunDetail | null>(null)
  const [pastRuns, setPastRuns] = useState<RunSummary[]>([])
  const [vaultEvents, setVaultEvents] = useState<VaultEvent[]>([])

  useEffect(() => {
    let isUnmounted = false

    async function loadInitialState() {
      const runsResponse = await fetch('/api/runs?limit=' + INITIAL_RUNS_LIMIT)
      const runsData: RunSummary[] = await runsResponse.json()
      if (isUnmounted === false) {
        setPastRuns(runsData)
      }

      const vaultEventsResponse = await fetch('/api/vault-events?limit=' + INITIAL_VAULT_EVENTS_LIMIT)
      const vaultEventsData: VaultEvent[] = await vaultEventsResponse.json()
      if (isUnmounted === false) {
        setVaultEvents(vaultEventsData)
      }
    }

    loadInitialState()

    return function cleanup() {
      isUnmounted = true
    }
  }, [])

  useEffect(() => {
    let activeSocket: WebSocket | null = null
    let reconnectTimeoutId: number | undefined
    let isUnmounted = false

    function handleMessage(message: DashboardMessage) {
      if (message.type === 'current_run_snapshot') {
        setCurrentRun(message)
        return
      }

      if (message.type === 'run_started') {
        const newRunSummary = buildRunSummaryFromStartedMessage(message)
        setCurrentRun({ ...newRunSummary, stages: [] })
        setPastRuns((previousRuns) => copyRunsWithOnePrepended(previousRuns, newRunSummary))
        return
      }

      if (message.type === 'stage_complete') {
        const newStage = { agent_name: message.agent_name, output_text: message.output_text }
        setCurrentRun((previousRun) => {
          if (previousRun === null || previousRun.run_id !== message.run_id) {
            return previousRun
          }
          return { ...previousRun, stages: copyStagesWithOneAppended(previousRun.stages, newStage) }
        })
        return
      }

      if (message.type === 'run_finished') {
        setCurrentRun((previousRun) => {
          if (previousRun === null || previousRun.run_id !== message.run_id) {
            return previousRun
          }
          return { ...previousRun, status: message.status }
        })
        setPastRuns((previousRuns) => copyRunsWithStatusUpdated(previousRuns, message.run_id, message.status))
        return
      }

      if (message.type === 'vault_event') {
        const newEvent: VaultEvent = {
          event_id: Date.now(),
          description: message.description,
          occurred_at: message.occurred_at,
        }
        setVaultEvents((previousEvents) => copyVaultEventsWithOnePrepended(previousEvents, newEvent))
      }
    }

    function connect() {
      let socketProtocol
      if (window.location.protocol === 'https:') {
        socketProtocol = 'wss:'
      } else {
        socketProtocol = 'ws:'
      }

      const socket = new WebSocket(socketProtocol + '//' + window.location.host + '/ws')
      activeSocket = socket

      socket.onopen = function handleOpen() {
        setConnected(true)
      }

      socket.onclose = function handleClose() {
        setConnected(false)
        if (isUnmounted === false) {
          reconnectTimeoutId = window.setTimeout(connect, RECONNECT_DELAY_MILLISECONDS)
        }
      }

      socket.onerror = function handleError() {
        socket.close()
      }

      socket.onmessage = function handleIncomingMessage(event: MessageEvent) {
        const parsedMessage: DashboardMessage = JSON.parse(event.data)
        handleMessage(parsedMessage)
      }
    }

    connect()

    return function cleanup() {
      isUnmounted = true
      window.clearTimeout(reconnectTimeoutId)
      if (activeSocket !== null) {
        activeSocket.close()
      }
    }
  }, [])

  return { connected, currentRun, pastRuns, vaultEvents }
}
