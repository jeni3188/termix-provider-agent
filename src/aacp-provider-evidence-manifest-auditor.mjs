import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";

const OUTPUT_DIR =
  process.env.AACP_OUTPUT_DIR ||
  path.join(process.cwd(), "provider-output", "aacp-observer");

const MANIFEST_FILE =
  path.join(OUTPUT_DIR, "latest-provider-evidence-manifest.json");

const VERIFY_FILE =
  path.join(
    OUTPUT_DIR,
    "latest-provider-evidence-manifest-verify.json"
  );

const OUTPUT_FILE =
  path.join(
    OUTPUT_DIR,
    "latest-provider-evidence-manifest-audit.json"
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
  return value !== null &&
    typeof value === "object" &&
    !Array.isArray(value);
}

function isBoolean(value) {
  return typeof value === "boolean";
}

function isNonNegativeInteger(value) {
  return Number.isInteger(value) && value >= 0;
}

function isSha256(value) {
  return typeof value === "string" &&
    /^[a-f0-9]{64}$/i.test(value);
}

function isTimestamp(value) {
  if (typeof value !== "string") return false;
  const time = Date.parse(value);
  return Number.isFinite(time);
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

function safeFlags(object) {
  if (!isObject(object)) return false;

  return SAFETY_FIELDS.every(
    (field) => object[field] === false
  );
}

function verifyPolicy(policy, errors, prefix = "POLICY") {
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

function verifySafety(report, errors, prefix = "SAFETY") {
  if (report.executionAuthorized !== false) {
    errors.push(`${prefix}_EXECUTION_AUTHORIZED`);
  }

  if (!safeFlags(report.safety)) {
    errors.push(`${prefix}_FLAGS_INVALID`);
  }

  if (!safeFlags(report.sideEffects)) {
    errors.push(`${prefix}_SIDE_EFFECT_FLAGS_INVALID`);
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

  if (manifest.type !== "AACP_PROVIDER_EVIDENCE_MANIFEST") {
    errors.push("MANIFEST_INVALID_TYPE");
  }

  if (!isTimestamp(manifest.generatedAt)) {
    errors.push("MANIFEST_INVALID_TIMESTAMP");
  }

  if (!ALLOWED_STATES.has(manifest.state)) {
    errors.push("MANIFEST_INVALID_STATE");
  }

  if (!ALLOWED_STATES.has(manifest.sourceState)) {
    errors.push("MANIFEST_INVALID_SOURCE_STATE");
  }

  if (
    ALLOWED_STATES.has(manifest.state) &&
    ALLOWED_STATES.has(manifest.sourceState) &&
    manifest.state !== manifest.sourceState
  ) {
    errors.push("MANIFEST_STATE_SOURCE_MISMATCH");
  }

  verifySafety(manifest, errors, "MANIFEST_SAFETY");

  verifyPolicy(manifest.policy, errors, "MANIFEST_POLICY");

  if (!isObject(manifest.artifacts)) {
    errors.push("MANIFEST_ARTIFACTS_INVALID");
    return;
  }

  if (
    !isNonNegativeInteger(manifest.artifacts.expected) ||
    manifest.artifacts.expected !== EXPECTED_FILES.length
  ) {
    errors.push("MANIFEST_EXPECTED_COUNT_INVALID");
  }

  if (!isNonNegativeInteger(manifest.artifacts.present)) {
    errors.push("MANIFEST_PRESENT_COUNT_INVALID");
  }

  if (!isNonNegativeInteger(manifest.artifacts.missing)) {
    errors.push("MANIFEST_MISSING_COUNT_INVALID");
  }

  if (
    isNonNegativeInteger(manifest.artifacts.present) &&
    isNonNegativeInteger(manifest.artifacts.missing) &&
    manifest.artifacts.present +
      manifest.artifacts.missing !==
      EXPECTED_FILES.length
  ) {
    errors.push("MANIFEST_ARTIFACT_TOTAL_INVALID");
  }

  if (!Array.isArray(manifest.artifacts.files)) {
    errors.push("MANIFEST_ARTIFACT_FILES_INVALID");
  } else {
    const names = new Set(
      manifest.artifacts.files
        .filter(isObject)
        .map((file) => file.file)
        .filter((file) => typeof file === "string")
    );

    for (const expected of EXPECTED_FILES) {
      if (!names.has(expected)) {
        errors.push(`MANIFEST_MISSING_ENTRY:${expected}`);
      }
    }
  }

  if (!isObject(manifest.states)) {
    errors.push("MANIFEST_STATES_INVALID");
  }

  if (!isObject(manifest.consistency)) {
    errors.push("MANIFEST_CONSISTENCY_INVALID");
  }
}

function verifyVerifierReport(report, errors) {
  if (!isObject(report)) {
    errors.push("VERIFY_INVALID_ROOT");
    return;
  }

  if (report.version !== VERSION) {
    errors.push("VERIFY_INVALID_VERSION");
  }

  if (
    report.type !==
    "AACP_PROVIDER_EVIDENCE_MANIFEST_VERIFY"
  ) {
    errors.push("VERIFY_INVALID_TYPE");
  }

  if (!isTimestamp(report.generatedAt)) {
    errors.push("VERIFY_INVALID_TIMESTAMP");
  }

  if (!ALLOWED_STATES.has(report.state)) {
    errors.push("VERIFY_INVALID_STATE");
  }

  if (
    report.sourceState !==
    report.state
  ) {
    errors.push("VERIFY_SOURCE_STATE_MISMATCH");
  }

  if (report.mode !== "READ_ONLY") {
    errors.push("VERIFY_MODE_INVALID");
  }

  verifySafety(report, errors, "VERIFY_SAFETY");

  verifyPolicy(report.policy, errors, "VERIFY_POLICY");

  if (!isObject(report.source)) {
    errors.push("VERIFY_SOURCE_INVALID");
  } else {
    if (
      typeof report.source.file !== "string"
    ) {
      errors.push("VERIFY_SOURCE_FILE_INVALID");
    }

    if (
      report.source.exists !== true
    ) {
      errors.push("VERIFY_SOURCE_MISSING");
    }

    if (
      !isSha256(report.source.sha256)
    ) {
      errors.push("VERIFY_SOURCE_SHA256_INVALID");
    }
  }

  if (!isObject(report.verification)) {
    errors.push("VERIFY_VERIFICATION_INVALID");
    return;
  }

  if (
    !isBoolean(report.verification.valid)
  ) {
    errors.push("VERIFY_VALID_FLAG_INVALID");
  }

  if (
    !Array.isArray(report.verification.errors)
  ) {
    errors.push("VERIFY_ERRORS_INVALID");
  }

  if (
    !isNonNegativeInteger(
      report.verification.errorCount
    )
  ) {
    errors.push("VERIFY_ERROR_COUNT_INVALID");
  }

  if (
    Array.isArray(report.verification.errors) &&
    isNonNegativeInteger(
      report.verification.errorCount
    ) &&
    report.verification.errorCount !==
      report.verification.errors.length
  ) {
    errors.push("VERIFY_ERROR_COUNT_MISMATCH");
  }

  if (
    report.state === "VERIFIED_READ_ONLY" &&
    report.verification.valid !== true
  ) {
    errors.push("VERIFY_VERIFIED_NOT_VALID");
  }

  if (
    report.state === "INCOMPLETE" &&
    report.verification.errors.length !== 0
  ) {
    errors.push("VERIFY_INCOMPLETE_HAS_ERRORS");
  }
}

function crossCheck(
  manifest,
  verifier,
  manifestSha,
  errors
) {
  if (
    verifier.source?.sha256 !==
    manifestSha
  ) {
    errors.push("SOURCE_SHA256_MISMATCH");
  }

  if (
    verifier.source?.file !==
    MANIFEST_FILE
  ) {
    errors.push("SOURCE_FILE_MISMATCH");
  }

  if (
    verifier.source?.exists !== true
  ) {
    errors.push("SOURCE_NOT_PRESENT");
  }

  if (
    manifest.mode !== "READ_ONLY"
  ) {
    errors.push("MANIFEST_MODE_NOT_READ_ONLY");
  }

  if (
    manifest.executionAuthorized !== false
  ) {
    errors.push("MANIFEST_EXECUTION_AUTHORIZED");
  }

  if (
    verifier.executionAuthorized !== false
  ) {
    errors.push("VERIFY_EXECUTION_AUTHORIZED");
  }

  if (
    manifest.state !==
    verifier.state
  ) {
    errors.push("STATE_CROSS_LAYER_MISMATCH");
  }

  if (
    manifest.sourceState !==
    verifier.sourceState
  ) {
    errors.push("SOURCE_STATE_CROSS_LAYER_MISMATCH");
  }

  if (
    manifest.state === "VERIFIED_READ_ONLY" &&
    verifier.state !== "VERIFIED_READ_ONLY"
  ) {
    errors.push("VERIFIED_STATE_NOT_PRESERVED");
  }

  if (
    manifest.state === "INCOMPLETE" &&
    verifier.state !== "INCOMPLETE"
  ) {
    errors.push("INCOMPLETE_STATE_NOT_PRESERVED");
  }
}

function buildAudit(
  state,
  sourceManifest,
  sourceVerifier,
  errors,
  metrics
) {
  return {
    version: VERSION,
    type: "AACP_PROVIDER_EVIDENCE_MANIFEST_AUDIT",
    generatedAt: new Date().toISOString(),
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
        exists: fs.existsSync(MANIFEST_FILE),
        sha256: sourceManifest,
      },
      verifier: {
        file: VERIFY_FILE,
        exists: fs.existsSync(VERIFY_FILE),
        sha256: sourceVerifier,
      },
    },

    metrics,

    errors,

    policy: POLICY,
  };
}

function writeAudit(report) {
  fs.mkdirSync(OUTPUT_DIR, {
    recursive: true,
  });

  fs.writeFileSync(
    OUTPUT_FILE,
    JSON.stringify(report, null, 2) +
      "\n",
    "utf8"
  );
}

function main() {
  const errors = [];

  let manifest = null;
  let verifier = null;

  let manifestSha = null;
  let verifierSha = null;

  if (!fs.existsSync(MANIFEST_FILE)) {
    const report = buildAudit(
      "INCOMPLETE",
      null,
      null,
      ["MISSING_MANIFEST"],
      {
        manifestExists: false,
        verifierExists: fs.existsSync(
          VERIFY_FILE
        ),
      }
    );

    writeAudit(report);

    console.log(
      "TERMiX AACP PROVIDER EVIDENCE MANIFEST AUDIT v1.0"
    );
    console.log(
      "READ ONLY / FAIL CLOSED"
    );
    console.log("STATE: INCOMPLETE");
    console.log(
      "ERRORS: 1"
    );
    console.log(
      `REPORT: ${OUTPUT_FILE}`
    );

    return report;
  }

  try {
    manifestSha =
      sha256File(MANIFEST_FILE);

    manifest =
      readJson(MANIFEST_FILE);

    verifyManifest(
      manifest,
      errors
    );
  } catch (error) {
    errors.push(
      `MANIFEST_READ_ERROR:${
        error?.message ||
        String(error)
      }`
    );
  }

  if (!fs.existsSync(VERIFY_FILE)) {
    errors.push("MISSING_VERIFIER_REPORT");
  } else {
    try {
      verifierSha =
        sha256File(VERIFY_FILE);

      verifier =
        readJson(VERIFY_FILE);

      verifyVerifierReport(
        verifier,
        errors
      );
    } catch (error) {
      errors.push(
        `VERIFIER_READ_ERROR:${
          error?.message ||
          String(error)
        }`
      );
    }
  }

  if (
    manifest &&
    verifier &&
    manifestSha
  ) {
    crossCheck(
      manifest,
      verifier,
      manifestSha,
      errors
    );
  }

  let state;

  if (errors.length > 0) {
    state = "BLOCKED";
  } else if (
    manifest.state ===
      "INCOMPLETE" ||
    verifier.state ===
      "INCOMPLETE"
  ) {
    state = "INCOMPLETE";
  } else {
    state = "VERIFIED_READ_ONLY";
  }

  const metrics = {
    manifestExists: true,
    verifierExists:
      fs.existsSync(VERIFY_FILE),
    manifestState:
      manifest?.state ?? null,
    verifierState:
      verifier?.state ?? null,
    manifestSha256:
      manifestSha,
    verifierSha256:
      verifierSha,
    expectedArtifacts:
      manifest?.artifacts?.expected ??
      null,
    presentArtifacts:
      manifest?.artifacts?.present ??
      null,
    missingArtifacts:
      manifest?.artifacts?.missing ??
      null,
    verifierValid:
      verifier?.verification?.valid ??
      null,
  };

  const report = buildAudit(
    state,
    manifestSha,
    verifierSha,
    errors,
    metrics
  );

  writeAudit(report);

  console.log(
    "TERMiX AACP PROVIDER EVIDENCE MANIFEST AUDIT v1.0"
  );
  console.log(
    "READ ONLY / FAIL CLOSED"
  );
  console.log(
    "=============================================="
  );
  console.log(`STATE: ${report.state}`);
  console.log(
    `ERRORS: ${report.errors.length}`
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

  if (state === "BLOCKED") {
    process.exitCode = 1;
  }

  return report;
}

main();
