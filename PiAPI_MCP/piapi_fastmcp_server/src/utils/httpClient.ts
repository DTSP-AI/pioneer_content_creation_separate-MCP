/**
 * HTTP client for calling Python backend
 */

import axios, { AxiosInstance, AxiosError } from "axios";
import { CONFIG } from "../config.js";
import { Logger } from "./logger.js";

/**
 * Configured axios instance for Python backend
 */
export const httpClient: AxiosInstance = axios.create({
  baseURL: CONFIG.backendUrl,
  timeout: 300000, // 5 minutes for long-running tasks
  headers: {
    "Content-Type": "application/json",
    "User-Agent": "PiAPI-FastMCP/1.0.0",
  },
});

/**
 * Call a Python backend endpoint with proper error handling
 *
 * @param endpoint - API endpoint path (e.g., "/process_image")
 * @param payload - Request body
 * @returns Response data
 * @throws Error with descriptive message on failure
 */
export async function callPythonEndpoint(
  endpoint: string,
  payload: any
): Promise<any> {
  const startTime = Date.now();

  try {
    Logger.info(`Calling Python backend → POST ${endpoint}`);
    Logger.debug(`Payload: ${JSON.stringify(payload, null, 2)}`);

    const response = await httpClient.post(endpoint, payload);

    const duration = Date.now() - startTime;
    Logger.info(`Python backend responded in ${duration}ms`);
    Logger.debug(`Response: ${JSON.stringify(response.data, null, 2)}`);

    return response.data;
  } catch (error) {
    const duration = Date.now() - startTime;

    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError;

      if (axiosError.response) {
        // Server responded with error status
        Logger.error(
          `Python backend error (${axiosError.response.status}) after ${duration}ms: ${endpoint}`,
          axiosError.response.data
        );
        throw new Error(
          `Backend error: ${JSON.stringify(axiosError.response.data)}`
        );
      } else if (axiosError.request) {
        // No response received
        Logger.error(
          `Python backend unreachable after ${duration}ms: ${endpoint}`,
          axiosError.message
        );
        throw new Error(
          `Backend unreachable at ${CONFIG.backendUrl}. Is the Python service running?`
        );
      }
    }

    // Generic error
    Logger.error(`Unexpected error calling ${endpoint}`, error);
    throw new Error(
      error instanceof Error ? error.message : "Unknown error"
    );
  }
}

/**
 * Health check for Python backend
 *
 * @returns true if backend is reachable
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    Logger.info("Checking Python backend health...");
    const response = await httpClient.get("/health", { timeout: 5000 });
    Logger.info("✅ Python backend is healthy");
    return response.status === 200;
  } catch (error) {
    Logger.warn("⚠️ Python backend health check failed");
    Logger.debug(`Health check error: ${error}`);
    return false;
  }
}
