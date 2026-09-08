import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";

const OUTPUT_DIR =
  process.env.AACP_OUTPUT_DIR ||
  path.join(process.cwd(), "provider-output", "aacp-observer");

const AUDIT_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health-audit.json"
);

const VERIFY_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health-audit-verify.json"
);

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health-audit-history.json"
);

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const SAFETY_FIELDS = [
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

function isObject(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value)
  );
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
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function verifySafety(report, prefix) {
  const errors = [];

  if (report?.executionAuthorized !== false) {
    errors.push(`${prefix}:EXECUTION_AUTHORIZED`);
  }

  if (!isObject(report?.safety)) {
    errors.push(`${prefix}:INVALID_SAFETY`);
  } else {
    for (const field of SAFETY_FIELDS) {
      if (report.safety[field] !== false) {
        errors.push(`${prefix}:SAFETY:${field}`);
      }
    }
  }

  if (!isObject(report?.sideEffects)) {
    errors.push(`${prefix}:INVALID_SIDE_EFFECTS`);
  } else {
    for (const field of SAFETY_FIELDS) {
      if (report.sideEffects[field] !== false) {
        errors.push(`${prefix}:SIDE_EFFECT:${field}`);
      }
    }
  }

  return errors;
}

function verifyPolicy(report, prefix) {
  const errors = [];

  if (!isObject(report?.policy)) {
    return [`${prefix}:INVALID_POLICY`];
  }

  for (const [key, expected] of Object.entries(POLICY)) {
    if (report.policy[key] !== expected) {
      errors.push(`${prefix}:POLICY:${key}`);
    }
  }

  return errors;
}

function verifyAuditReport(report) {
  const errors = [];

  if (!isObject(report)) {
    return ["AUDIT:ROOT_INVALID"];
  }

  if (report.version !== VERSION) {
    errors.push("AUDIT:VERSION");
  }

  if (report.type !== "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT") {
    errors.push("AUDIT:TYPE");
  }

  if (!isTimestamp(report.generatedAt)) {
    errors.push("AUDIT:GENERATED_AT");
  }

  if (report.mode !== "READ_ONLY") {
    errors.push("AUDIT:MODE");
  }

  if (!ALLOWED_STATES.has(report.state)) {
    errors.push("AUDIT:STATE");
  }

  if (
    typeof report.sourceState !== "string" ||
    !ALLOWED_STATES.has(report.sourceState)
  ) {
    errors.push("AUDIT:SOURCE_STATE");
  }

  if (report.state !== report.sourceState) {
    errors.push("AUDIT:STATE_SOURCE_STATE");
  }

  errors.push(...verifySafety(report, "AUDIT"));
  errors.push(...verifyPolicy(report, "AUDIT"));

  if (!isObject(report.audit)) {
    errors.push("AUDIT:INVALID_AUDIT");
  } else {
    if (typeof report.audit.valid !== "boolean") {
      errors.push("AUDIT:VALID");
    }

    if (!Array.isArray(report.audit.findings)) {
      errors.push("AUDIT:FINDINGS");
    }

    if (!Array.isArray(report.audit.errors)) {
      errors.push("AUDIT:ERRORS");
    }

    if (
      !Number.isInteger(report.audit.errorCount) ||
      report.audit.errorCount < 0
    ) {
      errors.push("AUDIT:ERROR_COUNT");
    }

    if (
      Array.isArray(report.audit.errors) &&
      Number.isInteger(report.audit.errorCount) &&
      report.audit.errorCount !== report.audit.errors.length
    ) {
      errors.push("AUDIT:ERROR_COUNT_MISMATCH");
    }
  }

  if (!isObject(report.sources)) {
    errors.push("AUDIT:SOURCES");
  }

  return errors;
}

function verifyVerifyReport(report) {
  const errors = [];

  if (!isObject(report)) {
    return ["VERIFY:ROOT_INVALID"];
  }

  if (report.version !== VERSION) {
    errors.push("VERIFY:VERSION");
  }

  if (report.type !== "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_VERIFY") {
    errors.push("VERIFY:TYPE");
  }

  if (!isTimestamp(report.generatedAt)) {
    errors.push("VERIFY:GENERATED_AT");
  }

  if (report.mode !== "READ_ONLY") {
    errors.push("VERIFY:MODE");
  }

  if (!ALLOWED_STATES.has(report.state)) {
    errors.push("VERIFY:STATE");
  }

  if (
    typeof report.sourceState !== "string" ||
    !ALLOWED_STATES.has(report.sourceState)
  ) {
    errors.push("VERIFY:SOURCE_STATE");
  }

  if (report.state !== report.sourceState) {
    errors.push("VERIFY:STATE_SOURCE_STATE");
  }

  errors.push(...verifySafety(report, "VERIFY"));
  errors.push(...verifyPolicy(report, "VERIFY"));

  if (!isObject(report.verification)) {
    errors.push("VERIFY:VERIFICATION");
  } else {
    if (typeof report.verification.valid !== "boolean") {
      errors.push("VERIFY:VALID");
    }

    if (!Array.isArray(report.verification.findings)) {
      errors.push("VERIFY:FINDINGS");
    }

    if (!Array.isArray(report.verification.errors)) {
      errors.push("VERIFY:ERRORS");
    }

    if (
      !Number.isInteger(report.verification.errorCount) ||
      report.verification.errorCount < 0
    ) {
      errors.push("VERIFY:ERROR_COUNT");
    }

    if (
      Array.isArray(report.verification.errors) &&
      Number.isInteger(report.verification.errorCount) &&
      report.verification.errorCount !==
        report.verification.errors.length
    ) {
      errors.push("VERIFY:ERROR_COUNT_MISMATCH");
    }
  }

  if (!isObject(report.sources)) {
    errors.push("VERIFY:SOURCES");
  }

  return errors;
}

