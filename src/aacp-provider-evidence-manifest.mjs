import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";

const OUTPUT_DIR =
  process.env.AACP_PROVIDER_OUTPUT_DIR ||
  path.resolve("provider-output/aacp-observer");

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-evidence-manifest.json"
);

const FILES = [
  {
    key: "history",
    file: "latest-provider-watch-history.json",
  },
  {
    key: "historyVerify",
    file: "latest-provider-watch-history-verify.json",
  },
  {
    key: "historyAnalysis",
    file: "latest-provider-watch-history-analysis.json",
  },
  {
    key: "historyAnalysisVerify",
    file: "latest-provider-watch-history-analysis-verify.json",
  },
  {
    key: "historyChainVerify",
    file: "latest-provider-watch-history-chain-verify.json",
  },
  {
    key: "historyIntegrityAudit",
    file: "latest-provider-watch-history-integrity-audit.json",
  },
  {
    key: "historyIntegrityAuditVerify",
    file: "latest-provider-watch-history-integrity-audit-verify.json",
  },
];

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const SAFETY_FIELDS = [
  "executionAuthorized",
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
];

const POLICY = {
  readOnly: true,
  failClosed: true,
  post: "NOT_PERFORMED",
  wallet: "NOT_USED",
  signing: "NOT_PERFORMED",
  broadcast: "NOT_PERFORMED",
  submission: "NOT_PERFORMED",
};

function sha256File(file) {
  const hash = crypto.createHash("sha256");
  const stream = fs.createReadStream(file);

  return new Promise((resolve, reject) => {
    stream.on("data", (chunk) => hash.update(chunk));
    stream.on("error", reject);
    stream.on("end", () => resolve(hash.digest("hex")));
  });
}

function isSha256(value) {
  return typeof value === "string" && /^[a-f0-9]{64}$/i.test(value);
}

