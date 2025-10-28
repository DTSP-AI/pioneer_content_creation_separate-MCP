import dotenv from "dotenv";
dotenv.config();

export const CONFIG = {
  port: parseInt(process.env.PORT || "8809", 10),
  backendUrl: process.env.PY_BACKEND_URL || "http://localhost:8000",
  env: process.env.NODE_ENV || "development",
  logLevel: process.env.LOG_LEVEL || "info",
} as const;

export function validateConfig(): void {
  if (!CONFIG.backendUrl) {
    throw new Error("PY_BACKEND_URL environment variable is required");
  }
  console.log(`✅ Configuration loaded:`);
  console.log(`   Port: ${CONFIG.port}`);
  console.log(`   Backend: ${CONFIG.backendUrl}`);
  console.log(`   Environment: ${CONFIG.env}`);
}
