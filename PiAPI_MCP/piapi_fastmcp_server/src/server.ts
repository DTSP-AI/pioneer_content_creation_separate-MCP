/**
 * FastMCP Server Implementation
 *
 * Exposes unified PiAPI tools over HTTP + SSE transport
 */

import { FastMCP } from "fastmcp";
import { z } from "zod";
import { Logger } from "./utils/logger.js";
import { checkBackendHealth } from "./utils/httpClient.js";
import { processImageUnified } from "./tools/imageTool.js";
import { generateVideoUnified } from "./tools/videoTool.js";
import { generateAudioUnified } from "./tools/audioTool.js";
import { CONFIG } from "./config.js";
import type { HealthCheckResponse } from "./types.js";

/**
 * Create and configure FastMCP server instance
 *
 * @returns Configured FastMCP server
 */
export async function createServer(): Promise<FastMCP> {
  Logger.info("🚀 Initializing PiAPI FastMCP Server...");

  // Check Python backend health
  const isBackendHealthy = await checkBackendHealth();
  if (!isBackendHealthy) {
    Logger.warn(
      "⚠️ Python backend health check failed - server will start but tools may fail"
    );
  }

  // Create FastMCP server
  const server = new FastMCP({
    name: "PiAPI-FastMCP",
    version: "1.0.0",
  });

  Logger.info("📦 Registering tools...");

  // ========================================================================
  // Image Processing Tool
  // ========================================================================
  server.addTool({
    name: "process_image_unified",
    description:
      "Generate, edit, or enhance images using AI. Supports text-to-image, " +
      "image-to-image, ControlNet, upscaling, background removal, face swap, " +
      "inpainting, and outpainting.",
    parameters: z.object({
      task_type: z.enum([
        "generate",
        "modify",
        "controlnet",
        "upscale",
        "remove_bg",
        "enhance",
        "faceswap",
        "inpaint",
        "outpaint",
      ]).describe("Image processing task type"),
      prompt: z.string().optional().describe("Text description (required for most tasks)"),
      input_image: z.string().url().optional().describe("Input image URL"),
      model: z.enum(["schnell", "dev"]).default("dev").describe("Flux model (schnell=fast, dev=high quality)"),
      width: z.number().default(1024).describe("Output width"),
      height: z.number().default(1024).describe("Output height"),
    }),
    execute: async (args) => {
      const result = await processImageUnified(args as any, null as any);
      return JSON.stringify(result);
    },
  });

  Logger.info("   ✓ process_image_unified");

  // ========================================================================
  // Video Generation Tool
  // ========================================================================
  server.addTool({
    name: "generate_video_unified",
    description:
      "Generate, animate, or extend videos using AI. Supports Hailuo " +
      "(best quality), Wan (camera control), and Luma (physics) providers.",
    parameters: z.object({
      prompt: z.string().describe("Text description of the video"),
      provider: z.enum(["hailuo", "wan", "luma"]).default("hailuo").describe("Video generation provider"),
      task_type: z.enum(["txt2vid", "img2vid", "extend"]).default("txt2vid").describe("Type of video task"),
      input_image: z.string().url().optional().describe("Input image URL for img2vid"),
      duration: z.number().default(6).describe("Video duration in seconds"),
      resolution: z.enum(["768p", "1080p"]).default("1080p").describe("Output resolution"),
    }),
    execute: async (args) => {
      const result = await generateVideoUnified(args as any, null as any);
      return JSON.stringify(result);
    },
  });

  Logger.info("   ✓ generate_video_unified");

  // ========================================================================
  // Audio Generation Tool
  // ========================================================================
  server.addTool({
    name: "generate_audio_unified",
    description:
      "Generate music or synthesize speech using AI. Supports Udio (music) " +
      "and F5-TTS (voice cloning) providers.",
    parameters: z.object({
      prompt: z.string().describe("Music description or text to synthesize"),
      provider: z.enum(["udio", "f5tts"]).default("udio").describe("Audio provider"),
      content_type: z.enum(["music", "speech"]).default("music").describe("Type of audio content"),
      lyrics_type: z.enum(["generate", "user", "instrumental"]).default("generate").describe("Lyrics mode (Udio only)"),
      style: z.string().optional().describe("Music style tags"),
    }),
    execute: async (args) => {
      const result = await generateAudioUnified(args as any, null as any);
      return JSON.stringify(result);
    },
  });

  Logger.info("   ✓ generate_audio_unified");

  // ========================================================================
  // Health Check Tool
  // ========================================================================
  server.addTool({
    name: "health_check",
    description: "Check FastMCP server and Python backend health status",
    parameters: z.object({}),
    execute: async () => {
      const backendHealthy = await checkBackendHealth();
      const response: HealthCheckResponse = {
        server: "PiAPI-FastMCP",
        backend: CONFIG.backendUrl,
        status: backendHealthy ? "ready" : "backend_unreachable",
        env: CONFIG.env,
        timestamp: new Date().toISOString(),
      };
      Logger.info(`Health check: ${response.status}`);
      return JSON.stringify(response);
    },
  });

  Logger.info("   ✓ health_check");

  Logger.info(`✅ FastMCP server configured successfully`);
  Logger.info(`   Tools registered: 4`);
  Logger.info(`   Transport: HTTP Streaming (SSE)`);
  Logger.info(`   Port: ${CONFIG.port}`);

  return server;
}

/**
 * Start the FastMCP server with HTTP Streaming transport
 *
 * @param server - Configured FastMCP server instance
 */
export async function startServer(server: FastMCP): Promise<void> {
  try {
    server.start({
      transportType: "httpStream",
      httpStream: {
        endpoint: "/sse",
        port: CONFIG.port,
      },
    });
    Logger.info(`🎯 FastMCP server listening on port ${CONFIG.port}`);
    Logger.info(`🔗 SSE endpoint: http://localhost:${CONFIG.port}/sse`);
    Logger.info(`📡 Connected to Python backend: ${CONFIG.backendUrl}`);
  } catch (error) {
    Logger.error("Failed to start FastMCP server", error);
    throw error;
  }
}
