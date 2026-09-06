import { spawn } from "node:child_process";
import { mkdir, appendFile } from "node:fs/promises";
import { existsSync } from "node:fs";

const INTERVAL_MS = Number(
  process.env.PROVIDER_DAEMON_INTERVAL_MS || 1800000
);

const LOG_DIR = "provider-output/daemon";
const LOG_FILE = `${LOG_DIR}/daemon.log`;

let stopping = false;
let previousBackendState = null;

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

  // ------------------------------------------------------------
  // Step 1: Fresh AACP intake
  // ------------------------------------------------------------
  await log("Step 1: AACP intake");

  const intake = await run("pnpm", ["run", "intake"]);

  if (intake.code !== 0) {
    await log(`INTAKE_FAILED code=${intake.code}`);
    await log("SKIP_PROCESSING=TRUE");
    await log("SKIP_OFFER_DRAFT=TRUE");
    await log("LIVE_SUBMISSION=BLOCKED");
    await log("CYCLE_COMPLETE");
    return;
  }

  let intakeState;

  try {
    const raw = await (
      await import("node:fs/promises")
    ).readFile(
      "provider-output/aacp-intake.json",
      "utf8"
    );

    intakeState = JSON.parse(raw);
  } catch (error) {
    await log(
      `INTAKE_STATE_READ_FAILED=${error.message}`
    );
    await log("SKIP_PROCESSING=TRUE");
    await log("SKIP_OFFER_DRAFT=TRUE");
    await log("LIVE_SUBMISSION=BLOCKED");
    await log("CYCLE_COMPLETE");
    return;
  }

  // ------------------------------------------------------------
  // Backend state + recovery detection
  // ------------------------------------------------------------
  const backendHealthy =
    intakeState.summary?.backendAvailable === true;

  const backendState =
    backendHealthy ? "HEALTHY" : "DOWN";

  await log(`AACP_STATE=${backendState}`);

  const recovered =
    previousBackendState === "DOWN" &&
    backendState === "HEALTHY";

  if (recovered) {
    await log("AACP_RECOVERED");
    await log("ACTION=READ_ONLY_DISCOVERY_ALLOWED");
    await log("RECOVERY_MODE=SAFE");
  }

  previousBackendState = backendState;

  // ------------------------------------------------------------
  // HARD SAFETY GATE: backend must explicitly be healthy
  // ------------------------------------------------------------
  if (!backendHealthy) {
    await log("BACKEND_UNAVAILABLE");
    await log("SKIP_PROCESSING=TRUE");
    await log("SKIP_OFFER_DRAFT=TRUE");
    await log("LIVE_SUBMISSION=BLOCKED");
    await log("CYCLE_COMPLETE");
    return;
  }

  await log("DISCOVERY=READ_ONLY");
  await log("PROCESS=ALLOWED");
  await log("OFFER_DRAFT=ALLOWED");

  const jobs = Array.isArray(intakeState.jobs)
    ? intakeState.jobs
    : [];

  if (jobs.length === 0) {
    await log("NO_JOBS_AVAILABLE");
    await log("SKIP_PROCESSING=TRUE");
    await log("SKIP_OFFER_DRAFT=TRUE");
    await log("CYCLE_COMPLETE");
    return;
  }

  await log(`JOBS_AVAILABLE=${jobs.length}`);

  // ------------------------------------------------------------
  // Step 2: Automatic job processing
  // ------------------------------------------------------------
  await log("Step 2: automatic job processing");

  const process = await run(
    "pnpm",
    ["run", "auto"]
  );

  if (process.code !== 0) {
    await log(
      `AUTO_PROCESSOR_FAILED code=${process.code}`
    );
    await log("SKIP_OFFER_DRAFT=TRUE");
    await log("LIVE_SUBMISSION=BLOCKED");
    await log("CYCLE_COMPLETE");
    return;
  }

  // ------------------------------------------------------------
  // Read processor aggregate result
  // ------------------------------------------------------------
  let processorState;

  try {
    const raw = await (
      await import("node:fs/promises")
    ).readFile(
      "provider-output/auto-processor-result.json",
      "utf8"
    );

    processorState = JSON.parse(raw);
  } catch (error) {
    await log(
      `PROCESSOR_RESULT_READ_FAILED=${error.message}`
    );
    await log("SKIP_OFFER_DRAFT=TRUE");
    await log("LIVE_SUBMISSION=BLOCKED");
    await log("CYCLE_COMPLETE");
    return;
  }

  const results = Array.isArray(
    processorState.results
  )
    ? processorState.results
    : [];

  const processed = results.filter(
    item =>
      item.status === "PROCESSED" &&
      typeof item.output === "string" &&
      item.output.length > 0
  );

  await log(
    `PROCESSOR_RESULTS=${results.length}`
  );

  await log(
    `PROCESSOR_SUCCESS=${processed.length}`
  );

  // ------------------------------------------------------------
  // Step 3: Generate DRAFT ONLY offers
  // ------------------------------------------------------------
  await log("Step 3: offer draft generation");

  let drafts = 0;
  let skipped = 0;

  for (const item of processed) {
    const processorFile = item.output;

    if (!existsSync(processorFile)) {
      skipped += 1;

      await log(
        `OFFER_DRAFT_SKIP=${item.jobId}:PROCESSOR_FILE_NOT_FOUND`
      );

      continue;
    }

    await log(
      `OFFER_DRAFT_START=${item.jobId}`
    );

    const draft = await run(
      "pnpm",
      ["run", "offer-draft", processorFile]
    );

    if (draft.code === 0) {
      drafts += 1;

      await log(
        `OFFER_DRAFT_READY=${item.jobId}`
      );
    } else if (draft.code === 2) {
      skipped += 1;

      await log(
        `OFFER_DRAFT_BLOCKED=${item.jobId}:NOT_ELIGIBLE`
      );
    } else {
      skipped += 1;

      await log(
        `OFFER_DRAFT_FAILED=${item.jobId} code=${draft.code}`
      );
    }
  }

  await log(`OFFER_DRAFT_COUNT=${drafts}`);
  await log(`OFFER_DRAFT_SKIPPED=${skipped}`);

  // ------------------------------------------------------------
  // HARD STOP
  // ------------------------------------------------------------
  await log("LIVE_SUBMISSION=BLOCKED");
  await log("MANUAL_APPROVAL_REQUIRED");
  await log("WALLET=NOT_USED");
  await log("SIGNING=NOT_USED");
  await log("BROADCAST=NOT_USED");
  await log("SUBMISSION=NOT_PERFORMED");
  await log("CYCLE_COMPLETE");
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
console.log(" PROVIDER DAEMON v1.2.0");
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
