import { spawn } from "node:child_process";
import { mkdir, appendFile } from "node:fs/promises";

const INTERVAL_MS = Number(
  process.env.PROVIDER_DAEMON_INTERVAL_MS || 1800000
);

const LOG_DIR = "provider-output/daemon";
const LOG_FILE = `${LOG_DIR}/daemon.log`;

let stopping = false;

function ts() {
  return new Date().toISOString();
}

async function log(message) {
  const line = `[${ts()}] ${message}\n`;
  console.log(line.trim());
  await mkdir(LOG_DIR, { recursive: true });
  await appendFile(LOG_FILE, line);
}

function run(command, args = []) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      stdio: "inherit",
      env: process.env
    });

    child.on("error", (err) => {
      resolve({ code: -1, error: err });
    });

    child.on("exit", (code) => {
      resolve({ code });
    });
  });
}

async function cycle() {
  await log("========================================");
  await log("PROVIDER DAEMON CYCLE");
  await log("MODE=READ_ONLY");
  await log("POST=DISABLED");
  await log("WALLET=NOT_USED");
  await log("SIGNING=NOT_USED");
  await log("SUBMISSION=NOT_PERFORMED");

  await log("Step 1: AACP intake");

  const intake = await run("pnpm", ["run", "intake"]);

  if (intake.code !== 0) {
    await log(`INTAKE_FAILED code=${intake.code}`);
    return;
  }

  await log("Step 2: automatic job processing");

  const process = await run("pnpm", ["run", "auto"]);

  if (process.code !== 0) {
    await log(`PROCESS_FAILED code=${process.code}`);
    return;
  }

  await log("Step 3: offer draft generation");

  const draft = await run("pnpm", ["run", "offer-draft"]);

  if (draft.code !== 0) {
    await log(`OFFER_DRAFT_FAILED code=${draft.code}`);
    return;
  }

  await log("CYCLE_COMPLETE");
  await log("MANUAL_APPROVAL_REQUIRED");
  await log("LIVE_SUBMISSION=BLOCKED");
}

function shutdown(signal) {
  if (stopping) return;

  stopping = true;

  console.log("");
  console.log(`[${ts()}] SHUTDOWN ${signal}`);
  console.log(`[${ts()}] POST=DISABLED`);
  console.log(`[${ts()}] WALLET=NOT_USED`);
  console.log(`[${ts()}] SIGNING=NOT_USED`);
  console.log(`[${ts()}] SUBMISSION=NOT_PERFORMED`);

  process.exit(0);
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

console.log("========================================");
console.log(" PROVIDER DAEMON v1.0.0");
console.log("========================================");
console.log(`Interval: ${Math.round(INTERVAL_MS / 1000)} seconds`);
console.log("Mode    : READ-ONLY");
console.log("POST    : DISABLED");
console.log("Wallet  : NOT USED");
console.log("Signing : NOT USED");
console.log("Submit  : NOT PERFORMED");
console.log("");

while (!stopping) {
  await cycle();

  if (!stopping) {
    await log(
      `NEXT_CYCLE_IN=${Math.round(INTERVAL_MS / 1000)}s`
    );

    await new Promise((resolve) =>
      setTimeout(resolve, INTERVAL_MS)
    );
  }
}
