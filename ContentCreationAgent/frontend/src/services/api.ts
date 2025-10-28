import axios, { type AxiosInstance, type AxiosError } from 'axios'
import type {
  WorkflowState,
  WorkflowCreate,
  WorkflowUpdate,
  HealthStatus,
  ApiError,
  ChatThread,
  ChatMessage,
  SendMessageRequest,
  SendMessageResponse,
} from '../types'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8006'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        const message = error.response?.data?.detail || error.message
        return Promise.reject(new Error(message))
      }
    )
  }

  async checkHealth(): Promise<HealthStatus> {
    const response = await this.client.get<HealthStatus>('/health')
    return response.data
  }

  async createWorkflow(data: WorkflowCreate): Promise<WorkflowState> {
    const response = await this.client.post<WorkflowState>('/api/workflows', {
      ...data,
      tenant_id: 'default-tenant',
      user_id: 'default-user',
      thread_id: `thread-${Date.now()}`,
    })
    return response.data
  }

  async getWorkflow(workflow_id: string): Promise<WorkflowState> {
    const response = await this.client.get<WorkflowState>(`/api/workflows/${workflow_id}`)
    return response.data
  }

  async listWorkflows(limit: number = 20): Promise<WorkflowState[]> {
    const response = await this.client.get<WorkflowState[]>('/api/workflows', {
      params: { limit },
    })
    return response.data
  }

  streamWorkflow(workflow_id: string, onUpdate: (update: WorkflowUpdate) => void): EventSource {
    const eventSource = new EventSource(
      `${API_BASE_URL}/api/workflows/${workflow_id}/stream`
    )

    eventSource.onmessage = (event) => {
      try {
        const update = JSON.parse(event.data) as WorkflowUpdate
        onUpdate(update)
      } catch (error) {
        console.error('Failed to parse SSE update:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error)
      eventSource.close()
    }

    return eventSource
  }

  // Chat/Thread endpoints
  async listThreads(user_id: string = 'default-user'): Promise<ChatThread[]> {
    const response = await this.client.get<ChatThread[]>('/api/chat/threads', {
      params: { user_id },
    })
    return response.data
  }

  async getThread(thread_id: string): Promise<ChatThread> {
    const response = await this.client.get<ChatThread>(`/api/chat/threads/${thread_id}`)
    return response.data
  }

  async getMessages(thread_id: string): Promise<ChatMessage[]> {
    const response = await this.client.get<ChatMessage[]>(`/api/chat/threads/${thread_id}/messages`)
    return response.data
  }

  async sendMessage(data: SendMessageRequest): Promise<SendMessageResponse> {
    const response = await this.client.post<SendMessageResponse>('/api/chat/send', {
      ...data,
      user_id: data.user_id || 'default-user',
    })
    return response.data
  }

  async approveWorkflow(thread_id: string, message_id: string): Promise<WorkflowState> {
    const response = await this.client.post<WorkflowState>(
      `/api/chat/threads/${thread_id}/messages/${message_id}/approve`
    )
    return response.data
  }

  async rejectWorkflow(thread_id: string, message_id: string, reason?: string): Promise<void> {
    await this.client.post(`/api/chat/threads/${thread_id}/messages/${message_id}/reject`, {
      reason,
    })
  }

  // Additional workflow endpoints
  async getWorkflowStatus(workflow_id: string): Promise<WorkflowState> {
    const response = await this.client.get<WorkflowState>(`/api/workflows/${workflow_id}/status`)
    return response.data
  }

  async getWorkflowResults(workflow_id: string): Promise<any> {
    const response = await this.client.get(`/api/workflows/${workflow_id}/results`)
    return response.data
  }

  // Health check endpoints
  async checkDetailedHealth(): Promise<any> {
    const response = await this.client.get('/health/detailed')
    return response.data
  }
}

export const apiClient = new ApiClient()
