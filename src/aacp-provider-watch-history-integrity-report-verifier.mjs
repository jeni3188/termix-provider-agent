import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";

const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  path.resolve("provider-output/aacp-observer");

const AUDIT_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-integrity-audit.json",
);

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-integrity-audit-verify.json",
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
    !Number.isNaN(Date.parse(value))
  );
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
      sha256: crypto
        .createHash("sha256")
        .update(raw)
        .digest("hex"),
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

function unsafeFlagsSafe(value) {
  if (!isObject(value)) {
    return false;
  }

  return UNSAFE_FIELDS.every(
    (field) => value[field] === false,
  );
}

function sideEffectsSafe(value) {
  if (!isObject(value)) {
    return false;
  }

  return [
    "postPerformed",
    "walletUsed",
    "signingPerformed",
    "broadcastPerformed",
    "submissionPerformed",
  ].every(
    (field) => value[field] === false,
  );
}

function verifyAudit(report) {
  const errors = [];
  const checks = [];

  if (!report.exists) {
    errors.push("audit_missing");

    return {
      state: "INCOMPLETE",
      errors,
      checks,
    };
  }

  if (report.error) {
    errors.push(`audit_invalid_json:${report.error}`);

    return {
      state: "BLOCKED",
      errors,
      checks,
    };
  }

  const data = report.value;

  if (!isObject(data)) {
    errors.push("audit_invalid_root");

    return {
      state: "BLOCKED",
      errors,
      checks,
    };
  }

  checks.push("root_object");

  if (data.mode !== "READ_ONLY") {
    errors.push("non_read_only");
  } else {
    checks.push("read_only");
  }

  if (data.executionAuthorized !== false) {
    errors.push("execution_authorized");
  } else {
    checks.push("execution_unauthorized");
  }

  if (
    typeof data.state !== "string" ||
    !ALLOWED_STATES.has(data.state)
  ) {
    errors.push("invalid_state");
  } else {
    checks.push("allowed_state");
  }

  if (
    typeof data.sourceState !== "string" ||
    !ALLOWED_STATES.has(data.sourceState)
  ) {
    errors.push("invalid_source_state");
  } else {
    checks.push("allowed_source_state");
  }

  if (
    data.state !== data.sourceState
  ) {
    errors.push("state_source_state_mismatch");
  } else {
    checks.push("state_source_state_match");
  }

  if (!isTimestamp(data.generatedAt)) {
    errors.push("invalid_generated_at");
  } else {
    checks.push("generated_at");
  }

  if (!isObject(data.safety)) {
    errors.push("safety_missing");
  } else if (!unsafeFlagsSafe(data.safety)) {
    errors.push("unsafe_safety");
  } else {
    checks.push("safety_flags");
  }

  if (!isObject(data.sideEffects)) {
    errors.push("side_effects_missing");
  } else if (!sideEffectsSafe(data.sideEffects)) {
    errors.push("unsafe_side_effects");
  } else {
    checks.push("side_effect_flags");
  }

  if (!isObject(data.integrity)) {
    errors.push("integrity_missing");
  } else {
    checks.push("integrity_object");

    if (
      typeof data.integrity.integrityValid !== "boolean"
    ) {
      errors.push("integrity_valid_missing");
    }

    if (
      !Number.isInteger(data.integrity.errorCount) ||
      data.integrity.errorCount < 0
    ) {
      errors.push("invalid_error_count");
    }

    if (
      !Number.isInteger(data.integrity.findingCount) ||
      data.integrity.findingCount < 0
    ) {
      errors.push("invalid_finding_count");
    }

    if (!Array.isArray(data.integrity.errors)) {
      errors.push("integrity_errors_missing");
    }

    if (!Array.isArray(data.integrity.findings)) {
      errors.push("integrity_findings_missing");
    }

    if (!Array.isArray(data.integrity.findingTypes)) {
      errors.push("integrity_finding_types_missing");
    }

    if (
      Number.isInteger(data.integrity.errorCount) &&
      Array.isArray(data.integrity.errors) &&
      data.integrity.errorCount !==
        data.integrity.errors.length
    ) {
      errors.push("error_count_mismatch");
    }

    if (
      Number.isInteger(data.integrity.findingCount) &&
      Array.isArray(data.integrity.findings) &&
      data.integrity.findingCount !==
        data.integrity.findings.length
    ) {
      errors.push("finding_count_mismatch");
    }

    if (
      data.integrity.integrityValid === true &&
      data.integrity.errorCount !== 0
    ) {
      errors.push("integrity_valid_with_errors");
    }

    if (
      data.integrity.integrityValid === false &&
      data.integrity.errorCount === 0
    ) {
      errors.push("integrity_invalid_without_errors");
    }

    if (
      data.state === "VERIFIED_READ_ONLY" &&
      data.integrity.integrityValid !== true
    ) {
      errors.push("verified_state_with_invalid_integrity");
    }

    if (
      data.state === "BLOCKED" &&
      data.integrity.integrityValid === true
    ) {
      errors.push("blocked_state_with_valid_integrity");
    }

    if (
      Number.isInteger(data.integrity.historyEvents) &&
      data.integrity.historyEvents < 0
    ) {
      errors.push("invalid_history_events");
    }
  }

  if (!isObject(data.source)) {
    errors.push("source_missing");
  } else {
    checks.push("source_object");

    const sourceKeys = [
      "history",
      "historyVerify",
      "analysis",
      "analysisVerify",
      "chainVerify",
    ];

    for (const key of sourceKeys) {
      if (!isObject(data.source[key])) {
        errors.push(`source_${key}_missing`);
        continue;
      }

      if (
        data.source[key].exists === true &&
        !isSha256(data.source[key].sha256)
      ) {
        errors.push(`source_${key}_invalid_sha256`);
      }
    }
  }

  if (!isObject(data.policy)) {
    errors.push("policy_missing");
  } else {
    if (data.policy.readOnly !== true) {
      errors.push("policy_not_read_only");
    }

    if (data.policy.failClosed !== true) {
      errors.push("policy_not_fail_closed");
    }

    if (data.policy.post !== "NOT_PERFORMED") {
      errors.push("policy_post_violation");
    }

    if (data.policy.wallet !== "NOT_USED") {
      errors.push("policy_wallet_violation");
    }

    if (data.policy.signing !== "NOT_PERFORMED") {
      errors.push("policy_signing_violation");
    }

    if (data.policy.broadcast !== "NOT_PERFORMED") {
      errors.push("policy_broadcast_violation");
    }

    if (data.policy.submission !== "NOT_PERFORMED") {
      errors.push("policy_submission_violation");
    }

    checks.push("policy");
  }

  const state =
    errors.length === 0
      ? "VERIFIED_READ_ONLY"
      : "BLOCKED";

  return {
    state,
    errors,
    checks,
  };
}

