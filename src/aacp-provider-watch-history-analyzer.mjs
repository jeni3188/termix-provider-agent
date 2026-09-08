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

const ANALYSIS_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-analysis.json"
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

const UNSAFE_FIELDS = [
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
    .map((field) => `${field}=${String(fingerprint?.[field])}`)
    .join("|");
}

function isSafeEvent(event) {
  if (!event || typeof event !== "object") {
    return false;
  }

  if (event.executionAuthorized !== false) {
    return false;
  }

  if (event.fingerprint?.mode !== "READ_ONLY") {
    return false;
  }

  if (event.fingerprint?.executionAuthorized !== false) {
    return false;
  }

  const safety = event.safety || {};
  const sideEffects = event.sideEffects || {};

  const values = [
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

  return values.every((value) => value !== true);
}

function normalizeState(event) {
  if (
    event &&
    typeof event.state === "string" &&
    ALLOWED_STATES.has(event.state)
  ) {
    return event.state;
  }

  return "BLOCKED";
}

function analyzeHistory(historyResult) {
  if (!historyResult.exists) {
    return {
      state: "INCOMPLETE",
      reason: "Watch history file unavailable.",
      errors: ["HISTORY_MISSING"],
      anomalies: [],
      events: 0,
      transitions: 0,
      unsafeEvents: 0,
      changedEvents: 0,
      uniqueStates: [],
      firstEventAt: null,
      lastEventAt: null,
      historySha256: null,
    };
  }

  if (!historyResult.valid) {
    return {
      state: "BLOCKED",
      reason: "Watch history JSON is invalid.",
      errors: ["HISTORY_INVALID_JSON"],
      anomalies: [],
      events: 0,
      transitions: 0,
      unsafeEvents: 0,
      changedEvents: 0,
      uniqueStates: [],
      firstEventAt: null,
      lastEventAt: null,
      historySha256: null,
    };
  }

  const history = historyResult.data;

  if (
    !history ||
    typeof history !== "object" ||
    !Array.isArray(history.events)
  ) {
    return {
      state: "BLOCKED",
      reason: "Watch history structure is invalid.",
      errors: ["HISTORY_STRUCTURE_INVALID"],
      anomalies: [],
      events: 0,
      transitions: 0,
      unsafeEvents: 0,
      changedEvents: 0,
      uniqueStates: [],
      firstEventAt: null,
      lastEventAt: null,
      historySha256: sha256(historyResult.raw),
    };
  }

  if (history.events.length === 0) {
    return {
      state: "INCOMPLETE",
      reason: "Watch history contains no events.",
      errors: ["NO_EVENTS"],
      anomalies: [],
      events: 0,
      transitions: 0,
      unsafeEvents: 0,
      changedEvents: 0,
      uniqueStates: [],
      firstEventAt: null,
      lastEventAt: null,
      historySha256: sha256(historyResult.raw),
    };
  }

  const errors = [];
  const anomalies = [];
  const states = new Set();

  let transitions = 0;
  let unsafeEvents = 0;
  let changedEvents = 0;
  let previousState = null;
  let previousFingerprint = null;
  let previousTimestamp = null;

  for (let index = 0; index < history.events.length; index += 1) {
    const event = history.events[index];
    const state = normalizeState(event);

    states.add(state);

    if (!event || typeof event !== "object") {
      errors.push(`EVENT_${index}:INVALID_EVENT`);
      continue;
    }

    if (!ALLOWED_STATES.has(event.state)) {
      errors.push(`EVENT_${index}:INVALID_STATE`);
    }

    if (
      typeof event.generatedAt !== "string" ||
      Number.isNaN(Date.parse(event.generatedAt))
    ) {
      errors.push(`EVENT_${index}:INVALID_TIMESTAMP`);
    }

    if (!isSafeEvent(event)) {
      unsafeEvents += 1;

      anomalies.push({
        type: "UNSAFE_EVENT",
        index,
        eventId:
          typeof event.id === "string"
            ? event.id
            : null,
      });
    }

    if (event.changed === true) {
      changedEvents += 1;
    }

    if (
      previousState !== null &&
      state !== previousState
    ) {
      transitions += 1;

      anomalies.push({
        type: "STATE_TRANSITION",
        index,
        eventId: event.id || null,
        from: previousState,
        to: state,
      });
    }

    const fingerprint = event.fingerprint;

    if (
      fingerprint &&
      typeof fingerprint === "object"
    ) {
      const currentKey = fingerprintKey(fingerprint);

      if (
        previousFingerprint !== null &&
        currentKey !== previousFingerprint &&
        event.changed !== true
      ) {
        anomalies.push({
          type: "FINGERPRINT_CHANGE_WITHOUT_CHANGED_FLAG",
          index,
          eventId: event.id || null,
        });
      }

      previousFingerprint = currentKey;
    } else {
      errors.push(`EVENT_${index}:MISSING_FINGERPRINT`);
    }

    if (
      typeof event.generatedAt === "string"
    ) {
      const timestamp = Date.parse(
        event.generatedAt
      );

      if (!Number.isNaN(timestamp)) {
        if (
          previousTimestamp !== null &&
          timestamp < previousTimestamp
        ) {
          errors.push(
            `EVENT_${index}:CHRONOLOGY_ERROR`
          );
        }

        previousTimestamp = timestamp;
      }
    }

    previousState = state;
  }

  if (unsafeEvents > 0) {
    return {
      state: "BLOCKED",
      reason: "Unsafe event detected in watch history.",
      errors,
      anomalies,
      events: history.events.length,
      transitions,
      unsafeEvents,
      changedEvents,
      uniqueStates: [...states],
      firstEventAt:
        history.events[0]?.generatedAt || null,
      lastEventAt:
        history.events[history.events.length - 1]
          ?.generatedAt || null,
      historySha256: sha256(historyResult.raw),
    };
  }

  if (errors.length > 0) {
    return {
      state: "BLOCKED",
      reason: "Watch history anomaly analysis failed integrity checks.",
      errors,
      anomalies,
      events: history.events.length,
      transitions,
      unsafeEvents,
      changedEvents,
      uniqueStates: [...states],
      firstEventAt:
        history.events[0]?.generatedAt || null,
      lastEventAt:
        history.events[history.events.length - 1]
          ?.generatedAt || null,
      historySha256: sha256(historyResult.raw),
    };
  }

  return {
    state: "VERIFIED_READ_ONLY",
    reason:
      anomalies.length > 0
        ? "Watch history is structurally safe; observable changes were detected."
        : "Watch history is structurally safe; no anomalies detected.",
    errors: [],
    anomalies,
    events: history.events.length,
    transitions,
    unsafeEvents,
    changedEvents,
    uniqueStates: [...states],
    firstEventAt:
      history.events[0]?.generatedAt || null,
    lastEventAt:
      history.events[history.events.length - 1]
        ?.generatedAt || null,
    historySha256: sha256(historyResult.raw),
  };
}

function writeReport(report) {
  fs.mkdirSync(OUTPUT_DIR, {
    recursive: true,
  });

  fs.writeFileSync(
    ANALYSIS_FILE,
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8"
  );
}

function main() {
  const history = readJson(HISTORY_FILE);
  const verification = readJson(VERIFY_FILE);

  const analysis = analyzeHistory(history);

  const report = {
    version: VERSION,
    generatedAt: new Date().toISOString(),

    mode: "READ_ONLY",
    state: analysis.state,

    source: {
      historyExists: history.exists,
      historyValid: history.valid,
      historySha256: analysis.historySha256,
      verifierExists: verification.exists,
      verifierValid: verification.valid,
    },

    analysis: {
      reason: analysis.reason,
      events: analysis.events,
      transitions: analysis.transitions,
      changedEvents: analysis.changedEvents,
      unsafeEvents: analysis.unsafeEvents,
      uniqueStates: analysis.uniqueStates,
      firstEventAt: analysis.firstEventAt,
      lastEventAt: analysis.lastEventAt,
      anomalies: analysis.anomalies,
      errors: analysis.errors,
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
    "TERMiX AACP PROVIDER WATCH HISTORY ANALYZER v1.0"
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log(`STATE=${report.state}`);
  console.log(`EVENTS=${report.analysis.events}`);
  console.log(
    `TRANSITIONS=${report.analysis.transitions}`
  );
  console.log(
    `CHANGED_EVENTS=${report.analysis.changedEvents}`
  );
  console.log(
    `UNSAFE_EVENTS=${report.analysis.unsafeEvents}`
  );
  console.log(
    `ANOMALIES=${report.analysis.anomalies.length}`
  );
  console.log(
    `HISTORY_SHA256=${report.source.historySha256 || "NONE"}`
  );
  console.log(`EXECUTION_AUTHORIZED=false`);
  console.log(`POST=NOT_PERFORMED`);
  console.log(`WALLET=NOT_USED`);
  console.log(`SIGNING=NOT_PERFORMED`);
  console.log(`BROADCAST=NOT_PERFORMED`);
  console.log(`SUBMISSION=NOT_PERFORMED`);
  console.log(`REPORT=${ANALYSIS_FILE}`);
}

main();
