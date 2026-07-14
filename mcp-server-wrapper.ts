#!/usr/bin/env node

/**
 * TypeScript wrapper for the Python Simplenote MCP Server
 * This allows mcp-evals to work with the Python server by providing a TypeScript entry point
 */

import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

// Get current directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to the Python server
const PYTHON_SERVER_PATH = path.join(__dirname, "simplenote_mcp_server.py");
// Prefer the project virtualenv's interpreter so the server sees its installed
// dependencies (e.g. the `mcp` package) instead of whatever `python3` resolves
// to on PATH.
const VENV_PYTHON_PATH = path.join(__dirname, ".venv", "bin", "python3");

async function main() {
  try {
    // Check if Python server exists
    const fs = await import("fs");
    if (!fs.existsSync(PYTHON_SERVER_PATH)) {
      console.error(`Python server not found at: ${PYTHON_SERVER_PATH}`);
      process.exit(1);
    }

    const pythonExecutable = fs.existsSync(VENV_PYTHON_PATH)
      ? VENV_PYTHON_PATH
      : "python3";

    // Start the Python MCP server as a child process
    const pythonProcess = spawn(pythonExecutable, [PYTHON_SERVER_PATH], {
      stdio: ["pipe", "pipe", "inherit"], // stdin, stdout, stderr
      env: {
        ...process.env,
        // Ensure MCP server runs in the right mode
        LOG_LEVEL: "INFO",
      },
    });

    // Handle Python process errors
    pythonProcess.on("error", (error) => {
      console.error("Failed to start Python server:", error);
      process.exit(1);
    });

    pythonProcess.on("exit", (code, signal) => {
      console.error(`Python server exited with code ${code}, signal ${signal}`);
      process.exit(code || 1);
    });

    // Forward stdin to Python server
    process.stdin.pipe(pythonProcess.stdin);

    // Forward Python server stdout to our stdout
    pythonProcess.stdout.pipe(process.stdout);

    // Handle process termination
    const cleanup = () => {
      if (!pythonProcess.killed) {
        pythonProcess.kill("SIGTERM");
        setTimeout(() => {
          if (!pythonProcess.killed) {
            pythonProcess.kill("SIGKILL");
          }
        }, 5000);
      }
    };

    process.on("SIGINT", cleanup);
    process.on("SIGTERM", cleanup);
    process.on("exit", cleanup);

    // Keep the wrapper alive
    await new Promise((resolve, reject) => {
      pythonProcess.on("exit", resolve);
      pythonProcess.on("error", reject);
    });
  } catch (error) {
    console.error("Error in MCP server wrapper:", error);
    process.exit(1);
  }
}

// Start the wrapper
main().catch((error) => {
  console.error("Unhandled error:", error);
  process.exit(1);
});
