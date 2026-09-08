import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";

const OUTPUT_DIR =
  process.env.AACP_OUTPUT_DIR ||
  path.join(process.cwd(), "provider-output", "aacp-observer");

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health.json"
);

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const ARTIFACTS = [
  {
    phase: "PHASE_12",
    key: "watchHistory",
    file: "latest-provider-watch-history.json",
  },
  {
    phase: "PHASE_13",
    key: "watchHistoryVerify",
    file: "latest-provider-watch-history-verify.json",
  },
  {
    phase: "PHASE_14",
    key: "watchHistoryAnalysis",
    file: "latest-provider-watch-history-analysis.json",
  },
  {
    phase: "PHASE_15",
    key: "watchHistoryAnalysisVerify",
    file: "latest-provider-watch-history-analysis-verify.json",
  },
  {
    phase: "PHASE_16",
    key: "watchHistoryChainVerify",
    file: "latest-provider-watch-history-chain-verify.json",
  },
  {
    phase: "PHASE_17",
    key: "watchHistoryIntegrityAudit",
    file: "latest-provider-watch-history-integrity-audit.json",
  },
  {
    phase: "PHASE_18",
    key: "watchHistoryIntegrityAuditVerify",
    file: "latest-provider-watch-history-integrity-audit-verify.json",
  },
  {
    phase: "PHASE_19",
    key: "evidenceManifest",
    file: "latest-provider-evidence-manifest.json",
  },
  {
    phase: "PHASE_20",
    key: "evidenceManifestVerify",
    file: "latest-provider-evidence-manifest-verify.json",
  },
  {
    phase: "PHASE_21",
    key: "evidenceManifestAudit",
    file: "latest-provider-evidence-manifest-audit.json",
  },
  {
    phase: "PHASE_22",
    key: "evidenceManifestAuditVerify",
    file: "latest-provider-evidence-manifest-audit-verify.json",
  },
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

const SAFETY_FIELDS = [
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
];

function isObject(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value)
  );
}

function isBoolean(value) {
  return typeof value === "boolean";
}

function isSha256(value) {
  return (
    typeof value === "string" &&
    /^[a-f0-9]{64}$/i.test(value)
  );
}

function isTimestamp(value) {
  return (
    typeof value === "string" &&
    Number.isFinite(Date.parse(value))
  );
}

function readJson(file) {
  return JSON.parse(
    fs.readFileSync(file, "utf8")
  );
}

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function safeFlags(report) {
  if (!isObject(report)) {
    return false;
  }

  if (!isObject(report.safety)) {
    return false;
  }

  if (!isObject(report.sideEffects)) {
    return false;
  }

  return SAFETY_FIELDS.every(
    (field) =>
      report.safety[field] === false &&
      report.sideEffects[field] === false
  );
}

function verifyPolicy(report) {
  if (!isObject(report?.policy)) {
    return false;
  }

  return (
    report.policy.readOnly === POLICY.readOnly &&
    report.policy.failClosed === POLICY.failClosed &&
    report.policy.post === POLICY.post &&
    report.policy.wallet === POLICY.wallet &&
    report.policy.signing === POLICY.signing &&
    report.policy.broadcast === POLICY.broadcast &&
    report.policy.submission === POLICY.submission
  );
}

function verifyReport(report, expectedType) {
  const errors = [];

  if (!isObject(report)) {
    return ["INVALID_ROOT"];
  }

  if (report.version !== VERSION) {
    errors.push("INVALID_VERSION");
  }

  if (report.type !== expectedType) {
    errors.push(`INVALID_TYPE:${expectedType}`);
  }

  if (!isTimestamp(report.generatedAt)) {
    errors.push("INVALID_TIMESTAMP");
  }

  if (!ALLOWED_STATES.has(report.state)) {
    errors.push("INVALID_STATE");
  }

  if (typeof report.sourceState !== "string") {
    errors.push("INVALID_SOURCE_STATE");
  }

  if (report.mode !== "READ_ONLY") {
    errors.push("MODE_NOT_READ_ONLY");
  }

  if (report.executionAuthorized !== false) {
    errors.push("EXECUTION_AUTHORIZED");
  }

  if (!safeFlags(report)) {
    errors.push("SAFETY_VIOLATION");
  }

  if (!verifyPolicy(report)) {
    errors.push("POLICY_VIOLATION");
  }

  return errors;
}

