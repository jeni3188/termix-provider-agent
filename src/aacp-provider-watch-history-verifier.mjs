import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  "provider-output/aacp-observer";

const HISTORY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history.json"
);

const VERIFY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-verify.json"
);

const VERSION = "1.0.0";

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const FINGERPRINT_FIELDS = [
  "state",
  "sourceState",
  "mode",
  "executionAuthorized",
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
];

function readJson(file) {
  try {
    if (!fs.existsSync(file)) {
      return {
        exists: false,
        valid: false,
        data: null,
        raw: null,
      };
    }

    const raw = fs.readFileSync(file, "utf8");

    return {
      exists: true,
      valid: true,
      data: JSON.parse(raw),
      raw,
    };
  } catch {
    return {
      exists: true,
      valid: false,
      data: null,
      raw: null,
    };
  }
}

function sha256(raw) {
  return crypto
    .createHash("sha256")
    .update(raw, "utf8")
    .digest("hex");
}

function fingerprintKey(fingerprint) {
  return FINGERPRINT_FIELDS
    .map((field) => [
      field,
      fingerprint[field],
    ])
    .map(([field, value]) =>
      `${field}=${String(value)}`
    )
    .join("|");
}

function validFingerprint(fingerprint) {
  if (
    !fingerprint ||
    typeof fingerprint !== "object"
  ) {
    return false;
  }

  for (const field of FINGERPRINT_FIELDS) {
    if (!(field in fingerprint)) {
      return false;
    }
  }

  if (!ALLOWED_STATES.has(fingerprint.state)) {
    return false;
  }

  if (typeof fingerprint.sourceState !== "string") {
    return false;
  }

  if (fingerprint.mode !== "READ_ONLY") {
    return false;
  }

  const booleanFields = [
    "executionAuthorized",
    "postPerformed",
    "walletUsed",
    "signingPerformed",
    "broadcastPerformed",
    "submissionPerformed",
  ];

  for (const field of booleanFields) {
    if (typeof fingerprint[field] !== "boolean") {
      return false;
    }

    if (fingerprint[field] === true) {
      return false;
    }
  }

  return true;
}

function validSafety(event) {
  if (!event || typeof event !== "object") {
    return false;
  }

  if (event.executionAuthorized !== false) {
    return false;
  }

  if (event.mode && event.mode !== "READ_ONLY") {
    return false;
  }

  const safety = event.safety || {};
  const sideEffects = event.sideEffects || {};

  const unsafe = [
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
    event.postPerformed,
    event.walletUsed,
    event.signingPerformed,
    event.broadcastPerformed,
    event.submissionPerformed,
  ];

  return unsafe.every((value) => value !== true);
}

function verifyEvent(event, index) {
  const errors = [];

  if (!event || typeof event !== "object") {
    errors.push("EVENT_NOT_OBJECT");
    return errors;
  }

  if (
    typeof event.id !== "string" ||
    event.id.length === 0
  ) {
    errors.push("INVALID_EVENT_ID");
  }

  if (
    typeof event.generatedAt !== "string" ||
    Number.isNaN(Date.parse(event.generatedAt))
  ) {
    errors.push("INVALID_GENERATED_AT");
  }

  if (!ALLOWED_STATES.has(event.state)) {
    errors.push("INVALID_STATE");
  }

  if (event.changed !== true && event.changed !== false) {
    errors.push("INVALID_CHANGED");
  }

  if (!Array.isArray(event.changedFields)) {
    errors.push("INVALID_CHANGED_FIELDS");
  }

  if (!validFingerprint(event.fingerprint)) {
    errors.push("INVALID_FINGERPRINT");
  }

  if (!validSafety(event)) {
    errors.push("UNSAFE_EVENT");
  }

  if (
    event.fingerprint &&
    event.fingerprint.state !== event.state
  ) {
    errors.push("STATE_FINGERPRINT_MISMATCH");
  }

  if (
    event.fingerprint &&
    event.fingerprint.mode !== "READ_ONLY"
  ) {
    errors.push("MODE_NOT_READ_ONLY");
  }

  if (
    event.fingerprint &&
    event.fingerprint.executionAuthorized !== false
  ) {
    errors.push("EXECUTION_AUTHORIZED");
  }

  return errors;
}

