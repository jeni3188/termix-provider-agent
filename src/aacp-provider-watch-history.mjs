import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT || "provider-output/aacp-observer";

const WATCH_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch.json"
);

const HISTORY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history.json"
);

const VERSION = "1.0.0";
const MAX_EVENTS = 100;

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
        raw: null,
      };
    }

    const raw = fs.readFileSync(file, "utf8");
    const data = JSON.parse(raw);

    return {
      exists: true,
      valid: true,
      data,
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

function safeWatch(data) {
  if (!data || typeof data !== "object") {
    return false;
  }

  if (data.mode !== "READ_ONLY") {
    return false;
  }

  if (data.executionAuthorized !== false) {
    return false;
  }

  const safety = data.safety || {};
  const sideEffects = data.sideEffects || {};

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

function normalizeState(data) {
  if (!data || typeof data !== "object") {
    return "INCOMPLETE";
  }

  const allowed = new Set([
    "BACKEND_UNAVAILABLE",
    "INCOMPLETE",
    "BLOCKED",
    "READY_READ_ONLY",
    "VERIFIED_READ_ONLY",
  ]);

  return allowed.has(data.state)
    ? data.state
    : "BLOCKED";
}

function loadHistory() {
  const result = readJson(HISTORY_FILE);

  if (!result.exists || !result.valid) {
    return {
      version: VERSION,
      events: [],
    };
  }

  if (
    !result.data ||
    !Array.isArray(result.data.events)
  ) {
    return {
      version: VERSION,
      events: [],
    };
  }

  return result.data;
}

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

function buildFingerprint(data) {
  const fingerprint = {
    state: normalizeState(data),
    sourceState:
      data?.lifecycle?.sourceState || "UNKNOWN",
    mode: data?.mode || "UNKNOWN",
    executionAuthorized:
      data?.executionAuthorized === true,
    postPerformed:
      data?.safety?.postPerformed === true ||
      data?.sideEffects?.postPerformed === true,
    walletUsed:
      data?.safety?.walletUsed === true ||
      data?.sideEffects?.walletUsed === true,
    signingPerformed:
      data?.safety?.signingPerformed === true ||
      data?.sideEffects?.signingPerformed === true,
    broadcastPerformed:
      data?.safety?.broadcastPerformed === true ||
      data?.sideEffects?.broadcastPerformed === true,
    submissionPerformed:
      data?.safety?.submissionPerformed === true ||
      data?.sideEffects?.submissionPerformed === true,
  };

  return fingerprint;
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

function diffFingerprint(previous, current) {
  if (!previous) {
    return {
      changed: true,
      fields: ["INITIAL_SNAPSHOT"],
    };
  }

  const fields = [];

  for (const key of FINGERPRINT_FIELDS) {
    if (
      previous[key] !== current[key]
    ) {
      fields.push(key);
    }
  }

  return {
    changed:
      fingerprintKey(previous) !==
      fingerprintKey(current),
    fields,
  };
}

function buildEvent(watchResult, history) {
  const watch = watchResult.data;
  const current = buildFingerprint(watch);

  const previousEvent =
    history.events.length > 0
      ? history.events[history.events.length - 1]
      : null;

  const previous =
    previousEvent?.fingerprint || null;

  const diff = diffFingerprint(previous, current);

  const safe = safeWatch(watch);

  const state =
    safe
      ? current.state
      : "BLOCKED";

  return {
    id: crypto.randomUUID(),
    generatedAt: new Date().toISOString(),
    state,
    changed: diff.changed,
    changedFields: diff.fields,

    watch: {
      exists: watchResult.exists,
      valid: watchResult.valid,
      sha256: watchResult.raw
        ? sha256(watchResult.raw)
        : null,
    },

    fingerprint: {
      ...current,
      mode: "READ_ONLY",
      executionAuthorized: false,
    },

    safety: {
      ...SAFETY,
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

function writeHistory(history) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  fs.writeFileSync(
    HISTORY_FILE,
    `${JSON.stringify(history, null, 2)}\n`,
    "utf8"
  );
}

function main() {
  const watch = readJson(WATCH_FILE);
  const history = loadHistory();

  const event = buildEvent(watch, history);

  history.version = VERSION;
  history.mode = "READ_ONLY";
  history.events.push(event);

  if (history.events.length > MAX_EVENTS) {
    history.events = history.events.slice(
      history.events.length - MAX_EVENTS
    );
  }

  writeHistory(history);

  console.log(
    "TERMiX AACP PROVIDER WATCH HISTORY v1.0"
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log(`STATE=${event.state}`);
  console.log(`CHANGED=${event.changed}`);
  console.log(
    `FIELDS=${event.changedFields.join(",") || "NONE"}`
  );
  console.log(
    `WATCH_SHA256=${event.watch.sha256 || "NONE"}`
  );
  console.log(`EVENTS=${history.events.length}`);
  console.log(`EXECUTION_AUTHORIZED=false`);
  console.log(`POST=NOT_PERFORMED`);
  console.log(`WALLET=NOT_USED`);
  console.log(`SIGNING=NOT_PERFORMED`);
  console.log(`BROADCAST=NOT_PERFORMED`);
  console.log(`SUBMISSION=NOT_PERFORMED`);
  console.log(`REPORT=${HISTORY_FILE}`);
}

main();