function inspectArtifact(descriptor) {
  const file = path.join(
    OUTPUT_DIR,
    descriptor.file
  );

  if (!fs.existsSync(file)) {
    return {
      ...descriptor,
      exists: false,
      valid: false,
      state: null,
      sourceState: null,
      sha256: null,
      errors: [`MISSING:${descriptor.file}`],
    };
  }

  const errors = [];

  let report;

  try {
    report = readJson(file);
  } catch {
    return {
      ...descriptor,
      exists: true,
      valid: false,
      state: "BLOCKED",
      sourceState: "BLOCKED",
      sha256: sha256File(file),
      errors: [`INVALID_JSON:${descriptor.file}`],
    };
  }

  /*
   * Phase 12 is raw provider watch history.
   * It is NOT a normal provider report and therefore
   * has no root-level generatedAt/state/sourceState/policy.
   */
  if (descriptor.phase === "PHASE_12") {
    if (report.version !== VERSION) {
      errors.push("INVALID_VERSION");
    }

    if (report.mode !== "READ_ONLY") {
      errors.push("MODE_NOT_READ_ONLY");
    }

    if (!Array.isArray(report.events)) {
      errors.push("INVALID_EVENTS");

      return {
        ...descriptor,
        exists: true,
        valid: false,
        state: "BLOCKED",
        sourceState: "BLOCKED",
        sha256: sha256File(file),
        errors,
      };
    }

    let previousGeneratedAt = null;
    const ids = new Set();

    for (let index = 0; index < report.events.length; index += 1) {
      const event = report.events[index];
      const prefix = `EVENT_${index + 1}`;

      if (!isObject(event)) {
        errors.push(`${prefix}:INVALID_ROOT`);
        continue;
      }

      if (
        typeof event.id !== "string" ||
        event.id.length === 0
      ) {
        errors.push(`${prefix}:INVALID_ID`);
      } else if (ids.has(event.id)) {
        errors.push(`${prefix}:DUPLICATE_ID`);
      } else {
        ids.add(event.id);
      }

      if (!isTimestamp(event.generatedAt)) {
        errors.push(`${prefix}:INVALID_TIMESTAMP`);
      } else if (previousGeneratedAt !== null) {
        const current = Date.parse(event.generatedAt);

        if (current < previousGeneratedAt) {
          errors.push(`${prefix}:CHRONOLOGY`);
        }

        previousGeneratedAt = current;
      } else {
        previousGeneratedAt = Date.parse(
          event.generatedAt
        );
      }

      if (!ALLOWED_STATES.has(event.state)) {
        errors.push(`${prefix}:INVALID_STATE`);
      }

      if (typeof event.changed !== "boolean") {
        errors.push(`${prefix}:INVALID_CHANGED`);
      }

      if (!Array.isArray(event.changedFields)) {
        errors.push(`${prefix}:INVALID_CHANGED_FIELDS`);
      }

      if (!isObject(event.fingerprint)) {
        errors.push(`${prefix}:INVALID_FINGERPRINT`);
      } else {
        const fp = event.fingerprint;

        if (typeof fp.state !== "string") {
          errors.push(`${prefix}:FINGERPRINT_STATE`);
        }

        if (typeof fp.sourceState !== "string") {
          errors.push(`${prefix}:FINGERPRINT_SOURCE_STATE`);
        }

        if (fp.mode !== "READ_ONLY") {
          errors.push(`${prefix}:FINGERPRINT_MODE`);
        }

        if (fp.executionAuthorized !== false) {
          errors.push(
            `${prefix}:FINGERPRINT_EXECUTION_AUTHORIZED`
          );
        }

        for (const field of SAFETY_FIELDS) {
          if (fp[field] !== false) {
            errors.push(
              `${prefix}:FINGERPRINT_${field.toUpperCase()}`
            );
          }
        }
      }

      if (!isObject(event.safety)) {
        errors.push(`${prefix}:INVALID_SAFETY`);
      } else {
        if (event.safety.executionAuthorized !== false) {
          errors.push(
            `${prefix}:SAFETY_EXECUTION_AUTHORIZED`
          );
        }

        for (const field of SAFETY_FIELDS) {
          if (event.safety[field] !== false) {
            errors.push(
              `${prefix}:SAFETY_${field.toUpperCase()}`
            );
          }
        }
      }

      if (!isObject(event.sideEffects)) {
        errors.push(`${prefix}:INVALID_SIDE_EFFECTS`);
      } else {
        for (const field of SAFETY_FIELDS) {
          if (event.sideEffects[field] !== false) {
            errors.push(
              `${prefix}:SIDE_EFFECT_${field.toUpperCase()}`
            );
          }
        }
      }

      if (event.executionAuthorized !== false) {
        errors.push(
          `${prefix}:EXECUTION_AUTHORIZED`
        );
      }

      if (
        isObject(event.fingerprint) &&
        typeof event.state === "string" &&
        event.fingerprint.state !== event.state
      ) {
        errors.push(
          `${prefix}:STATE_FINGERPRINT_MISMATCH`
        );
      }

      if (
        isObject(event.fingerprint) &&
        typeof event.state === "string" &&
        typeof event.fingerprint.sourceState === "string" &&
        event.fingerprint.sourceState !== event.state
      ) {
        errors.push(
          `${prefix}:SOURCE_STATE_FINGERPRINT_MISMATCH`
        );
      }
    }

    /*
     * Empty raw history is incomplete rather than corrupt.
     */
    if (report.events.length === 0) {
      return {
        ...descriptor,
        exists: true,
        valid: true,
        state: "INCOMPLETE",
        sourceState: "INCOMPLETE",
        sha256: sha256File(file),
        errors: [],
      };
    }

    const states = report.events.map(
      (event) =>
        ALLOWED_STATES.has(event?.state)
          ? event.state
          : "BLOCKED"
    );

    let state = "INCOMPLETE";

    if (errors.length > 0) {
      state = "BLOCKED";
    } else if (
      states.every(
        (value) =>
          value === "VERIFIED_READ_ONLY"
      )
    ) {
      state = "VERIFIED_READ_ONLY";
    } else if (
      states.every(
        (value) =>
          value === "READY_READ_ONLY"
      )
    ) {
      state = "READY_READ_ONLY";
    } else if (
      states.includes("BACKEND_UNAVAILABLE")
    ) {
      state = "BACKEND_UNAVAILABLE";
    } else if (
      states.includes("BLOCKED")
    ) {
      state = "BLOCKED";
    } else {
      state = "INCOMPLETE";
    }

    return {
      ...descriptor,
      exists: true,
      valid: errors.length === 0,
      state,
      sourceState: state,
      sha256: sha256File(file),
      errors,
    };
  }

  const expectedTypes = {
    PHASE_13:
      "AACP_PROVIDER_WATCH_HISTORY_VERIFY",
    PHASE_14:
      "AACP_PROVIDER_WATCH_HISTORY_ANALYSIS",
    PHASE_15:
      "AACP_PROVIDER_WATCH_HISTORY_ANALYSIS_VERIFY",
    PHASE_16:
      "AACP_PROVIDER_WATCH_HISTORY_CHAIN_VERIFY",
    PHASE_17:
      "AACP_PROVIDER_WATCH_HISTORY_INTEGRITY_AUDIT",
    PHASE_18:
      "AACP_PROVIDER_WATCH_HISTORY_INTEGRITY_AUDIT_VERIFY",
    PHASE_19:
      "AACP_PROVIDER_EVIDENCE_MANIFEST",
    PHASE_20:
      "AACP_PROVIDER_EVIDENCE_MANIFEST_VERIFY",
    PHASE_21:
      "AACP_PROVIDER_EVIDENCE_MANIFEST_AUDIT",
    PHASE_22:
      "AACP_PROVIDER_EVIDENCE_MANIFEST_AUDIT_VERIFY",
  };

  const expectedType =
    expectedTypes[descriptor.phase];

  errors.push(
    ...verifyReport(report, expectedType)
  );

  const state = ALLOWED_STATES.has(report.state)
    ? report.state
    : "BLOCKED";

  const sourceState =
    typeof report.sourceState === "string"
      ? report.sourceState
      : state;

  return {
    ...descriptor,
    exists: true,
    valid: errors.length === 0,
    state,
    sourceState,
    sha256: sha256File(file),
    errors,
  };
}

