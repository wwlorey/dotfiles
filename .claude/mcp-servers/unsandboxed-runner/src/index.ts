import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { spawn, type ChildProcess } from "node:child_process";
import { z } from "zod";
import path from "node:path";

const DEFAULT_TIMEOUT_SECS = 300;
const MAX_TIMEOUT_SECS = 600;
const MAX_OUTPUT_BYTES = 512 * 1024; // 512KB per stream

interface RunResult {
  success: boolean;
  exit_code: number | null;
  stdout: string;
  stderr: string;
  timed_out: boolean;
}

function clampTimeout(requested?: number): number {
  const secs = requested ?? DEFAULT_TIMEOUT_SECS;
  return Math.min(Math.max(1, secs), MAX_TIMEOUT_SECS);
}

function resolveCwd(relative?: string): string {
  const base = process.cwd();
  if (!relative) return base;
  const resolved = path.resolve(base, relative);
  if (!resolved.startsWith(base)) {
    throw new Error(`cwd must be relative to project root: ${relative}`);
  }
  return resolved;
}

function truncate(output: string, label: string): string {
  if (Buffer.byteLength(output) <= MAX_OUTPUT_BYTES) return output;
  const truncated = Buffer.from(output).subarray(0, MAX_OUTPUT_BYTES).toString("utf-8");
  return truncated + `\n\n... [${label} truncated at ${MAX_OUTPUT_BYTES / 1024}KB]`;
}

function runCommand(
  command: string,
  args: string[],
  cwd: string,
  timeoutSecs: number
): Promise<RunResult> {
  return new Promise((resolve) => {
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let killed = false;

    const child: ChildProcess = spawn(command, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env },
    });

    child.stdout?.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });

    child.stderr?.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    const timer = setTimeout(() => {
      timedOut = true;
      killed = true;
      child.kill("SIGTERM");
      setTimeout(() => {
        if (!child.killed) child.kill("SIGKILL");
      }, 5000);
    }, timeoutSecs * 1000);

    child.on("close", (code, signal) => {
      clearTimeout(timer);
      resolve({
        success: !timedOut && code === 0,
        exit_code: code,
        stdout: truncate(stdout, "stdout"),
        stderr: truncate(stderr, "stderr"),
        timed_out: timedOut,
      });
    });

    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({
        success: false,
        exit_code: null,
        stdout: truncate(stdout, "stdout"),
        stderr: err.message,
        timed_out: false,
      });
    });
  });
}

function runSmokeTest(
  command: string,
  args: string[],
  cwd: string,
  timeoutSecs: number,
  readyPattern: RegExp,
  failPatterns: RegExp[]
): Promise<RunResult> {
  return new Promise((resolve) => {
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let settled = false;

    const child: ChildProcess = spawn(command, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env },
    });

    function finish(success: boolean) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      child.kill("SIGTERM");
      setTimeout(() => {
        if (!child.killed) child.kill("SIGKILL");
      }, 5000);
      resolve({
        success,
        exit_code: null,
        stdout: truncate(stdout, "stdout"),
        stderr: truncate(stderr, "stderr"),
        timed_out: timedOut,
      });
    }

    child.stdout?.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
      if (readyPattern.test(stdout)) finish(true);
      for (const pat of failPatterns) {
        if (pat.test(stdout)) finish(false);
      }
    });

    child.stderr?.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
      for (const pat of failPatterns) {
        if (pat.test(stderr)) finish(false);
      }
    });

    child.on("close", (code) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        resolve({
          success: false,
          exit_code: code,
          stdout: truncate(stdout, "stdout"),
          stderr: truncate(stderr, "stderr"),
          timed_out: false,
        });
      }
    });

    child.on("error", (err) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        resolve({
          success: false,
          exit_code: null,
          stdout: truncate(stdout, "stdout"),
          stderr: err.message,
          timed_out: false,
        });
      }
    });

    const timer = setTimeout(() => {
      timedOut = true;
      finish(false);
    }, timeoutSecs * 1000);
  });
}

const server = new McpServer({
  name: "unsandboxed-runner",
  version: "1.0.0",
});

server.tool(
  "run_playwright",
  "Run Playwright e2e tests outside the sandbox. Chromium launches normally without bootstrap_check_in restrictions.",
  {
    file: z.string().optional().describe("Specific test file to run (e.g. e2e/settings.test.ts). Omit to run all e2e tests."),
    cwd: z.string().optional().describe("Working directory relative to project root."),
    timeout_secs: z.number().optional().describe("Timeout in seconds (default 300, max 600)."),
  },
  async ({ file, cwd, timeout_secs }) => {
    const resolvedCwd = resolveCwd(cwd);
    const timeout = clampTimeout(timeout_secs);
    const args = ["run", "test:e2e"];
    if (file) args.push(file);

    const result = await runCommand("pnpm", args, resolvedCwd, timeout);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

server.tool(
  "run_tauri_build",
  "Run cargo tauri build outside the sandbox. Has access to code signing, notarization, and full OS APIs.",
  {
    cwd: z.string().optional().describe("Working directory relative to project root."),
    timeout_secs: z.number().optional().describe("Timeout in seconds (default 300, max 600)."),
  },
  async ({ cwd, timeout_secs }) => {
    const resolvedCwd = resolveCwd(cwd);
    const timeout = clampTimeout(timeout_secs);

    const result = await runCommand("cargo", ["tauri", "build"], resolvedCwd, timeout);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

server.tool(
  "smoke_test_tauri",
  "Start cargo tauri dev, wait for the app to boot successfully, then kill it. Catches runtime panics at the Tauri/Rust boundary that cargo build misses (unimplemented!(), wrong async context, etc.).",
  {
    cwd: z.string().optional().describe("Working directory relative to project root."),
    timeout_secs: z.number().optional().describe("Timeout in seconds (default 120, max 600). How long to wait for the app to become ready."),
  },
  async ({ cwd, timeout_secs }) => {
    const resolvedCwd = resolveCwd(cwd);
    const timeout = clampTimeout(timeout_secs ?? 120);

    const readyPattern = /ready in \d+/i;
    const failPatterns = [
      /panicked at/,
      /thread '.*' panicked/,
      /not yet implemented/,
      /fatal error/i,
      /error\[E\d+\]/,
    ];

    const result = await runSmokeTest(
      "cargo",
      ["tauri", "dev"],
      resolvedCwd,
      timeout,
      readyPattern,
      failPatterns
    );
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
