/**
 * Unified Video Generation Tool
 *
 * Bridges FastMCP calls to Python backend /generate_video endpoint
 */

import { callPythonEndpoint } from "../utils/httpClient.js";
import { Logger } from "../utils/logger.js";
import type { ToolInput, PiAPITaskResult } from "../types.js";

/**
 * Generate video via unified Python backend
 *
 * @param input - Tool input matching UnifiedVideoInput schema
 * @param ctx - FastMCP context for progress reporting
 * @returns Task result with task_id, status, and output
 */
export async function generateVideoUnified(
  input: ToolInput,
  ctx: any
): Promise<PiAPITaskResult> {
  try {
    Logger.info("🎬 Executing generate_video_unified tool via Python backend...");
    Logger.debug(`Input: ${JSON.stringify(input, null, 2)}`);

    // Report progress to MCP context
    if (ctx && ctx.report) {
      await ctx.report({ progress: 0.1, message: "Starting video generation..." });
    }

    // Call Python backend
    const result = await callPythonEndpoint("/generate_video", input);

    // Report completion
    if (ctx && ctx.report) {
      await ctx.report({ progress: 1.0, message: "Video generation complete" });
    }

    Logger.info(`✅ Video task completed: ${result.task_id}`);
    return result;
  } catch (err: any) {
    Logger.error("❌ Video generation failed", err);

    return {
      task_id: "unknown",
      status: "Failed",
      error: err.message || "Unknown error during video generation",
    };
  }
}