function deriveHealth(artifacts) {
  const errors = [];
  const missing = [];
  const blocked = [];
  const verified = [];

  for (const artifact of artifacts) {
    if (!artifact.exists) {
      missing.push(artifact.file);
      continue;
    }

    if (!artifact.valid) {
      blocked.push(artifact.file);
    }

    if (artifact.state === "VERIFIED_READ_ONLY") {
      verified.push(artifact.file);
    }

    errors.push(...artifact.errors);
  }

  if (blocked.length > 0) {
    return {
      state: "BLOCKED",
      errors,
      missing,
      blocked,
      verified,
    };
  }

  if (missing.length > 0) {
    return {
      state: "INCOMPLETE",
      errors,
      missing,
      blocked,
      verified,
    };
  }

  const states = new Set(
    artifacts.map((artifact) => artifact.state)
  );

  if (states.has("BLOCKED")) {
    return {
      state: "BLOCKED",
      errors,
      missing,
      blocked,
      verified,
    };
  }

  if (
    states.size === 1 &&
    states.has("VERIFIED_READ_ONLY")
  ) {
    return {
      state: "VERIFIED_READ_ONLY",
      errors,
      missing,
      blocked,
      verified,
    };
  }

  return {
    state: "READY_READ_ONLY",
    errors,
    missing,
    blocked,
    verified,
  };
}

