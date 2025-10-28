/**
 * Type definitions for PiAPI FastMCP Server
 */

/**
 * Result structure returned by Python backend tasks
 */
export interface PiAPITaskResult {
  task_id: string;
  status: string;
  output?: any;
  error?: string;
}

/**
 * Generic tool input (typed via JSON Schema in FastMCP)
 */
export interface ToolInput {
  [key: string]: any;
}

/**
 * Health check response
 */
export interface HealthCheckResponse {
  server: string;
  backend: string;
  status: string;
  env: string;
  timestamp: string;
}

/**
 * Error response structure
 */
export interface ErrorResponse {
  task_id: string;
  status: "Failed";
  error: string;
}
