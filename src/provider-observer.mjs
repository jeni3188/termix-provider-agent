import fs from "node:fs";
import path from "node:path";

const BASE_URL =
  process.env.TERMIX_AACP_URL ||
  "https://aacp-backend.termix.live";

const OUTPUT_DIR =
  path.resolve(
    process.env.AACP_OBSERVER_OUTPUT ||
      path.join("provider-output", "aacp-observer")
  );

const STATUS_FILE =
  path.join(
    OUTPUT_DIR,
    "latest-backend-status.json"
  );

const HISTORY_FILE =
  path.join(
    OUTPUT_DIR,
    "observer-history.jsonl"
  );

const TIMEOUT_MS = 15000;

export function loadPreviousSnapshot(
  statusFile = STATUS_FILE
) {
  if (!fs.existsSync(statusFile)) {
    return null;
  }

  try {
    return JSON.parse(
      fs.readFileSync(
        statusFile,
        "utf8"
      )
    );
  } catch {
    return null;
  }
}

export async function probe(
  endpoint,
  baseUrl = BASE_URL
) {
  const url =
    `${baseUrl.replace(/\/$/, "")}${endpoint}`;

  const controller =
    new AbortController();

  const timer =
    setTimeout(
      () => controller.abort(),
      TIMEOUT_MS
    );

  const started =
    Date.now();

  try {
    const response =
      await fetch(
        url,
        {
          method: "GET",
          signal: controller.signal,
          headers: {
            accept: "application/json"
          }
        }
      );

    return {
      endpoint,
      url,
      httpStatus: response.status,
      ok: response.ok,
      elapsedMs:
        Date.now() - started
    };
  } catch (error) {
    return {
      endpoint,
      url,
      httpStatus: null,
      ok: false,
      elapsedMs:
        Date.now() - started,
      error:
        error?.name === "AbortError"
          ? "TIMEOUT"
          : error.message
    };
  } finally {
    clearTimeout(timer);
  }
}

export function determineState(
  config,
  jobs
) {
  if (
    config.ok &&
    jobs.ok
  ) {
    return "HEALTHY";
  }

  return "BACKEND_UNAVAILABLE";
}

export function determineRecovery(
  previousState,
  currentState
) {
  return (
    previousState ===
      "BACKEND_UNAVAILABLE" &&
    currentState ===
      "HEALTHY"
  );
}

export function buildSnapshot({
  previousState,
  config,
  jobs,
  backend = BASE_URL,
  timestamp = new Date().toISOString()
}) {
  const state =
    determineState(
      config,
      jobs
    );

  const recovered =
    determineRecovery(
      previousState,
      state
    );

  return {
    observer:
      "TermiX AACP Backend Observer",

    version:
      "1.2.0",

    timestamp,

    mode:
      "READ_ONLY",

    backend,

    state,

    previousState,

    recovered,

    probes: {
      config,
      jobs
    },

    safety: {
      getOnly: true,
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false
    }
  };
}

export function saveSnapshot(
  snapshot,
  outputDir = OUTPUT_DIR
) {
  const statusFile =
    path.join(
      outputDir,
      "latest-backend-status.json"
    );

  const historyFile =
    path.join(
      outputDir,
      "observer-history.jsonl"
    );

  fs.mkdirSync(
    outputDir,
    { recursive: true }
  );

  fs.writeFileSync(
    statusFile,
    JSON.stringify(
      snapshot,
      null,
      2
    ) + "\n"
  );

  fs.appendFileSync(
    historyFile,
    JSON.stringify(snapshot) + "\n"
  );

  return {
    statusFile,
    historyFile
  };
}

export async function observeOnce({
  baseUrl = BASE_URL,
  outputDir = OUTPUT_DIR
} = {}) {
  const statusFile =
    path.join(
      outputDir,
      "latest-backend-status.json"
    );

  const previous =
    loadPreviousSnapshot(
      statusFile
    );

  const config =
    await probe(
      "/api/v1/config",
      baseUrl
    );

  const jobs =
    await probe(
      "/api/v1/jobs",
      baseUrl
    );

  const previousState =
    previous?.state ??
    "UNKNOWN";

  const snapshot =
    buildSnapshot({
      previousState,
      config,
      jobs,
      backend: baseUrl
    });

  const files =
    saveSnapshot(
      snapshot,
      outputDir
    );

  return {
    snapshot,
    ...files
  };
}

async function main() {
  const {
    snapshot,
    statusFile,
    historyFile
  } =
    await observeOnce();

  console.log(
    "========================================"
  );

  console.log(
    " TERMiX AACP BACKEND OBSERVER v1.2"
  );

  console.log(
    " READ ONLY / GET ONLY"
  );

  console.log(
    "========================================"
  );

  console.log(
    `Backend        : ${snapshot.backend}`
  );

  console.log("");

  console.log(
    `Previous State : ${snapshot.previousState}`
  );

  console.log(
    `Current State  : ${snapshot.state}`
  );

  console.log(
    `Recovered      : ${
      snapshot.recovered
        ? "YES"
        : "NO"
    }`
  );

  console.log("");

  console.log(
    `CONFIG         : ${
      snapshot.probes.config.httpStatus ??
      "ERROR"
    }`
  );

  console.log(
    `JOBS           : ${
      snapshot.probes.jobs.httpStatus ??
      "ERROR"
    }`
  );

  console.log("");

  console.log(
    "POST           : NOT PERFORMED"
  );

  console.log(
    "WALLET         : NOT USED"
  );

  console.log(
    "SIGNING        : NOT PERFORMED"
  );

  console.log(
    "BROADCAST      : NOT PERFORMED"
  );

  console.log(
    "SUBMISSION     : NOT PERFORMED"
  );

  console.log("");

  console.log(
    `STATUS_FILE    : ${statusFile}`
  );

  console.log(
    `HISTORY_FILE   : ${historyFile}`
  );

  console.log(
    "========================================"
  );
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) ===
    path.resolve(new URL(import.meta.url).pathname)
) {
  main().catch(
    error => {
      console.error(
        `OBSERVER_FAILED=${error.message}`
      );

      process.exit(1);
    }
  );
}
