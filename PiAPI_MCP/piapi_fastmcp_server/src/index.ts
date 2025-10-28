/**
 * PiAPI FastMCP Server - Entry Point
 *
 * TypeScript FastMCP bridge to Python PiAPI backend
 */

import { createServer, startServer } from "./server.js";
import { validateConfig } from "./config.js";
import { Logger } from "./utils/logger.js";

/**
 * Main entry point
 */
async function main(): Promise<void> {
  try {
    Logger.info("=" .repeat(60));
    Logger.info("PiAPI FastMCP Server v1.0.0");
    Logger.info("=" .repeat(60));

    // Validate configuration
    validateConfig();

    // Create server
    const server = await createServer();

    // Start listening
    await startServer(server);

    // Graceful shutdown handlers
    const shutdown = async (signal: string) => {
      Logger.info(`\n📴 Received ${signal}, shutting down gracefully...`);
      process.exit(0);
    };

    process.on("SIGINT", () => shutdown("SIGINT"));
    process.on("SIGTERM", () => shutdown("SIGTERM"));

    Logger.info("🟢 Server is ready to accept connections");
  } catch (error) {
    Logger.error("💥 Fatal error during server startup", error);
    process.exit(1);
  }
}

// Run the server
main().catch((error) => {
  Logger.error("Unhandled error in main()", error);
  process.exit(1);
});
