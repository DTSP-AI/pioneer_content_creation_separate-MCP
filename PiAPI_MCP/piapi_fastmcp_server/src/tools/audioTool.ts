/**
 * Unified Audio Generation Tool
 *
 * Bridges FastMCP calls to Python backend /generate_audio endpoint
 */

import { callPythonEndpoint } from "../utils/httpClient.js";
import { Logger } from "../utils/logger.js";
import type { ToolInput, PiAPITaskResult } from "../types.js";

/**
 * Generate audio via unified Python backend
 *
 * @param input - Tool input matching UnifiedAudioInput schema
 * @param ctx - FastMCP context for progress reporting
 * @returns Task result with task_id, status, and output
 */
export async function generateAudioUnified(
  input: ToolInput,
  ctx: any
): Promise<PiAPITaskResult> {
  try {
    Logger.info("🎵 Executing generate_audio_unified tool via Python backend...");
    Logger.debug(`Input: ${JSON.stringify(input, null, 2)}`);

    // Report progress to MCP context
    if (ctx && ctx.report) {
      await ctx.report({ progress: 0.1, message: "Starting audio generation..." });
    }

    // Call Python backend
    const result = await callPythonEndpoint("/generate_audio", input);

    // Report completion
    if (ctx && ctx.report) {
      await ctx.report({ progress: 1.0, message: "Audio generation complete" });
    }

    Logger.info(`✅ Audio task completed: ${result.task_id}`);
    return result;
  } catch (err: any) {
    Logger.error("❌ Audio generation failed", err);

    return {
      task_id: "unknown",
      status: "Failed",
      error: err.message || "Unknown error during audio generation",
    };
  }
}
