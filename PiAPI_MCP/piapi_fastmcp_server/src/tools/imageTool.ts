/**
 * Unified Image Processing Tool
 *
 * Bridges FastMCP calls to Python backend /process_image endpoint
 */

import { callPythonEndpoint } from "../utils/httpClient.js";
import { Logger } from "../utils/logger.js";
import type { ToolInput, PiAPITaskResult } from "../types.js";

/**
 * Process image via unified Python backend
 *
 * @param input - Tool input matching UnifiedImageInput schema
 * @param ctx - FastMCP context for progress reporting
 * @returns Task result with task_id, status, and output
 */
export async function processImageUnified(
  input: ToolInput,
  ctx: any
): Promise<PiAPITaskResult> {
  try {
    Logger.info("🎨 Executing process_image_unified tool via Python backend...");
    Logger.debug(`Input: ${JSON.stringify(input, null, 2)}`);

    // Report progress to MCP context
    if (ctx && ctx.report) {
      await ctx.report({ progress: 0.1, message: "Starting image processing..." });
    }

    // Call Python backend
    const result = await callPythonEndpoint("/process_image", input);

    // Report completion
    if (ctx && ctx.report) {
      await ctx.report({ progress: 1.0, message: "Image processing complete" });
    }

    Logger.info(`✅ Image task completed: ${result.task_id}`);
    return result;
  } catch (err: any) {
    Logger.error("❌ Image generation failed", err);

    return {
      task_id: "unknown",
      status: "Failed",
      error: err.message || "Unknown error during image processing",
    };
  }
}