function writeReport(report, auditSha256, verification) {
  const output = {
    version: VERSION,
    generatedAt: new Date().toISOString(),

    mode: "READ_ONLY",
    state: verification.state,
    sourceState:
      isObject(report.value)
        ? report.value.state || null
        : null,

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
      auditFile: AUDIT_FILE,
      auditSha256,
    },

    verification: {
      valid: verification.state === "VERIFIED_READ_ONLY",
      checks: verification.checks,
      errors: verification.errors,
      errorCount: verification.errors.length,
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

  fs.mkdirSync(
    path.dirname(OUTPUT_FILE),
    { recursive: true },
  );

  fs.writeFileSync(
    OUTPUT_FILE,
    `${JSON.stringify(output, null, 2)}\n`,
    "utf8",
  );

  return output;
}

function main() {
  console.log(
    "TERMiX AACP PROVIDER WATCH HISTORY INTEGRITY REPORT VERIFIER v1.0",
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log("POST=NOT_PERFORMED");
  console.log("WALLET=NOT_USED");
  console.log("SIGNING=NOT_PERFORMED");
  console.log("BROADCAST=NOT_PERFORMED");
  console.log("SUBMISSION=NOT_PERFORMED");

  const audit = readJson(AUDIT_FILE);

  const verification = verifyAudit(audit);

  const output = writeReport(
    audit,
    audit.sha256,
    verification,
  );

  console.log(`STATE=${output.state}`);
  console.log(
    `AUDIT_EXISTS=${audit.exists}`,
  );
  console.log(
    `CHECKS=${output.verification.checks.length}`,
  );
  console.log(
    `ERRORS=${output.verification.errorCount}`,
  );
  console.log("EXECUTION_AUTHORIZED=false");
  console.log(`REPORT=${OUTPUT_FILE}`);
}

main();
