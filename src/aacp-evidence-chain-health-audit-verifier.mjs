import fs from "node:fs";
import path from "node:path";

const VERSION = "1.0.0";

const OUTPUT_DIR =
  process.env.AACP_OUTPUT_DIR ||
  path.join(process.cwd(), "provider-output", "aacp-observer");

const AUDIT_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health-audit.json"
);

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health-audit-verify.json"
);

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const EXPECTED_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT";

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

function verifyRoot(report) {
  const errors = [];

  if (!isObject(report)) {
    return ["ROOT:INVALID"];
  }

  if (report.version !== VERSION) {
    errors.push("ROOT:VERSION");
  }

  if (report.type !== EXPECTED_TYPE) {
    errors.push("ROOT:TYPE");
  }

  if (!isTimestamp(report.generatedAt)) {
    errors.push("ROOT:GENERATED_AT");
  }

  if (report.mode !== "READ_ONLY") {
    errors.push("ROOT:MODE");
  }

  if (!ALLOWED_STATES.has(report.state)) {
    errors.push("ROOT:STATE");
  }

  if (
    typeof report.sourceState !== "string" ||
    !ALLOWED_STATES.has(report.sourceState)
  ) {
    errors.push("ROOT:SOURCE_STATE");
  }

  if (report.state !== report.sourceState) {
    errors.push("ROOT:STATE_SOURCE_STATE");
  }

  return errors;
}

function verifyAudit(report) {
  const errors = [];
  const audit = report?.audit;

  if (!isObject(audit)) {
    return ["AUDIT:INVALID_STRUCTURE"];
  }

  if (typeof audit.valid !== "boolean") {
    errors.push("AUDIT:VALID");
  }

  if (!Array.isArray(audit.findings)) {
    errors.push("AUDIT:FINDINGS");
  }

  if (!Array.isArray(audit.errors)) {
    errors.push("AUDIT:ERRORS");
  }

  if (
    !Number.isInteger(audit.errorCount) ||
    audit.errorCount < 0
  ) {
    errors.push("AUDIT:ERROR_COUNT");
  }

  if (
    Array.isArray(audit.errors) &&
    Number.isInteger(audit.errorCount) &&
    audit.errorCount !== audit.errors.length
  ) {
    errors.push("AUDIT:ERROR_COUNT_MISMATCH");
  }

  /*
   * Phase 25 semantics:
   * audit.valid means the audit itself is structurally valid.
   * It does NOT mean the complete evidence chain is verified.
   *
   * Therefore:
   *   INCOMPLETE + valid=true + errors=[] is legitimate.
   */

  if (
    report.state === "BLOCKED" &&
    Array.isArray(audit.errors) &&
    audit.errors.length === 0
  ) {
    errors.push("AUDIT:BLOCKED_WITHOUT_ERRORS");
  }

  if (
    report.state !== "BLOCKED" &&
    Array.isArray(audit.errors) &&
    audit.errors.length > 0
  ) {
    errors.push("AUDIT:ERRORS_WITHOUT_BLOCKED");
  }

  return errors;
}

function verifySources(report) {
  const errors = [];
  const sources = report?.sources;

  if (!isObject(sources)) {
    return ["SOURCES:INVALID"];
  }

  for (const key of ["health", "verify"]) {
    const source = sources[key];

    if (!isObject(source)) {
      errors.push(`SOURCES:${key.toUpperCase()}:INVALID`);
      continue;
    }

    if (
      typeof source.file !== "string" ||
      !source.file
    ) {
      errors.push(`SOURCES:${key.toUpperCase()}:FILE`);
      continue;
    }

    if (typeof source.exists !== "boolean") {
      errors.push(`SOURCES:${key.toUpperCase()}:EXISTS`);
      continue;
    }

    const localFile = path.join(
      OUTPUT_DIR,
      path.basename(source.file)
    );

    if (source.exists === false) {
      if (source.sha256 !== null) {
        errors.push(
          `SOURCES:${key.toUpperCase()}:MISSING_SHA256`
        );
      }

      continue;
    }

    if (!isSha256(source.sha256)) {
      errors.push(
        `SOURCES:${key.toUpperCase()}:SHA256`
      );
      continue;
    }

    if (!fs.existsSync(localFile)) {
      errors.push(
        `SOURCES:${key.toUpperCase()}:FILE_MISSING`
      );
      continue;
    }

    const actual = sha256File(localFile);

    if (actual !== source.sha256) {
      errors.push(
        `SOURCES:${key.toUpperCase()}:SHA256_MISMATCH`
      );
    }
  }

  return errors;
}