function isTimestamp(value) {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function safeBoolean(value) {
  return value === false;
}

function safetyObjectSafe(report) {
  if (!report || typeof report !== "object") {
    return false;
  }

  if (report.executionAuthorized !== false) {
    return false;
  }

  if (report.mode !== "READ_ONLY") {
    return false;
  }

  if (!report.safety || typeof report.safety !== "object") {
    return false;
  }

  if (!report.sideEffects || typeof report.sideEffects !== "object") {
    return false;
  }

  for (const field of SAFETY_FIELDS) {
    const container =
      field === "executionAuthorized"
        ? report
        : field === "postPerformed" ||
            field === "walletUsed" ||
            field === "signingPerformed" ||
            field === "broadcastPerformed" ||
            field === "submissionPerformed"
          ? report.safety
          : report.safety;

    if (field !== "executionAuthorized" && container[field] === true) {
      return false;
    }
  }

  for (const field of [
    "postPerformed",
    "walletUsed",
    "signingPerformed",
    "broadcastPerformed",
    "submissionPerformed",
  ]) {
    if (report.safety[field] !== false) {
      return false;
    }
  }

  if (
    report.sideEffects.postPerformed !== false ||
    report.sideEffects.walletUsed !== false ||
    report.sideEffects.signingPerformed !== false ||
    report.sideEffects.broadcastPerformed !== false ||
    report.sideEffects.submissionPerformed !== false
  ) {
    return false;
  }

  return true;
}

function collectState(report) {
  if (!report || typeof report !== "object") {
    return null;
  }

  if (ALLOWED_STATES.has(report.state)) {
    return report.state;
  }

  if (ALLOWED_STATES.has(report.sourceState)) {
    return report.sourceState;
  }

  return null;
}

async function inspectFile(entry) {
  const file = path.join(OUTPUT_DIR, entry.file);

  if (!fs.existsSync(file)) {
    return {
      key: entry.key,
      file: entry.file,
      exists: false,
      sizeBytes: null,
      sha256: null,
    };
  }

  const stat = fs.statSync(file);
  const sha256 = await sha256File(file);

  return {
    key: entry.key,
    file: entry.file,
    exists: true,
    sizeBytes: stat.size,
    sha256,
  };
}

function buildManifestState(states, errors) {
  if (errors.length > 0) {
    return "BLOCKED";
  }

  const values = Object.values(states).filter(Boolean);

  if (values.length === 0) {
    return "INCOMPLETE";
  }

  if (values.some((state) => state === "BLOCKED")) {
    return "BLOCKED";
  }

  if (values.includes("INCOMPLETE")) {
    return "INCOMPLETE";
  }

  if (values.every((state) => state === "VERIFIED_READ_ONLY")) {
    return "VERIFIED_READ_ONLY";
  }

  if (values.some((state) => state === "READY_READ_ONLY")) {
    return "READY_READ_ONLY";
  }

  if (values.some((state) => state === "BACKEND_UNAVAILABLE")) {
    return "BACKEND_UNAVAILABLE";
  }

  return "INCOMPLETE";
}

async function main() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const generatedAt = new Date().toISOString();

  const files = [];
  const errors = [];
  const states = {};
  const reports = {};

  for (const entry of FILES) {
    const file = path.join(OUTPUT_DIR, entry.file);

    if (!fs.existsSync(file)) {
      files.push({
        key: entry.key,
        file: entry.file,
        exists: false,
        sizeBytes: null,
        sha256: null,
      });
      continue;
    }

    const stat = fs.statSync(file);
    const sha256 = await sha256File(file);

    files.push({
      key: entry.key,
      file: entry.file,
      exists: true,
      sizeBytes: stat.size,
      sha256,
    });

    try {
      reports[entry.key] = readJson(file);
    } catch {
      errors.push(`INVALID_JSON:${entry.file}`);
    }
  }

  /*
   * Phase 12 raw history is NOT a normal provider report.
   * Validate its own schema and safety invariants separately.
   */
  const history = reports.history;

  if (history) {
    if (
      typeof history !== "object" ||
      Array.isArray(history) ||
      history.mode !== "READ_ONLY" ||
      !Array.isArray(history.events)
    ) {
      errors.push("INVALID_HISTORY_STRUCTURE");
    } else {
      let previousTimestamp = null;

      for (const [index, event] of history.events.entries()) {
        if (!event || typeof event !== "object") {
          errors.push(`INVALID_HISTORY_EVENT:${index}`);
          continue;
        }

        if (
          typeof event.id !== "string" ||
          event.id.length === 0
        ) {
          errors.push(`INVALID_HISTORY_EVENT_ID:${index}`);
        }

        if (!isTimestamp(event.generatedAt)) {
          errors.push(`INVALID_HISTORY_TIMESTAMP:${index}`);
        }

        if (!ALLOWED_STATES.has(event.state)) {
          errors.push(`INVALID_HISTORY_STATE:${index}`);
        }

        if (event.executionAuthorized !== false) {
          errors.push(`UNSAFE_HISTORY_EVENT:${index}`);
        }

        if (
          !event.fingerprint ||
          typeof event.fingerprint !== "object" ||
          event.fingerprint.mode !== "READ_ONLY" ||
          event.fingerprint.executionAuthorized !== false ||
          event.fingerprint.postPerformed !== false ||
          event.fingerprint.walletUsed !== false ||
          event.fingerprint.signingPerformed !== false ||
          event.fingerprint.broadcastPerformed !== false ||
          event.fingerprint.submissionPerformed !== false
        ) {
          errors.push(`UNSAFE_HISTORY_FINGERPRINT:${index}`);
        }

        if (
          !event.safety ||
          event.safety.executionAuthorized !== false ||
          event.safety.postPerformed !== false ||
          event.safety.walletUsed !== false ||
          event.safety.signingPerformed !== false ||
          event.safety.broadcastPerformed !== false ||
          event.safety.submissionPerformed !== false
        ) {
          errors.push(`UNSAFE_HISTORY_SAFETY:${index}`);
        }

        if (
          !event.sideEffects ||
          event.sideEffects.postPerformed !== false ||
          event.sideEffects.walletUsed !== false ||
          event.sideEffects.signingPerformed !== false ||
          event.sideEffects.broadcastPerformed !== false ||
          event.sideEffects.submissionPerformed !== false
        ) {
          errors.push(`UNSAFE_HISTORY_SIDE_EFFECTS:${index}`);
        }

        if (previousTimestamp && isTimestamp(event.generatedAt)) {
          if (
            Date.parse(event.generatedAt) <
            Date.parse(previousTimestamp)
          ) {
            errors.push(`INVALID_HISTORY_CHRONOLOGY:${index}`);
          }
        }

        if (isTimestamp(event.generatedAt)) {
          previousTimestamp = event.generatedAt;
        }
      }

      if (history.events.length === 0) {
        errors.push("EMPTY_HISTORY");
      } else {
        const historyStates = history.events
          .map((event) => event?.state)
          .filter((state) => ALLOWED_STATES.has(state));

        const latestState =
          historyStates[historyStates.length - 1];

        if (latestState) {
          states.history = latestState;
        }
      }
    }
  }

  /*
   * All other Phase 13–18 artifacts are provider reports.
   */
  for (const entry of FILES.slice(1)) {
    const report = reports[entry.key];

    if (!report) {
      continue;
    }

    const state = collectState(report);

    if (state) {
      states[entry.key] = state;
    } else {
      errors.push(`INVALID_STATE:${entry.file}`);
    }

    if (!safetyObjectSafe(report)) {
      errors.push(`UNSAFE_REPORT:${entry.file}`);
    }

    if (
      report.generatedAt !== undefined &&
      !isTimestamp(report.generatedAt)
    ) {
      errors.push(`INVALID_GENERATED_AT:${entry.file}`);
    }
  }

  const presentFiles = files.filter((file) => file.exists);
  const missingFiles = files.filter((file) => !file.exists);

  const uniqueHashes = new Set(
    presentFiles
      .map((file) => file.sha256)
      .filter((hash) => isSha256(hash))
  );

  /*
   * Missing downstream artifacts mean the evidence chain is
   * incomplete, not corrupted. Never upgrade INCOMPLETE to
   * VERIFIED_READ_ONLY.
   */
  if (missingFiles.length > 0) {
    for (const file of missingFiles) {
      errors.push(`MISSING_FILE:${file.file}`);
    }
  }

  const historyVerify = reports.historyVerify;
  const historyAnalysis = reports.historyAnalysis;
  const historyAnalysisVerify = reports.historyAnalysisVerify;
  const historyChainVerify = reports.historyChainVerify;
  const historyIntegrityAudit = reports.historyIntegrityAudit;
  const historyIntegrityAuditVerify =
    reports.historyIntegrityAuditVerify;

  if (
    historyVerify &&
    states.history &&
    collectState(historyVerify) &&
    states.history !== collectState(historyVerify)
  ) {
    errors.push("STATE_MISMATCH_HISTORY_VERIFY");
  }

  if (
    historyAnalysis &&
    historyAnalysisVerify &&
    collectState(historyAnalysis) &&
    collectState(historyAnalysisVerify) &&
    collectState(historyAnalysis) !==
      collectState(historyAnalysisVerify)
  ) {
    errors.push("STATE_MISMATCH_ANALYSIS_VERIFY");
  }

  if (
    historyIntegrityAudit &&
    historyIntegrityAuditVerify &&
    collectState(historyIntegrityAudit) &&
    collectState(historyIntegrityAuditVerify) &&
    collectState(historyIntegrityAudit) !==
      collectState(historyIntegrityAuditVerify)
  ) {
    errors.push("STATE_MISMATCH_INTEGRITY_VERIFY");
  }

  if (
    historyChainVerify &&
    collectState(historyChainVerify) === "VERIFIED_READ_ONLY"
  ) {
    const unsafeUpstream = Object.entries(states).some(
      ([key, state]) =>
        key !== "history" &&
        (state === "BLOCKED" || state === "INCOMPLETE")
    );

    if (unsafeUpstream) {
      errors.push("CHAIN_STATE_INCONSISTENT");
    }
  }

  if (
    historyIntegrityAudit?.integrity &&
    historyIntegrityAudit.integrity.integrityValid === false
  ) {
    errors.push("INTEGRITY_AUDIT_INVALID");
  }

  if (
    historyIntegrityAuditVerify?.state ===
      "VERIFIED_READ_ONLY" &&
    historyIntegrityAuditVerify.verification?.valid !== true
  ) {
    errors.push("INTEGRITY_VERIFY_STATE_MISMATCH");
  }

  /*
   * Safety errors are BLOCKED.
   * Missing downstream evidence is INCOMPLETE.
   */
  const safetyErrors = errors.filter(
    (error) =>
      error.startsWith("UNSAFE_") ||
      error.includes("INVALID_JSON") ||
      error.includes("INVALID_HISTORY") ||
      error.includes("STATE_MISMATCH") ||
      error.includes("CHAIN_STATE_INCONSISTENT") ||
      error.includes("INTEGRITY_")
  );

  let state;

  if (safetyErrors.length > 0) {
    state = "BLOCKED";
  } else if (missingFiles.length > 0) {
    state = "INCOMPLETE";
  } else if (
    Object.values(states).some(
      (value) => value === "BLOCKED"
    )
  ) {
    state = "BLOCKED";
  } else if (
    Object.values(states).some(
      (value) => value === "INCOMPLETE"
    )
  ) {
    state = "INCOMPLETE";
  } else if (
    Object.values(states).length === FILES.length &&
    Object.values(states).every(
      (value) => value === "VERIFIED_READ_ONLY"
    )
  ) {
    state = "VERIFIED_READ_ONLY";
  } else if (
    Object.values(states).some(
      (value) => value === "READY_READ_ONLY"
    )
  ) {
    state = "READY_READ_ONLY";
  } else if (
    Object.values(states).some(
      (value) => value === "BACKEND_UNAVAILABLE"
    )
  ) {
    state = "BACKEND_UNAVAILABLE";
  } else {
    state = "INCOMPLETE";
  }

  const manifest = {
    version: VERSION,
    type: "AACP_PROVIDER_EVIDENCE_MANIFEST",
    generatedAt,

    mode: "READ_ONLY",
    state,
    sourceState: state,

    executionAuthorized: false,

    safety: {
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

    artifacts: {
      expected: FILES.length,
      present: presentFiles.length,
      missing: missingFiles.length,
      uniqueSha256: uniqueHashes.size,
      files,
    },

    states,

    consistency: {
      historyVerify:
        Boolean(historyVerify) &&
        Boolean(states.history) &&
        collectState(historyVerify) === states.history,

      analysisVerify:
        Boolean(historyAnalysis && historyAnalysisVerify) &&
        collectState(historyAnalysis) ===
          collectState(historyAnalysisVerify),

      integrityVerify:
        Boolean(
          historyIntegrityAudit &&
            historyIntegrityAuditVerify
        ) &&
        collectState(historyIntegrityAudit) ===
          collectState(historyIntegrityAuditVerify),

      chainConsistent:
        !errors.includes("CHAIN_STATE_INCONSISTENT"),
    },

    errors,

    policy: POLICY,
  };

  fs.writeFileSync(
    OUTPUT_FILE,
    JSON.stringify(manifest, null, 2) + "\n",
    "utf8"
  );

  console.log("TERMiX AACP PROVIDER EVIDENCE MANIFEST v1.0");
  console.log("READ ONLY / FAIL CLOSED");
  console.log("==============================================");
  console.log(`STATE: ${manifest.state}`);
  console.log(
    `ARTIFACTS EXPECTED: ${manifest.artifacts.expected}`
  );
  console.log(
    `ARTIFACTS PRESENT: ${manifest.artifacts.present}`
  );
  console.log(
    `ARTIFACTS MISSING: ${manifest.artifacts.missing}`
  );
  console.log(
    `UNIQUE SHA256: ${manifest.artifacts.uniqueSha256}`
  );
  console.log(`ERRORS: ${manifest.errors.length}`);
  console.log(
    `EXECUTION AUTHORIZED: ${manifest.executionAuthorized}`
  );
  console.log(`POST: ${POLICY.post}`);
  console.log(`WALLET: ${POLICY.wallet}`);
  console.log(`SIGNING: ${POLICY.signing}`);
  console.log(`BROADCAST: ${POLICY.broadcast}`);
  console.log(`SUBMISSION: ${POLICY.submission}`);
  console.log(`REPORT: ${OUTPUT_FILE}`);

  /*
   * INCOMPLETE is a valid observation state and does not
   * indicate unsafe execution.
   */
  if (manifest.state === "BLOCKED") {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error("BLOCKED: evidence manifest failure");
  console.error(error?.message || String(error));
  process.exitCode = 1;
});
