/**
 * Lightweight logger for FastMCP server
 */

type LogLevel = "info" | "warn" | "error" | "debug";

export class Logger {
  private static formatMessage(level: LogLevel, message: string): string {
    const timestamp = new Date().toISOString();
    const emoji = {
      info: "🟢",
      warn: "🟡",
      error: "🔴",
      debug: "🔵",
    }[level];
    return `${emoji} [${level.toUpperCase()}] ${timestamp} - ${message}`;
  }

  static info(message: string): void {
    console.log(this.formatMessage("info", message));
  }

  static warn(message: string): void {
    console.warn(this.formatMessage("warn", message));
  }

  static error(message: string, err?: any): void {
    console.error(this.formatMessage("error", message));
    if (err) {
      if (err instanceof Error) {
        console.error(`   Stack: ${err.stack}`);
      } else {
        console.error(`   Details: ${JSON.stringify(err, null, 2)}`);
      }
    }
  }

  static debug(message: string): void {
    if (process.env.LOG_LEVEL === "debug") {
      console.debug(this.formatMessage("debug", message));
    }
  }
}