function verifyCrossLayer(report) {
  const errors = [];

  if (report.state !== report.sourceState) {
    errors.push("CROSS_LAYER:STATE_SOURCE_STATE");
  }

  if (
    report.state === "VERIFIED_READ_ONLY" &&
    report.audit?.valid !== true
  ) {
    errors.push("CROSS_LAYER:VERIFIED_WITHOUT_VALID_AUDIT");
  }

  if (
    report.audit &&
    Array.isArray(report.audit.errors) &&
    Number.isInteger(report.audit.errorCount) &&
    report.audit.errorCount !== report.audit.errors.length
  ) {
    errors.push("CROSS_LAYER:ERROR_COUNT");
  }

  return errors;
}

function buildReport({
  state,
  sourceState,
  sources,
  verification,
}) {
  return {
    version: VERSION,
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_VERIFY",
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
    sources,
    verification,
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

function makeIncomplete(reason) {
  const report = buildReport({
    state: "INCOMPLETE",
    sourceState: "INCOMPLETE",
    sources: {
      health: {
        file: "latest-aacp-evidence-chain-health.json",
        exists: false,
        sha256: null,
      },
      verify: {
        file: "latest-aacp-evidence-chain-health-verify.json",
        exists: false,
        sha256: null,
      },
    },
    verification: {
      valid: false,
      sourceState: "INCOMPLETE",
      findings: [reason],
      errors: [],
      errorCount: 0,
    },
  });

  writeJson(OUTPUT_FILE, report);

  console.log(
    "TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT VERIFY v1.0"
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log("STATE: INCOMPLETE");
  console.log("SOURCE STATE: INCOMPLETE");
  console.log("ERRORS: 0");
  console.log("EXECUTION AUTHORIZED: false");
  console.log(`REPORT: ${OUTPUT_FILE}`);

  return 0;
}

function main() {
  if (!fs.existsSync(AUDIT_FILE)) {
    return makeIncomplete(
      `MISSING:${path.basename(AUDIT_FILE)}`
    );
  }

  let audit;

  try {
    audit = readJson(AUDIT_FILE);
  } catch {
    const report = buildReport({
      state: "BLOCKED",
      sourceState: "BLOCKED",
      sources: {
        health: {
          file: "latest-aacp-evidence-chain-health.json",
          exists: false,
          sha256: null,
        },
        verify: {
          file: "latest-aacp-evidence-chain-health-verify.json",
          exists: false,
          sha256: null,
        },
      },
      verification: {
        valid: false,
        sourceState: "BLOCKED",
        findings: [],
        errors: ["AUDIT:INVALID_JSON"],
        errorCount: 1,
      },
    });

    writeJson(OUTPUT_FILE, report);

    console.log(
      "TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT VERIFY v1.0"
    );
    console.log("READ ONLY / FAIL CLOSED");
    console.log("STATE: BLOCKED");
    console.log("SOURCE STATE: BLOCKED");
    console.log("FINDINGS: 0");
    console.log("ERRORS: 1");
    console.log("EXECUTION AUTHORIZED: false");
    console.log(`REPORT: ${OUTPUT_FILE}`);

    return 1;
  }

  const errors = [
    ...verifyRoot(audit),
    ...verifySafety(audit, "AUDIT_REPORT"),
    ...verifyPolicy(audit, "AUDIT_REPORT"),
    ...verifyAudit(audit),
    ...verifySources(audit),
    ...verifyCrossLayer(audit),
  ];

  let state;

  if (errors.length > 0) {
    state = "BLOCKED";
  } else if (audit.state === "INCOMPLETE") {
    state = "INCOMPLETE";
  } else if (audit.state === "VERIFIED_READ_ONLY") {
    state = "VERIFIED_READ_ONLY";
  } else {
    state = audit.state;
  }

  const sourceState =
    errors.length > 0
      ? "BLOCKED"
      : state;

  const report = buildReport({
    state,
    sourceState,
    sources: audit.sources,
    verification: {
      valid: errors.length === 0,
      sourceState: audit.sourceState,
      findings:
        errors.length === 0
          ? ["AUDIT_VERIFIED"]
          : [],
      errors,
      errorCount: errors.length,
    },
  });

  writeJson(OUTPUT_FILE, report);

  console.log(
    "TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT VERIFY v1.0"
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log(`STATE: ${state}`);
  console.log(`SOURCE STATE: ${sourceState}`);
  console.log(
    `FINDINGS: ${report.verification.findings.length}`
  );
  console.log(`ERRORS: ${errors.length}`);
  console.log("EXECUTION AUTHORIZED: false");
  console.log(`REPORT: ${OUTPUT_FILE}`);

  return errors.length === 0 ? 0 : 1;
}

import crypto from "node:crypto";

process.exitCode = main();
