import fs from "node:fs";
import path from "node:path";

const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT || "provider-output/aacp-observer";

const LIFECYCLE_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-lifecycle.json"
);

const WATCH_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch.json"
);

const VERSION = "1.0.0";

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const SAFETY = {
  executionAuthorized: false,
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false,
};

function readJson(file) {
  try {
    if (!fs.existsSync(file)) {
      return {
        exists: false,
        valid: false,
        data: null,
      };
    }

    const raw = fs.readFileSync(file, "utf8");
    const data = JSON.parse(raw);

    return {
      exists: true,
      valid: true,
      data,
    };
  } catch {
    return {
      exists: true,
      valid: false,
      data: null,
    };
  }
}

function normalizeState(lifecycle) {
  const state = lifecycle?.lifecycle;

  if (!ALLOWED_STATES.has(state)) {
    return "BLOCKED";
  }

  return state;
}

function verifySafety(lifecycle) {
  if (!lifecycle || typeof lifecycle !== "object") {
    return false;
  }

  if (lifecycle.mode !== "READ_ONLY") {
    return false;
  }

  if (lifecycle.executionAuthorized !== false) {
    return false;
  }

  const safety = lifecycle.safety || {};
  const sideEffects = lifecycle.sideEffects || {};

  const unsafeValues = [
    safety.executionAuthorized,
    safety.postPerformed,
    safety.walletUsed,
    safety.signingPerformed,
    safety.broadcastPerformed,
    safety.submissionPerformed,
    sideEffects.postPerformed,
    sideEffects.walletUsed,
    sideEffects.signingPerformed,
    sideEffects.broadcastPerformed,
    sideEffects.submissionPerformed,
  ];

  return unsafeValues.every((value) => value !== true);
}

function loadPrevious() {
  const result = readJson(WATCH_FILE);

  if (!result.exists || !result.valid) {
    return null;
  }

  return result.data;
}

function buildWatch(lifecycleResult, previous) {
  const lifecycle = lifecycleResult.data;

  const state = normalizeState(lifecycle);
  const safe = verifySafety(lifecycle);

  const previousState = previous?.state ?? null;
  const changed = previousState !== state;

  const watchState = safe ? state : "BLOCKED";

  return {
    version: VERSION,
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",

    state: watchState,
    previousState,
    changed,

    lifecycle: {
      exists: lifecycleResult.exists,
      valid: lifecycleResult.valid,
      sourceState: state,
      reason: lifecycle?.reason || "Lifecycle report unavailable.",
    },

    safety: {
      executionAuthorized: false,
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false,
    },

    sideEffects: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false,
    },

    executionAuthorized: false,
  };
}

function writeWatch(report) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  fs.writeFileSync(
    WATCH_FILE,
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8"
  );
}

function main() {
  const lifecycle = readJson(LIFECYCLE_FILE);
  const previous = loadPrevious();

  const report = buildWatch(lifecycle, previous);

  writeWatch(report);

  console.log("TERMiX AACP PROVIDER WATCH v1.0");
  console.log("READ ONLY / FAIL CLOSED");
  console.log(`STATE=${report.state}`);
  console.log(`PREVIOUS=${report.previousState || "NONE"}`);
  console.log(`CHANGED=${report.changed}`);
  console.log(`SOURCE=${report.lifecycle.sourceState}`);
  console.log(`EXECUTION_AUTHORIZED=false`);
  console.log(`POST=NOT_PERFORMED`);
  console.log(`WALLET=NOT_USED`);
  console.log(`SIGNING=NOT_PERFORMED`);
  console.log(`BROADCAST=NOT_PERFORMED`);
  console.log(`SUBMISSION=NOT_PERFORMED`);
  console.log(`REPORT=${WATCH_FILE}`);
}

main();