function verifyHistory(result) {
  if (!result.exists) {
    return {
      state: "INCOMPLETE",
      reason: "Watch history file unavailable.",
      errors: ["HISTORY_MISSING"],
      events: 0,
      fingerprintVerified: false,
      sha256: null,
    };
  }

  if (!result.valid) {
    return {
      state: "BLOCKED",
      reason: "Watch history JSON is invalid.",
      errors: ["HISTORY_INVALID_JSON"],
      events: 0,
      fingerprintVerified: false,
      sha256: null,
    };
  }

  const history = result.data;

  if (!history || typeof history !== "object") {
    return {
      state: "BLOCKED",
      reason: "Watch history root is invalid.",
      errors: ["HISTORY_ROOT_INVALID"],
      events: 0,
      fingerprintVerified: false,
      sha256: result.raw
        ? sha256(result.raw)
        : null,
    };
  }

  if (!Array.isArray(history.events)) {
    return {
      state: "BLOCKED",
      reason: "Watch history events is not an array.",
      errors: ["EVENTS_NOT_ARRAY"],
      events: 0,
      fingerprintVerified: false,
      sha256: result.raw
        ? sha256(result.raw)
        : null,
    };
  }

  if (history.events.length === 0) {
    return {
      state: "INCOMPLETE",
      reason: "Watch history contains no events.",
      errors: ["NO_EVENTS"],
      events: 0,
      fingerprintVerified: false,
      sha256: result.raw
        ? sha256(result.raw)
        : null,
    };
  }

  const errors = [];
  const ids = new Set();
  let previousTime = null;

  for (let i = 0; i < history.events.length; i += 1) {
    const event = history.events[i];

    errors.push(
      ...verifyEvent(event, i)
        .map((error) => `EVENT_${i}:${error}`)
    );

    if (
      event &&
      typeof event.id === "string"
    ) {
      if (ids.has(event.id)) {
        errors.push(
          `EVENT_${i}:DUPLICATE_EVENT_ID`
        );
      }

      ids.add(event.id);
    }

    if (
      event &&
      typeof event.generatedAt === "string"
    ) {
      const timestamp = Date.parse(
        event.generatedAt
      );

      if (!Number.isNaN(timestamp)) {
        if (
          previousTime !== null &&
          timestamp < previousTime
        ) {
          errors.push(
            `EVENT_${i}:CHRONOLOGY_ERROR`
          );
        }

        previousTime = timestamp;
      }
    }
  }

  const fingerprintVerified =
    errors.filter((error) =>
      error.includes("INVALID_FINGERPRINT") ||
      error.includes("FINGERPRINT_MISMATCH")
    ).length === 0;

  if (errors.length > 0) {
    return {
      state: "BLOCKED",
      reason: "Watch history integrity verification failed.",
      errors,
      events: history.events.length,
      fingerprintVerified,
      sha256: result.raw
        ? sha256(result.raw)
        : null,
    };
  }

  return {
    state: "VERIFIED_READ_ONLY",
    reason: "Watch history integrity verified.",
    errors: [],
    events: history.events.length,
    fingerprintVerified: true,
    sha256: result.raw
      ? sha256(result.raw)
      : null,
  };
}

function writeReport(report) {
  fs.mkdirSync(OUTPUT_DIR, {
    recursive: true,
  });

  fs.writeFileSync(
    VERIFY_FILE,
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8"
  );
}

function main() {
  const history = readJson(HISTORY_FILE);
  const verification = verifyHistory(history);

  const report = {
    version: VERSION,
    generatedAt: new Date().toISOString(),

    mode: "READ_ONLY",
    state: verification.state,

    history: {
      exists: history.exists,
      valid: history.valid,
      events: verification.events,
      sha256: verification.sha256,
    },

    integrity: {
      verified:
        verification.state ===
        "VERIFIED_READ_ONLY",
      fingerprintVerified:
        verification.fingerprintVerified,
      errors: verification.errors,
      reason: verification.reason,
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

  writeReport(report);

  console.log(
    "TERMiX AACP PROVIDER WATCH HISTORY VERIFIER v1.0"
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log(`STATE=${report.state}`);
  console.log(
    `INTEGRITY_VERIFIED=${report.integrity.verified}`
  );
  console.log(
    `FINGERPRINT_VERIFIED=${report.integrity.fingerprintVerified}`
  );
  console.log(`EVENTS=${report.history.events}`);
  console.log(
    `HISTORY_SHA256=${report.history.sha256 || "NONE"}`
  );
  console.log(
    `ERRORS=${report.integrity.errors.length}`
  );
  console.log(`EXECUTION_AUTHORIZED=false`);
  console.log(`POST=NOT_PERFORMED`);
  console.log(`WALLET=NOT_USED`);
  console.log(`SIGNING=NOT_PERFORMED`);
  console.log(`BROADCAST=NOT_PERFORMED`);
  console.log(`SUBMISSION=NOT_PERFORMED`);
  console.log(`REPORT=${VERIFY_FILE}`);
}

main();
