import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";

const OUTPUT_DIR =
  process.env.AACP_OUTPUT_DIR ||
  path.join(process.cwd(), "provider-output", "aacp-observer");

const MANIFEST_FILE =
  path.join(
    OUTPUT_DIR,
    "latest-provider-evidence-manifest.json"
  );

const MANIFEST_VERIFY_FILE =
  path.join(
    OUTPUT_DIR,
    "latest-provider-evidence-manifest-verify.json"
  );

const AUDIT_FILE =
  path.join(
    OUTPUT_DIR,
    "latest-provider-evidence-manifest-audit.json"
  );

const OUTPUT_FILE =
  path.join(
    OUTPUT_DIR,
    "latest-provider-evidence-manifest-audit-verify.json"
  );

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const EXPECTED_FILES = [
  "latest-provider-watch-history.json",
  "latest-provider-watch-history-verify.json",
  "latest-provider-watch-history-analysis.json",
  "latest-provider-watch-history-analysis-verify.json",
  "latest-provider-watch-history-chain-verify.json",
  "latest-provider-watch-history-integrity-audit.json",
  "latest-provider-watch-history-integrity-audit-verify.json",
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

function isNonNegativeInteger(value) {
  return Number.isInteger(value) && value >= 0;
}

function isSha256(value) {
  return (
    typeof value === "string" &&
    /^[a-f0-9]{64}$/i.test(value)
  );
}

function isTimestamp(value) {
  if (typeof value !== "string") {
    return false;
  }

  return Number.isFinite(Date.parse(value));
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

function safeFlags(value) {
  if (!isObject(value)) {
    return false;
  }

  return SAFETY_FIELDS.every(
    (field) => value[field] === false
  );
}

function verifyPolicy(policy, errors, prefix) {
  if (!isObject(policy)) {
    errors.push(`${prefix}_INVALID`);
    return;
  }

  if (policy.readOnly !== true) {
    errors.push(`${prefix}_READ_ONLY_INVALID`);
  }

  if (policy.failClosed !== true) {
    errors.push(`${prefix}_FAIL_CLOSED_INVALID`);
  }

  if (policy.post !== POLICY.post) {
    errors.push(`${prefix}_POST_INVALID`);
  }

  if (policy.wallet !== POLICY.wallet) {
    errors.push(`${prefix}_WALLET_INVALID`);
  }

  if (policy.signing !== POLICY.signing) {
    errors.push(`${prefix}_SIGNING_INVALID`);
  }

  if (policy.broadcast !== POLICY.broadcast) {
    errors.push(`${prefix}_BROADCAST_INVALID`);
  }

  if (policy.submission !== POLICY.submission) {
    errors.push(`${prefix}_SUBMISSION_INVALID`);
  }
}

function verifySafety(report, errors, prefix) {
  if (report.executionAuthorized !== false) {
    errors.push(
      `${prefix}_EXECUTION_AUTHORIZED`
    );
  }

  if (!safeFlags(report.safety)) {
    errors.push(
      `${prefix}_FLAGS_INVALID`
    );
  }

  if (!safeFlags(report.sideEffects)) {
    errors.push(
      `${prefix}_SIDE_EFFECT_FLAGS_INVALID`
    );
  }
}

function verifyManifest(manifest, errors) {
  if (!isObject(manifest)) {
    errors.push("MANIFEST_INVALID_ROOT");
    return;
  }

  if (manifest.version !== VERSION) {
    errors.push("MANIFEST_INVALID_VERSION");
  }

  if (
    manifest.type !==
    "AACP_PROVIDER_EVIDENCE_MANIFEST"
  ) {
    errors.push("MANIFEST_INVALID_TYPE");
  }

  if (!isTimestamp(manifest.generatedAt)) {
    errors.push("MANIFEST_INVALID_TIMESTAMP");
  }

  if (!ALLOWED_STATES.has(manifest.state)) {
    errors.push("MANIFEST_INVALID_STATE");
  }

  if (
    !ALLOWED_STATES.has(
      manifest.sourceState
    )
  ) {
    errors.push(
      "MANIFEST_INVALID_SOURCE_STATE"
    );
  }

  if (
    ALLOWED_STATES.has(manifest.state) &&
    ALLOWED_STATES.has(manifest.sourceState) &&
    manifest.state !== manifest.sourceState
  ) {
    errors.push(
      "MANIFEST_STATE_SOURCE_MISMATCH"
    );
  }

  if (manifest.mode !== "READ_ONLY") {
    errors.push("MANIFEST_MODE_INVALID");
  }

  verifySafety(
    manifest,
    errors,
    "MANIFEST_SAFETY"
  );

  verifyPolicy(
    manifest.policy,
    errors,
    "MANIFEST_POLICY"
  );

  if (!isObject(manifest.artifacts)) {
    errors.push(
      "MANIFEST_ARTIFACTS_INVALID"
    );
    return;
  }

  if (
    !isNonNegativeInteger(
      manifest.artifacts.expected
    ) ||
    manifest.artifacts.expected !==
      EXPECTED_FILES.length
  ) {
    errors.push(
      "MANIFEST_EXPECTED_COUNT_INVALID"
    );
  }

  if (
    !isNonNegativeInteger(
      manifest.artifacts.present
    )
  ) {
    errors.push(
      "MANIFEST_PRESENT_COUNT_INVALID"
    );
  }

  if (
    !isNonNegativeInteger(
      manifest.artifacts.missing
    )
  ) {
    errors.push(
      "MANIFEST_MISSING_COUNT_INVALID"
    );
  }

  if (
    isNonNegativeInteger(
      manifest.artifacts.present
    ) &&
    isNonNegativeInteger(
      manifest.artifacts.missing
    ) &&
    manifest.artifacts.present +
      manifest.artifacts.missing !==
      EXPECTED_FILES.length
  ) {
    errors.push(
      "MANIFEST_ARTIFACT_TOTAL_INVALID"
    );
  }

  if (
    !Array.isArray(
      manifest.artifacts.files
    )
  ) {
    errors.push(
      "MANIFEST_ARTIFACT_FILES_INVALID"
    );
  } else {
    const names = new Set(
      manifest.artifacts.files
        .filter(isObject)
        .map((entry) => entry.file)
        .filter(
          (value) =>
            typeof value === "string"
        )
    );

    for (const expected of EXPECTED_FILES) {
      if (!names.has(expected)) {
        errors.push(
          `MANIFEST_MISSING_ENTRY:${expected}`
        );
      }
    }
  }

  if (!isObject(manifest.states)) {
    errors.push(
      "MANIFEST_STATES_INVALID"
    );
  }

  if (
    !isObject(manifest.consistency)
  ) {
    errors.push(
      "MANIFEST_CONSISTENCY_INVALID"
    );
  }
}

function verifyManifestVerifier(
  report,
  errors
) {
  if (!isObject(report)) {
    errors.push(
      "MANIFEST_VERIFY_INVALID_ROOT"
    );
    return;
  }

  if (report.version !== VERSION) {
    errors.push(
      "MANIFEST_VERIFY_INVALID_VERSION"
    );
  }

  if (
    report.type !==
    "AACP_PROVIDER_EVIDENCE_MANIFEST_VERIFY"
  ) {
    errors.push(
      "MANIFEST_VERIFY_INVALID_TYPE"
    );
  }

  if (!isTimestamp(report.generatedAt)) {
    errors.push(
      "MANIFEST_VERIFY_INVALID_TIMESTAMP"
    );
  }

  if (
    !ALLOWED_STATES.has(report.state)
  ) {
    errors.push(
      "MANIFEST_VERIFY_INVALID_STATE"
    );
  }

  if (
    report.sourceState !==
    report.state
  ) {
    errors.push(
      "MANIFEST_VERIFY_SOURCE_STATE_MISMATCH"
    );
  }

  if (report.mode !== "READ_ONLY") {
    errors.push(
      "MANIFEST_VERIFY_MODE_INVALID"
    );
  }

  verifySafety(
    report,
    errors,
    "MANIFEST_VERIFY_SAFETY"
  );

  verifyPolicy(
    report.policy,
    errors,
    "MANIFEST_VERIFY_POLICY"
  );

  if (!isObject(report.source)) {
    errors.push(
      "MANIFEST_VERIFY_SOURCE_INVALID"
    );
  } else {
    if (
      report.source.file !==
      MANIFEST_FILE
    ) {
      errors.push(
        "MANIFEST_VERIFY_SOURCE_FILE_INVALID"
      );
    }

    if (report.source.exists !== true) {
      errors.push(
        "MANIFEST_VERIFY_SOURCE_MISSING"
      );
    }

    if (
      !isSha256(
        report.source.sha256
      )
    ) {
      errors.push(
        "MANIFEST_VERIFY_SOURCE_SHA256_INVALID"
      );
    }
  }

  if (
    !isObject(report.verification)
  ) {
    errors.push(
      "MANIFEST_VERIFY_VERIFICATION_INVALID"
    );
    return;
  }

  if (
    !isBoolean(
      report.verification.valid
    )
  ) {
    errors.push(
      "MANIFEST_VERIFY_VALID_INVALID"
    );
  }

  if (
    !Array.isArray(
      report.verification.errors
    )
  ) {
    errors.push(
      "MANIFEST_VERIFY_ERRORS_INVALID"
    );
  }

  if (
    !isNonNegativeInteger(
      report.verification.errorCount
    )
  ) {
    errors.push(
      "MANIFEST_VERIFY_ERROR_COUNT_INVALID"
    );
  }

  if (
    Array.isArray(
      report.verification.errors
    ) &&
    isNonNegativeInteger(
      report.verification.errorCount
    ) &&
    report.verification.errorCount !==
      report.verification.errors.length
  ) {
    errors.push(
      "MANIFEST_VERIFY_ERROR_COUNT_MISMATCH"
    );
  }

  if (
    report.state ===
      "VERIFIED_READ_ONLY" &&
    report.verification.valid !== true
  ) {
    errors.push(
      "MANIFEST_VERIFY_VERIFIED_NOT_VALID"
    );
  }

  if (
    report.state === "INCOMPLETE" &&
    Array.isArray(
      report.verification.errors
    ) &&
    report.verification.errors.length !== 0
  ) {
    errors.push(
      "MANIFEST_VERIFY_INCOMPLETE_HAS_ERRORS"
    );
  }
}

function verifyAudit(
  audit,
  errors
) {
  if (!isObject(audit)) {
    errors.push(
      "AUDIT_INVALID_ROOT"
    );
    return;
  }

  if (audit.version !== VERSION) {
    errors.push(
      "AUDIT_INVALID_VERSION"
    );
  }

  if (
    audit.type !==
    "AACP_PROVIDER_EVIDENCE_MANIFEST_AUDIT"
  ) {
    errors.push(
      "AUDIT_INVALID_TYPE"
    );
  }

  if (!isTimestamp(audit.generatedAt)) {
    errors.push(
      "AUDIT_INVALID_TIMESTAMP"
    );
  }

  if (!ALLOWED_STATES.has(audit.state)) {
    errors.push(
      "AUDIT_INVALID_STATE"
    );
  }

  if (
    audit.sourceState !==
    audit.state
  ) {
    errors.push(
      "AUDIT_SOURCE_STATE_MISMATCH"
    );
  }

  if (audit.mode !== "READ_ONLY") {
    errors.push(
      "AUDIT_MODE_INVALID"
    );
  }

  verifySafety(
    audit,
    errors,
    "AUDIT_SAFETY"
  );

  verifyPolicy(
    audit.policy,
    errors,
    "AUDIT_POLICY"
  );

  if (!isObject(audit.sources)) {
    errors.push(
      "AUDIT_SOURCES_INVALID"
    );
    return;
  }

  if (
    !isObject(audit.sources.manifest)
  ) {
    errors.push(
      "AUDIT_MANIFEST_SOURCE_INVALID"
    );
  } else {
    if (
      audit.sources.manifest.file !==
      MANIFEST_FILE
    ) {
      errors.push(
        "AUDIT_MANIFEST_FILE_INVALID"
      );
    }

    if (
      audit.sources.manifest.exists !==
      true
    ) {
      errors.push(
        "AUDIT_MANIFEST_MISSING"
      );
    }

    if (
      !isSha256(
        audit.sources.manifest.sha256
      )
    ) {
      errors.push(
        "AUDIT_MANIFEST_SHA256_INVALID"
      );
    }
  }

  if (
    !isObject(audit.sources.verifier)
  ) {
    errors.push(
      "AUDIT_VERIFIER_SOURCE_INVALID"
    );
  } else {
    if (
      audit.sources.verifier.file !==
      MANIFEST_VERIFY_FILE
    ) {
      errors.push(
        "AUDIT_VERIFIER_FILE_INVALID"
      );
    }

    if (
      audit.sources.verifier.exists !==
      true
    ) {
      errors.push(
        "AUDIT_VERIFIER_MISSING"
      );
    }

    if (
      !isSha256(
        audit.sources.verifier.sha256
      )
    ) {
      errors.push(
        "AUDIT_VERIFIER_SHA256_INVALID"
      );
    }
  }

  if (!isObject(audit.metrics)) {
    errors.push(
      "AUDIT_METRICS_INVALID"
    );
    return;
  }

  if (
    audit.metrics.manifestExists !==
    true
  ) {
    errors.push(
      "AUDIT_METRIC_MANIFEST_MISSING"
    );
  }

  if (
    audit.metrics.verifierExists !==
    true
  ) {
    errors.push(
      "AUDIT_METRIC_VERIFIER_MISSING"
    );
  }

  if (
    !ALLOWED_STATES.has(
      audit.metrics.manifestState
    )
  ) {
    errors.push(
      "AUDIT_METRIC_MANIFEST_STATE_INVALID"
    );
  }

  if (
    !ALLOWED_STATES.has(
      audit.metrics.verifierState
    )
  ) {
    errors.push(
      "AUDIT_METRIC_VERIFIER_STATE_INVALID"
    );
  }

  if (
    audit.metrics.manifestState !==
    audit.metrics.verifierState
  ) {
    errors.push(
      "AUDIT_METRIC_STATE_MISMATCH"
    );
  }

  if (
    !isSha256(
      audit.metrics.manifestSha256
    )
  ) {
    errors.push(
      "AUDIT_METRIC_MANIFEST_SHA256_INVALID"
    );
  }

  if (
    !isSha256(
      audit.metrics.verifierSha256
    )
  ) {
    errors.push(
      "AUDIT_METRIC_VERIFIER_SHA256_INVALID"
    );
  }

  if (
    !isNonNegativeInteger(
      audit.metrics.expectedArtifacts
    ) ||
    audit.metrics.expectedArtifacts !==
      EXPECTED_FILES.length
  ) {
    errors.push(
      "AUDIT_METRIC_EXPECTED_INVALID"
    );
  }

  if (
    !isNonNegativeInteger(
      audit.metrics.presentArtifacts
    )
  ) {
    errors.push(
      "AUDIT_METRIC_PRESENT_INVALID"
    );
  }

  if (
    !isNonNegativeInteger(
      audit.metrics.missingArtifacts
    )
  ) {
    errors.push(
      "AUDIT_METRIC_MISSING_INVALID"
    );
  }

  if (
    isNonNegativeInteger(
      audit.metrics.presentArtifacts
    ) &&
    isNonNegativeInteger(
      audit.metrics.missingArtifacts
    ) &&
    audit.metrics.presentArtifacts +
      audit.metrics.missingArtifacts !==
      EXPECTED_FILES.length
  ) {
    errors.push(
      "AUDIT_METRIC_TOTAL_INVALID"
    );
  }

  if (
    audit.metrics.verifierValid !==
      true &&
    audit.metrics.verifierState ===
      "VERIFIED_READ_ONLY"
  ) {
    errors.push(
      "AUDIT_METRIC_VERIFIER_NOT_VALID"
    );
  }

  if (
    audit.metrics.manifestState ===
      "INCOMPLETE" &&
    audit.metrics.verifierState !==
      "INCOMPLETE"
  ) {
    errors.push(
      "AUDIT_METRIC_INCOMPLETE_NOT_PRESERVED"
    );
  }
}

function crossCheck(
  manifest,
  verifier,
  audit,
  manifestSha,
  verifierSha,
  errors
) {
  if (
    verifier.source?.sha256 !==
    manifestSha
  ) {
    errors.push(
      "VERIFY_MANIFEST_SHA256_MISMATCH"
    );
  }

  if (
    audit.sources?.manifest?.sha256 !==
    manifestSha
  ) {
    errors.push(
      "AUDIT_MANIFEST_SHA256_MISMATCH"
    );
  }

  if (
    audit.sources?.verifier?.sha256 !==
    verifierSha
  ) {
    errors.push(
      "AUDIT_VERIFIER_SHA256_MISMATCH"
    );
  }

  if (
    audit.metrics?.manifestSha256 !==
    manifestSha
  ) {
    errors.push(
      "AUDIT_METRIC_MANIFEST_SHA256_MISMATCH"
    );
  }

  if (
    audit.metrics?.verifierSha256 !==
    verifierSha
  ) {
    errors.push(
      "AUDIT_METRIC_VERIFIER_SHA256_MISMATCH"
    );
  }

  if (
    manifest.state !==
    verifier.state ||
    verifier.state !==
    audit.state
  ) {
    errors.push(
      "STATE_CHAIN_MISMATCH"
    );
  }

  if (
    manifest.sourceState !==
    verifier.sourceState ||
    verifier.sourceState !==
    audit.sourceState
  ) {
    errors.push(
      "SOURCE_STATE_CHAIN_MISMATCH"
    );
  }

  if (
    manifest.mode !== "READ_ONLY" ||
    verifier.mode !== "READ_ONLY" ||
    audit.mode !== "READ_ONLY"
  ) {
    errors.push(
      "MODE_CHAIN_INVALID"
    );
  }

  if (
    manifest.executionAuthorized !== false ||
    verifier.executionAuthorized !== false ||
    audit.executionAuthorized !== false
  ) {
    errors.push(
      "EXECUTION_AUTHORIZED_CHAIN_INVALID"
    );
  }

  if (
    manifest.state ===
      "VERIFIED_READ_ONLY" &&
    (
      verifier.state !==
        "VERIFIED_READ_ONLY" ||
      audit.state !==
        "VERIFIED_READ_ONLY"
    )
  ) {
    errors.push(
      "VERIFIED_STATE_NOT_PRESERVED"
    );
  }

  if (
    manifest.state === "INCOMPLETE" &&
    (
      verifier.state !== "INCOMPLETE" ||
      audit.state !== "INCOMPLETE"
    )
  ) {
    errors.push(
      "INCOMPLETE_STATE_NOT_PRESERVED"
    );
  }

  if (
    manifest.artifacts?.expected !==
    audit.metrics?.expectedArtifacts
  ) {
    errors.push(
      "EXPECTED_ARTIFACT_COUNT_CHAIN_MISMATCH"
    );
  }

  if (
    manifest.artifacts?.present !==
    audit.metrics?.presentArtifacts
  ) {
    errors.push(
      "PRESENT_ARTIFACT_COUNT_CHAIN_MISMATCH"
    );
  }

  if (
    manifest.artifacts?.missing !==
    audit.metrics?.missingArtifacts
  ) {
    errors.push(
      "MISSING_ARTIFACT_COUNT_CHAIN_MISMATCH"
    );
  }
}

function buildReport(
  state,
  manifestSha,
  verifierSha,
  auditSha,
  errors,
  checks
) {
  return {
    version: VERSION,
    type:
      "AACP_PROVIDER_EVIDENCE_MANIFEST_AUDIT_VERIFY",
    generatedAt:
      new Date().toISOString(),
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

    sources: {
      manifest: {
        file: MANIFEST_FILE,
        exists:
          fs.existsSync(MANIFEST_FILE),
        sha256: manifestSha,
      },
      verifier: {
        file: MANIFEST_VERIFY_FILE,
        exists:
          fs.existsSync(
            MANIFEST_VERIFY_FILE
          ),
        sha256: verifierSha,
      },
      audit: {
        file: AUDIT_FILE,
        exists:
          fs.existsSync(AUDIT_FILE),
        sha256: auditSha,
      },
    },

    verification: {
      valid:
        state === "VERIFIED_READ_ONLY",
      checks,
      errors,
      errorCount: errors.length,
    },

    policy: POLICY,
  };
}

function writeReport(report) {
  fs.mkdirSync(OUTPUT_DIR, {
    recursive: true,
  });

  fs.writeFileSync(
    OUTPUT_FILE,
    JSON.stringify(
      report,
      null,
      2
    ) + "\n",
    "utf8"
  );
}

function printReport(report) {
  console.log(
    "TERMiX AACP PROVIDER EVIDENCE MANIFEST AUDIT VERIFY v1.0"
  );
  console.log(
    "READ ONLY / FAIL CLOSED"
  );
  console.log(
    "=============================================="
  );
  console.log(
    `STATE: ${report.state}`
  );
  console.log(
    `SOURCE STATE: ${report.sourceState}`
  );
  console.log(
    `ERRORS: ${report.errors?.length ?? report.verification?.errorCount ?? 0}`
  );
  console.log(
    "EXECUTION AUTHORIZED: false"
  );
  console.log(
    "POST: NOT_PERFORMED"
  );
  console.log(
    "WALLET: NOT_USED"
  );
  console.log(
    "SIGNING: NOT_PERFORMED"
  );
  console.log(
    "BROADCAST: NOT_PERFORMED"
  );
  console.log(
    "SUBMISSION: NOT_PERFORMED"
  );
  console.log(
    `REPORT: ${OUTPUT_FILE}`
  );
}

function main() {
  const errors = [];
  const checks = [];

  if (!fs.existsSync(AUDIT_FILE)) {
    const report = buildReport(
      "INCOMPLETE",
      null,
      null,
      null,
      [],
      ["MISSING_AUDIT"]
    );

    writeReport(report);
    printReport(report);
    return report;
  }

  let manifest = null;
  let verifier = null;
  let audit = null;

  let manifestSha = null;
  let verifierSha = null;
  let auditSha = null;

  try {
    manifestSha =
      sha256File(MANIFEST_FILE);
    manifest = readJson(MANIFEST_FILE);
    verifyManifest(
      manifest,
      errors
    );
    checks.push(
      "MANIFEST_VALIDATED"
    );
  } catch (error) {
    errors.push(
      `MANIFEST_READ_ERROR:${
        error?.message ??
        String(error)
      }`
    );
  }

  try {
    verifierSha =
      sha256File(
        MANIFEST_VERIFY_FILE
      );
    verifier =
      readJson(
        MANIFEST_VERIFY_FILE
      );
    verifyManifestVerifier(
      verifier,
      errors
    );
    checks.push(
      "MANIFEST_VERIFY_VALIDATED"
    );
  } catch (error) {
    errors.push(
      `MANIFEST_VERIFY_READ_ERROR:${
        error?.message ??
        String(error)
      }`
    );
  }

  try {
    auditSha =
      sha256File(AUDIT_FILE);
    audit =
      readJson(AUDIT_FILE);
    verifyAudit(
      audit,
      errors
    );
    checks.push(
      "AUDIT_VALIDATED"
 );
  } catch (error) {
    errors.push(
      `AUDIT_READ_ERROR:${
        error?.message ??
        String(error)
      }`
    );
  }

  if (
    manifest &&
    verifier &&
    audit &&
    manifestSha &&
    verifierSha
  ) {
    crossCheck(
      manifest,
      verifier,
      audit,
      manifestSha,
      verifierSha,
      errors
    );

    if (errors.length === 0) {
      checks.push(
        "CROSS_LAYER_VALID"
      );
    }
  }

  let state;

  if (errors.length > 0) {
    state = "BLOCKED";
  } else if (
    manifest?.state === "INCOMPLETE" ||
    verifier?.state === "INCOMPLETE" ||
    audit?.state === "INCOMPLETE"
  ) {
    state = "INCOMPLETE";
  } else {
    state = "VERIFIED_READ_ONLY";
  }

  const report = buildReport(
    state,
    manifestSha,
    verifierSha,
    auditSha,
    errors,
    checks
  );

  writeReport(report);
  printReport(report);

  if (state === "BLOCKED") {
    process.exitCode = 1;
  }

  return report;
}

main();
