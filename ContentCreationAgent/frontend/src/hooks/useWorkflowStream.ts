import { useEffect, useRef } from 'react'
import { apiClient } from '../services/api'
import { useWorkflowStore } from '../store/workflow'
import type { WorkflowUpdate } from '../types'

export function useWorkflowStream(workflowId: string | null) {
  const eventSourceRef = useRef<EventSource | null>(null)
  const { addRealtimeUpdate, updateWorkflow } = useWorkflowStore()

  useEffect(() => {
    if (!workflowId) return

    console.log(`[SSE] Connecting to workflow stream: ${workflowId}`)

    eventSourceRef.current = apiClient.streamWorkflow(
      workflowId,
      (update: WorkflowUpdate) => {
        console.log(`[SSE] Received update:`, update)
        addRealtimeUpdate(update)
        if (update.state) {
          updateWorkflow(update.state)
        }
      }
    )

    return () => {
      if (eventSourceRef.current) {
        console.log(`[SSE] Disconnecting from workflow stream: ${workflowId}`)
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
    }
  }, [workflowId, addRealtimeUpdate, updateWorkflow])

  return {
    isConnected: !!eventSourceRef.current,
    disconnect: () => eventSourceRef.current?.close(),
  }
}
