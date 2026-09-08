import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";
const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  path.resolve("provider-output/aacp-observer");

const HISTORY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history.json",
);

const HISTORY_VERIFY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-verify.json",
);

const ANALYSIS_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-analysis.json",
);

const ANALYSIS_VERIFY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-analysis-verify.json",
);

const CHAIN_VERIFY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-chain-verify.json",
);

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-integrity-audit.json",
);

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const UNSAFE_FIELDS = [
  "executionAuthorized",
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
];

const SIDE_EFFECT_FIELDS = [
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
];

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isSha256(value) {
  return typeof value === "string" && /^[a-f0-9]{64}$/i.test(value);
}

function isTimestamp(value) {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function sha256Buffer(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

function sha256File(file) {
  return sha256Buffer(fs.readFileSync(file));
}

function readJson(file) {
  if (!fs.existsSync(file)) {
    return {
      exists: false,
      value: null,
      sha256: null,
      error: null,
    };
  }

  try {
    const raw = fs.readFileSync(file);
    return {
      exists: true,
      value: JSON.parse(raw.toString("utf8")),
      sha256: sha256Buffer(raw),
      error: null,
    };
  } catch (error) {
    return {
      exists: true,
      value: null,
      sha256: null,
      error: String(error?.message || error),
    };
  }
}

function safetyFlagsSafe(value) {
  if (!isObject(value)) return false;

  return UNSAFE_FIELDS.every(
    (field) => value[field] === false,
  );
}

function sideEffectsSafe(value) {
  if (!isObject(value)) return false;

  return SIDE_EFFECT_FIELDS.every(
    (field) => value[field] === false,
  );
}

function eventSafetySafe(event) {
  if (!isObject(event)) return false;

  if (event.executionAuthorized !== false) {
    return false;
  }

  if (
    !isObject(event.fingerprint) ||
    event.fingerprint.mode !== "READ_ONLY" ||
    event.fingerprint.executionAuthorized !== false
  ) {
    return false;
  }

  return SIDE_EFFECT_FIELDS.every(
    (field) => event.fingerprint[field] === false,
  );
}

function fingerprintKey(event) {
  if (!isObject(event) || !isObject(event.fingerprint)) {
    return null;
  }

  const fields = [
    "state",
    "sourceState",
    "mode",
    "executionAuthorized",
    ...SIDE_EFFECT_FIELDS,
  ];

  const result = {};

  for (const field of fields) {
    result[field] = event.fingerprint[field];
  }

  return JSON.stringify(result);
}

function normalizeState(value) {
  return typeof value === "string" && ALLOWED_STATES.has(value)
    ? value
    : null;
}

function extractState(value) {
  if (!isObject(value)) return null;

  return normalizeState(value.state) ||
    normalizeState(value.sourceState) ||
    normalizeState(value.lifecycleState) ||
    null;
}

function collectHashCandidates(value) {
  if (!isObject(value)) return [];

  const candidates = [];

  const keys = [
    "historySha256",
    "analysisSha256",
    "chainSha256",
    "sha256",
  ];

  for (const key of keys) {
    if (isSha256(value[key])) {
      candidates.push({
        key,
        value: value[key],
      });
    }
  }

  for (const containerKey of [
    "source",
    "history",
    "analysis",
    "chain",
    "verification",
  ]) {
    const nested = value[containerKey];

    if (!isObject(nested)) continue;

    for (const key of keys) {
      if (isSha256(nested[key])) {
        candidates.push({
          key: `${containerKey}.${key}`,
          value: nested[key],
        });
      }
    }
  }

  return candidates;
}

function verifyHistory(history, errors, findings) {
  if (!history.exists) {
    errors.push("history_missing");
    return null;
  }

  if (history.error) {
    errors.push(`history_invalid_json:${history.error}`);
    return null;
  }

  if (!isObject(history.value)) {
    errors.push("history_invalid_root");
    return null;
  }

  const events = history.value.events;

  if (!Array.isArray(events)) {
    errors.push("history_events_missing");
    return null;
  }

  if (events.length === 0) {
    errors.push("history_empty");
    return null;
  }

  let previousTimestamp = null;
  let previousFingerprint = null;
  const ids = new Set();

  for (let index = 0; index < events.length; index += 1) {
    const event = events[index];

    if (!isObject(event)) {
      errors.push(`event_${index}_invalid`);
      continue;
    }

    if (typeof event.eventId !== "string" || !event.eventId) {
      errors.push(`event_${index}_missing_id`);
    } else if (ids.has(event.eventId)) {
      errors.push(`event_${index}_duplicate_id`);
    } else {
      ids.add(event.eventId);
    }

    if (!isTimestamp(event.generatedAt)) {
      errors.push(`event_${index}_invalid_timestamp`);
    } else {
      const timestamp = Date.parse(event.generatedAt);

      if (
        previousTimestamp !== null &&
        timestamp < previousTimestamp
      ) {
        errors.push(`event_${index}_chronology_error`);
      }

      previousTimestamp = timestamp;
    }

    const state = normalizeState(event.state);

    if (!state) {
      errors.push(`event_${index}_invalid_state`);
    }

    if (!eventSafetySafe(event)) {
      errors.push(`event_${index}_unsafe`);
    }

    const fingerprint = fingerprintKey(event);

    if (!fingerprint) {
      errors.push(`event_${index}_missing_fingerprint`);
    } else if (
      previousFingerprint !== null &&
      fingerprint !== previousFingerprint
    ) {
      findings.push({
        type: "FINGERPRINT_TRANSITION",
        eventId: event.eventId,
        index,
      });
    }

    if (event.changed === true) {
      findings.push({
        type: "DECLARED_CHANGE",
        eventId: event.eventId,
        index,
        changedFields: Array.isArray(event.changedFields)
          ? event.changedFields
          : [],
      });
    }

    previousFingerprint = fingerprint;
  }

  return events;
}

function verifyCompanionReports(
  history,
  historyVerify,
  analysis,
  analysisVerify,
  chainVerify,
  errors,
  findings,
) {
  const reports = [
    ["history_verify", historyVerify],
    ["analysis", analysis],
    ["analysis_verify", analysisVerify],
    ["chain_verify", chainVerify],
  ];

  for (const [name, report] of reports) {
    if (!report.exists) {
      errors.push(`${name}_missing`);
      continue;
    }

    if (report.error) {
      errors.push(`${name}_invalid_json:${report.error}`);
      continue;
    }

    if (!isObject(report.value)) {
      errors.push(`${name}_invalid_root`);
      continue;
    }

    if (report.value.mode !== "READ_ONLY") {
      errors.push(`${name}_non_read_only`);
    }

    if (report.value.executionAuthorized !== false) {
      errors.push(`${name}_execution_authorized`);
    }

    if (
      report.value.safety &&
      !safetyFlagsSafe(report.value.safety)
    ) {
      errors.push(`${name}_unsafe_safety`);
    }

    if (
      report.value.sideEffects &&
      !sideEffectsSafe(report.value.sideEffects)
    ) {
      errors.push(`${name}_unsafe_side_effects`);
    }
  }

  const historyState = extractState(history.value);
  const historyVerifyState = extractState(historyVerify.value);
  const analysisState = extractState(analysis.value);
  const analysisVerifyState = extractState(analysisVerify.value);
  const chainState = extractState(chainVerify.value);

  const states = [
    ["history", historyState],
    ["history_verify", historyVerifyState],
    ["analysis", analysisState],
    ["analysis_verify", analysisVerifyState],
    ["chain_verify", chainState],
  ];

  for (const [name, state] of states) {
    if (!state) {
      errors.push(`${name}_state_missing_or_invalid`);
    }
  }

  const validStates = states
    .map(([, state]) => state)
    .filter(Boolean);

  if (
    validStates.length > 1 &&
    !validStates.every((state) => state === validStates[0])
  ) {
    errors.push("cross_layer_state_mismatch");
  }

  const historyCandidates = [
    ...collectHashCandidates(historyVerify.value),
    ...collectHashCandidates(analysis.value),
    ...collectHashCandidates(analysisVerify.value),
    ...collectHashCandidates(chainVerify.value),
  ];

  if (history.exists && history.sha256) {
    for (const candidate of historyCandidates) {
      if (
        candidate.key.toLowerCase().includes("history") &&
        candidate.value !== history.sha256
      ) {
        errors.push(
          `history_hash_mismatch:${candidate.key}`,
        );
      }
    }
  }

  if (analysis.exists && analysis.sha256) {
    const analysisVerifyCandidates =
      collectHashCandidates(analysisVerify.value);

    for (const candidate of analysisVerifyCandidates) {
      if (
        candidate.key.toLowerCase().includes("analysis") &&
        candidate.value !== analysis.sha256
      ) {
        errors.push(
          `analysis_hash_mismatch:${candidate.key}`,
        );
      }
    }
  }

  const historyEvents =
    isObject(history.value) &&
    Array.isArray(history.value.events)
      ? history.value.events
      : null;

  const historyVerifyEvents =
    isObject(historyVerify.value) &&
    historyVerify.value.history &&
    Number.isInteger(historyVerify.value.history.events)
      ? historyVerify.value.history.events
      : Number.isInteger(historyVerify.value.events)
        ? historyVerify.value.events
        : null;

  if (
    historyEvents &&
    historyVerifyEvents !== null &&
    historyEvents.length !== historyVerifyEvents
  ) {
    errors.push("history_event_count_mismatch");
  }

  if (
    isObject(analysis.value) &&
    isObject(analysis.value.analysis)
  ) {
    const metrics = analysis.value.analysis;

    if (
      Number.isInteger(metrics.events) &&
      historyEvents &&
      metrics.events !== historyEvents.length
    ) {
      errors.push("analysis_event_count_mismatch");
    }
  }

  findings.push({
    type: "CROSS_LAYER_STATE",
    state: validStates[0] || null,
  });
}

function buildAudit({
  state,
  errors,
  findings,
  history,
  historyVerify,
  analysis,
  analysisVerify,
  chainVerify,
  events,
}) {
  const uniqueFindingTypes = [
    ...new Set(findings.map((finding) => finding.type)),
  ];

  const integrityState =
    errors.length === 0
      ? "VERIFIED_READ_ONLY"
      : "BLOCKED";

  return {
    version: VERSION,
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state: integrityState,
    sourceState: state,
    executionAuthorized: false,

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

    source: {
      history: {
        exists: history.exists,
        sha256: history.sha256,
      },
      historyVerify: {
        exists: historyVerify.exists,
        sha256: historyVerify.sha256,
      },
      analysis: {
        exists: analysis.exists,
        sha256: analysis.sha256,
      },
      analysisVerify: {
        exists: analysisVerify.exists,
        sha256: analysisVerify.sha256,
      },
      chainVerify: {
        exists: chainVerify.exists,
        sha256: chainVerify.sha256,
      },
    },

    integrity: {
      historyExists: history.exists,
      historyEvents: Array.isArray(events)
        ? events.length
        : 0,
      errors: [...errors],
      errorCount: errors.length,
      findings,
      findingCount: findings.length,
      findingTypes: uniqueFindingTypes,
      integrityValid: errors.length === 0,
    },

    policy: {
      readOnly: true,
      failClosed: true,
      post: "NOT_PERFORMED",
      wallet: "NOT_USED",
      signing: "NOT_PERFORMED",
      broadcast: "NOT_PERFORMED",
      submission: "NOT_PERFORMED",
    },
  };
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(
    file,
    `${JSON.stringify(value, null, 2)}\n`,
    "utf8",
  );
}

function main() {
  console.log(
    "TERMiX AACP PROVIDER WATCH HISTORY INTEGRITY AUDITOR v1.0",
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log("POST=NOT_PERFORMED");
  console.log("WALLET=NOT_USED");
  console.log("SIGNING=NOT_PERFORMED");
  console.log("BROADCAST=NOT_PERFORMED");
  console.log("SUBMISSION=NOT_PERFORMED");

  const history = readJson(HISTORY_FILE);
  const historyVerify = readJson(HISTORY_VERIFY_FILE);
  const analysis = readJson(ANALYSIS_FILE);
  const analysisVerify = readJson(ANALYSIS_VERIFY_FILE);
  const chainVerify = readJson(CHAIN_VERIFY_FILE);

  const errors = [];
  const findings = [];

  const events = verifyHistory(
    history,
    errors,
    findings,
  );

  if (events) {
    verifyCompanionReports(
      history,
      historyVerify,
      analysis,
      analysisVerify,
      chainVerify,
      errors,
      findings,
    );
  }

  const sourceState =
    extractState(chainVerify.value) ||
    extractState(analysisVerify.value) ||
    extractState(analysis.value) ||
    extractState(historyVerify.value) ||
    extractState(history.value) ||
    null;

  const report = buildAudit({
    state: sourceState,
    errors,
    findings,
    history,
    historyVerify,
    analysis,
    analysisVerify,
    chainVerify,
    events,
  });

  writeJson(OUTPUT_FILE, report);

  console.log(`STATE=${report.state}`);
  console.log(`EVENTS=${report.integrity.historyEvents}`);
  console.log(`FINDINGS=${report.integrity.findingCount}`);
  console.log(`ERRORS=${report.integrity.errorCount}`);
  console.log("EXECUTION_AUTHORIZED=false");
  console.log(`REPORT=${OUTPUT_FILE}`);
}

main();
