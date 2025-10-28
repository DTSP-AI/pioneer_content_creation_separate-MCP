// Workflow Types
export type WorkflowStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'partial_success';
export type WorkflowPhase =
  | 'supervisor'
  | 'content_creation'
  | 'publishing'
  | 'completed';
export type Platform = 'tiktok' | 'youtube_shorts';

export interface WorkflowState {
  workflow_id: string;
  user_request: string;
  target_platforms: Platform[];
  workflow_status: WorkflowStatus;
  current_phase: WorkflowPhase;
  script?: string;
  video_path?: string;
  publish_results?: Record<Platform, PublishResult>;
  cost_breakdown?: Record<string, number>;
  total_cost_usd?: number;
  error_message?: string;
  created_at: string;
  updated_at?: string;
}

export interface PublishResult {
  status: 'success' | 'failed';
  url?: string;
  platform_video_id?: string;
  error?: string;
  metadata?: Record<string, any>;
}

export interface WorkflowCreate {
  user_request: string;
  target_platforms: Platform[];
  cost_limit_usd?: number;
}

export interface WorkflowUpdate {
  event_type: string;
  message?: string;
  state?: Partial<WorkflowState>;
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
}

export interface ApiError {
  detail: string;
}

// Chat & Thread Types
export interface ChatMessage {
  id: string;
  thread_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  metadata?: {
    workflow_id?: string;
    awaiting_approval?: boolean;
    workflow_proposal?: WorkflowProposal;
    workflow_completed?: boolean;
    video_url?: string;
    publish_results?: Record<Platform, PublishResult>;
  };
}

export interface WorkflowProposal {
  user_request: string;
  target_platforms: Platform[];
  estimated_cost_usd?: number;
  reasoning?: string;
}

export interface ChatThread {
  thread_id: string;
  title: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string;
  active_workflow_id?: string;
}

export interface SendMessageRequest {
  thread_id?: string;
  message: string;
  user_id?: string;
}

export interface SendMessageResponse {
  message: ChatMessage;
  thread: ChatThread;
  workflow_created?: WorkflowState;
}
