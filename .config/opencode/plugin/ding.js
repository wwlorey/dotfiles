import { spawn } from "child_process";

const playDing = () => {
  try {
    const proc = spawn("afplay", ["/System/Library/Sounds/Blow.aiff"], {
      stdio: "ignore",
      detached: true,
    });
    proc.unref();
  } catch (error) {
    // Silent error handling
  }
};

export const Ding = async ({ project, client, $, directory, worktree }) => {
  console.log("Plugin initialized!");

  // Source: https://opencode.ai/docs/plugins/#send-notifications
  return {
    event: async ({ event }) => {
      // Send notification on session completion
      if (event.type === "session.idle") {
        playDing();
      }
    },
  }
};