function buildHistory({
  state,
  sourceState,
  audit,
  verify,
  errors,
}) {
  return {
    version: VERSION,
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",

    state,
    sourceState,

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

    snapshots: {
      audit: audit
        ? {
            file: path.basename(AUDIT_FILE),
            exists: true,
            sha256: sha256File(AUDIT_FILE),
            state: audit.state,
            sourceState: audit.sourceState,
            auditValid:
              typeof audit.audit?.valid === "boolean"
                ? audit.audit.valid
                : null,
            errorCount:
              Number.isInteger(audit.audit?.errorCount)
                ? audit.audit.errorCount
                : null,
          }
        : {
            file: path.basename(AUDIT_FILE),
            exists: false,
            sha256: null,
            state: null,
            sourceState: null,
            auditValid: null,
            errorCount: null,
          },

      verify: verify
        ? {
            file: path.basename(VERIFY_FILE),
            exists: true,
            sha256: sha256File(VERIFY_FILE),
            state: verify.state,
            sourceState: verify.sourceState,
            verificationValid:
              typeof verify.verification?.valid === "boolean"
                ? verify.verification.valid
                : null,
            errorCount:
              Number.isInteger(verify.verification?.errorCount)
                ? verify.verification.errorCount
                : null,
          }
        : {
            file: path.basename(VERIFY_FILE),
            exists: false,
            sha256: null,
            state: null,
            sourceState: null,
            verificationValid: null,
            errorCount: null,
          },
    },

    consistency: {
      auditExists: Boolean(audit),
      verifyExists: Boolean(verify),
      stateMatch:
        Boolean(audit) &&
        Boolean(verify) &&
        audit.state === verify.state,
      sourceStateMatch:
        Boolean(audit) &&
        Boolean(verify) &&
        audit.sourceState === verify.sourceState,
    },

    errors,
    errorCount: errors.length,

    policy: POLICY,
  };
}

function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });

  fs.writeFileSync(
    file,
    JSON.stringify(data, null, 2) + "\n",
    "utf8"
  );
}

function main() {
  const errors = [];

  let audit = null;
  let verify = null;

  if (fs.existsSync(AUDIT_FILE)) {
    try {
      audit = readJson(AUDIT_FILE);
      errors.push(...verifyAuditReport(audit));
    } catch {
      errors.push("AUDIT:INVALID_JSON");
    }
  }

  if (fs.existsSync(VERIFY_FILE)) {
    try {
      verify = readJson(VERIFY_FILE);
      errors.push(...verifyVerifyReport(verify));
    } catch {
      errors.push("VERIFY:INVALID_JSON");
    }
  }

  if (!audit && !verify) {
    const report = buildHistory({
      state: "INCOMPLETE",
      sourceState: "INCOMPLETE",
      audit: null,
      verify: null,
      errors: ["SOURCES:MISSING"],
    });

    writeJson(OUTPUT_FILE, report);

    console.log(
      "TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT HISTORY v1.0"
    );
    console.log("READ ONLY / FAIL CLOSED");
    console.log("STATE: INCOMPLETE");
    console.log("SOURCE STATE: INCOMPLETE");
    console.log("ERRORS: 1");
    console.log("EXECUTION AUTHORIZED: false");
    console.log(`REPORT: ${OUTPUT_FILE}`);

    return 0;
  }

  if (!audit) {
    errors.push("AUDIT:FILE_MISSING");
  }

  if (!verify) {
    errors.push("VERIFY:FILE_MISSING");
  }

  if (
    audit &&
    verify &&
    audit.state !== verify.state
  ) {
    errors.push("CROSS_LAYER:STATE_MISMATCH");
  }

  if (
    audit &&
    verify &&
    audit.sourceState !== verify.sourceState
  ) {
    errors.push("CROSS_LAYER:SOURCE_STATE_MISMATCH");
  }

  const state =
    errors.length > 0
      ? "BLOCKED"
      : audit?.state === "VERIFIED_READ_ONLY"
        ? "VERIFIED_READ_ONLY"
        : audit?.state || "INCOMPLETE";

  const sourceState =
    errors.length > 0
      ? "BLOCKED"
      : audit?.sourceState || "INCOMPLETE";

  const report = buildHistory({
    state,
    sourceState,
    audit,
    verify,
    errors,
  });

  writeJson(OUTPUT_FILE, report);

  console.log(
    "TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT HISTORY v1.0"
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log(`STATE: ${state}`);
  console.log(`SOURCE STATE: ${sourceState}`);
  console.log(`ERRORS: ${errors.length}`);
  console.log("EXECUTION AUTHORIZED: false");
  console.log(`REPORT: ${OUTPUT_FILE}`);

  return errors.length === 0 ? 0 : 1;
}

process.exitCode = main();