function buildReport(artifacts, health) {
  const present = artifacts.filter(
    (artifact) => artifact.exists
  ).length;

  const missing = artifacts.length - present;

  return {
    version: VERSION,
    type: "AACP_EVIDENCE_CHAIN_HEALTH",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state: health.state,
    sourceState: health.state,
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

    health: {
      artifactsExpected: artifacts.length,
      artifactsPresent: present,
      artifactsMissing: missing,
      artifactsBlocked: health.blocked.length,
      artifactsVerified: health.verified.length,
      missing: health.missing,
      blocked: health.blocked,
      errors: health.errors,
      errorCount: health.errors.length,
      allArtifactsPresent: missing === 0,
      allArtifactsValid: health.blocked.length === 0,
    },

    artifacts: artifacts.map(
      (artifact) => ({
        phase: artifact.phase,
        key: artifact.key,
        file: artifact.file,
        exists: artifact.exists,
        valid: artifact.valid,
        state: artifact.state,
        sourceState: artifact.sourceState,
        sha256: artifact.sha256,
        errors: artifact.errors,
      })
    ),

    policy: POLICY,
  };
}

function main() {
  fs.mkdirSync(
    OUTPUT_DIR,
    { recursive: true }
  );

  const artifacts = ARTIFACTS.map(
    inspectArtifact
  );

  const health = deriveHealth(artifacts);

  const report = buildReport(
    artifacts,
    health
  );

  fs.writeFileSync(
    OUTPUT_FILE,
    JSON.stringify(report, null, 2) + "\n",
    "utf8"
  );

  console.log(
    "TERMiX AACP EVIDENCE CHAIN HEALTH v1.0"
  );
  console.log(
    "READ ONLY / FAIL CLOSED"
  );
  console.log(
    "======================================="
  );
  console.log(
    `STATE: ${report.state}`
  );
  console.log(
    `ARTIFACTS EXPECTED: ${report.health.artifactsExpected}`
  );
  console.log(
    `ARTIFACTS PRESENT: ${report.health.artifactsPresent}`
  );
  console.log(
    `ARTIFACTS MISSING: ${report.health.artifactsMissing}`
  );
  console.log(
    `ARTIFACTS BLOCKED: ${report.health.artifactsBlocked}`
  );
  console.log(
    `ARTIFACTS VERIFIED: ${report.health.artifactsVerified}`
  );
  console.log(
    `ERRORS: ${report.health.errorCount}`
  );
  console.log(
    `EXECUTION AUTHORIZED: ${report.executionAuthorized}`
  );
  console.log(
    `POST: ${report.policy.post}`
  );
  console.log(
    `WALLET: ${report.policy.wallet}`
  );
  console.log(
    `SIGNING: ${report.policy.signing}`
  );
  console.log(
    `BROADCAST: ${report.policy.broadcast}`
  );
  console.log(
    `SUBMISSION: ${report.policy.submission}`
  );
  console.log(
    `REPORT: ${OUTPUT_FILE}`
  );

  if (report.state === "BLOCKED") {
    process.exitCode = 1;
  }
}

main();
