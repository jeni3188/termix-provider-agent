import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";
const OUTPUT_DIR =
  process.env.AACP_PROVIDER_OUTPUT_DIR ||
  path.resolve("provider-output/aacp-observer");

const INPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-evidence-manifest.json"
);

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-evidence-manifest-verify.json"
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

const UNSAFE_FIELDS = [
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
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isBoolean(value) {
  return typeof value === "boolean";
}

function isNonNegativeInteger(value) {
  return Number.isInteger(value) && value >= 0;
}

function isSha256(value) {
  return typeof value === "string" && /^[a-f0-9]{64}$/i.test(value);
}

function isTimestamp(value) {
  if (typeof value !== "string") return false;
  return !Number.isNaN(Date.parse(value));
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

function unsafeObjectSafe(object) {
  if (!isObject(object)) return false;

  return UNSAFE_FIELDS.every(
    (field) => object[field] === false
  );
}

function verifyPolicy(policy, errors) {
  if (!isObject(policy)) {
    errors.push("INVALID_POLICY");
    return;
  }

  if (policy.readOnly !== true) errors.push("POLICY_READ_ONLY_INVALID");
  if (policy.failClosed !== true) errors.push("POLICY_FAIL_CLOSED_INVALID");
  if (policy.post !== "NOT_PERFORMED") errors.push("POLICY_POST_INVALID");
  if (policy.wallet !== "NOT_USED") errors.push("POLICY_WALLET_INVALID");
  if (policy.signing !== "NOT_PERFORMED") {
    errors.push("POLICY_SIGNING_INVALID");
  }
  if (policy.broadcast !== "NOT_PERFORMED") {
    errors.push("POLICY_BROADCAST_INVALID");
  }
  if (policy.submission !== "NOT_PERFORMED") {
    errors.push("POLICY_SUBMISSION_INVALID");
  }
}

function verifySafety(manifest, errors) {
  if (manifest.mode !== "READ_ONLY") {
    errors.push("MODE_NOT_READ_ONLY");
  }

  if (manifest.executionAuthorized !== false) {
    errors.push("EXECUTION_AUTHORIZED");
  }

  if (!isObject(manifest.safety)) {
    errors.push("INVALID_SAFETY");
  } else if (!unsafeObjectSafe(manifest.safety)) {
    errors.push("UNSAFE_SAFETY_FIELD");
  }

  if (!isObject(manifest.sideEffects)) {
    errors.push("INVALID_SIDE_EFFECTS");
  } else if (!unsafeObjectSafe(manifest.sideEffects)) {
    errors.push("UNSAFE_SIDE_EFFECT_FIELD");
  }

  verifyPolicy(manifest.policy, errors);
}

function verifyArtifacts(manifest, errors) {
  const artifacts = manifest.artifacts;

  if (!isObject(artifacts)) {
    errors.push("INVALID_ARTIFACTS");
    return;
  }

  if (!isNonNegativeInteger(artifacts.expected)) {
    errors.push("INVALID_ARTIFACT_EXPECTED");
  }

  if (!isNonNegativeInteger(artifacts.present)) {
    errors.push("INVALID_ARTIFACT_PRESENT");
  }

  if (!isNonNegativeInteger(artifacts.missing)) {
    errors.push("INVALID_ARTIFACT_MISSING");
  }

  if (!isNonNegativeInteger(artifacts.uniqueSha256)) {
    errors.push("INVALID_ARTIFACT_UNIQUE_SHA256");
  }

  if (!Array.isArray(artifacts.files)) {
    errors.push("INVALID_ARTIFACT_FILES");
    return;
  }

  if (artifacts.files.length !== EXPECTED_FILES.length) {
    errors.push("ARTIFACT_COUNT_MISMATCH");
  }

  const names = new Set();

  for (const file of artifacts.files) {
    if (!isObject(file)) {
      errors.push("INVALID_ARTIFACT_ENTRY");
      continue;
    }

    if (typeof file.file !== "string") {
      errors.push("INVALID_ARTIFACT_FILENAME");
      continue;
    }

    names.add(file.file);

    if (file.exists === true) {
      if (!isNonNegativeInteger(file.sizeBytes)) {
        errors.push(`INVALID_SIZE:${file.file}`);
      }

      if (!isSha256(file.sha256)) {
        errors.push(`INVALID_SHA256:${file.file}`);
      }
    } else if (file.exists === false) {
      if (file.sizeBytes !== null) {
        errors.push(`MISSING_SIZE_NOT_NULL:${file.file}`);
      }

      if (file.sha256 !== null) {
        errors.push(`MISSING_SHA256_NOT_NULL:${file.file}`);
      }
    } else {
      errors.push(`INVALID_EXISTS:${file.file}`);
    }
  }

  for (const expected of EXPECTED_FILES) {
    if (!names.has(expected)) {
      errors.push(`EXPECTED_FILE_NOT_LISTED:${expected}`);
    }
  }

  if (
    isNonNegativeInteger(artifacts.expected) &&
    isNonNegativeInteger(artifacts.present) &&
    isNonNegativeInteger(artifacts.missing) &&
    artifacts.expected !==
      artifacts.present + artifacts.missing
  ) {
    errors.push("ARTIFACT_TOTAL_MISMATCH");
  }

  const presentFiles = artifacts.files.filter(
    (file) => file?.exists === true && isSha256(file.sha256)
  );

  const uniqueHashes = new Set(
    presentFiles.map((file) => file.sha256.toLowerCase())
  );

  if (
    isNonNegativeInteger(artifacts.uniqueSha256) &&
    artifacts.uniqueSha256 !== uniqueHashes.size
  ) {
    errors.push("UNIQUE_SHA256_MISMATCH");
  }

  if (artifacts.missing === 0 && artifacts.present !== EXPECTED_FILES.length) {
    errors.push("COMPLETE_COUNT_MISMATCH");
  }
}

function verifyStates(manifest, errors) {
  if (!isObject(manifest.states)) {
    errors.push("INVALID_STATES");
    return;
  }

  for (const [key, state] of Object.entries(manifest.states)) {
    if (!ALLOWED_STATES.has(state)) {
      errors.push(`INVALID_STATE:${key}`);
    }
  }

  if (
    manifest.state === "VERIFIED_READ_ONLY" &&
    manifest.artifacts?.missing !== 0
  ) {
    errors.push("VERIFIED_WITH_MISSING_ARTIFACTS");
  }

  if (
    manifest.state === "VERIFIED_READ_ONLY" &&
    manifest.artifacts?.present !== EXPECTED_FILES.length
  ) {
    errors.push("VERIFIED_WITH_INCOMPLETE_ARTIFACT_COUNT");
  }

  if (
    manifest.state === "INCOMPLETE" &&
    manifest.artifacts?.missing === 0
  ) {
    errors.push("INCOMPLETE_WITH_NO_MISSING_ARTIFACTS");
  }
}

function verifyConsistency(manifest, errors) {
  if (!isObject(manifest.consistency)) {
    errors.push("INVALID_CONSISTENCY");
    return;
  }

  for (const key of [
    "historyVerify",
    "analysisVerify",
    "integrityVerify",
    "chainConsistent",
  ]) {
    if (!isBoolean(manifest.consistency[key])) {
      errors.push(`INVALID_CONSISTENCY_FLAG:${key}`);
    }
  }

  if (
    manifest.state === "VERIFIED_READ_ONLY" &&
    manifest.consistency.historyVerify !== true
  ) {
    errors.push("HISTORY_VERIFY_NOT_CONSISTENT");
  }

  if (
    manifest.state === "VERIFIED_READ_ONLY" &&
    manifest.consistency.analysisVerify !== true
  ) {
    errors.push("ANALYSIS_VERIFY_NOT_CONSISTENT");
  }

  if (
    manifest.state === "VERIFIED_READ_ONLY" &&
    manifest.consistency.integrityVerify !== true
  ) {
    errors.push("INTEGRITY_VERIFY_NOT_CONSISTENT");
  }

  if (
    manifest.state === "VERIFIED_READ_ONLY" &&
    manifest.consistency.chainConsistent !== true
  ) {
    errors.push("CHAIN_NOT_CONSISTENT");
  }
}

function verifyRoot(manifest, errors) {
  if (!isObject(manifest)) {
    errors.push("INVALID_ROOT");
    return;
  }

  if (manifest.version !== "1.0.0") {
    errors.push("INVALID_VERSION");
  }

  if (manifest.type !== "AACP_PROVIDER_EVIDENCE_MANIFEST") {
    errors.push("INVALID_TYPE");
  }

  if (!isTimestamp(manifest.generatedAt)) {
    errors.push("INVALID_GENERATED_AT");
  }

  if (!ALLOWED_STATES.has(manifest.state)) {
    errors.push("INVALID_STATE");
  }

  if (!ALLOWED_STATES.has(manifest.sourceState)) {
    errors.push("INVALID_SOURCE_STATE");
  }

  if (
    ALLOWED_STATES.has(manifest.state) &&
    ALLOWED_STATES.has(manifest.sourceState) &&
    manifest.state !== manifest.sourceState
  ) {
    errors.push("STATE_SOURCE_STATE_MISMATCH");
  }

  verifySafety(manifest, errors);
  verifyArtifacts(manifest, errors);
  verifyStates(manifest, errors);
  verifyConsistency(manifest, errors);
}

function writeReport(state, sourceSha, errors, manifest) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const report = {
    version: VERSION,
    type: "AACP_PROVIDER_EVIDENCE_MANIFEST_VERIFY",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state,
    sourceState: manifest?.state ?? null,
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

    source: {
      file: INPUT_FILE,
      exists: fs.existsSync(INPUT_FILE),
      sha256: sourceSha,
    },

    verification: {
      valid: state === "VERIFIED_READ_ONLY",
      errors,
      errorCount: errors.length,
    },

    policy: POLICY,
  };

  fs.writeFileSync(
    OUTPUT_FILE,
    JSON.stringify(report, null, 2) + "\n",
    "utf8"
  );

  return report;
}

function main() {
  let manifest = null;
  let sourceSha = null;
  let errors = [];

  if (!fs.existsSync(INPUT_FILE)) {
    const report = writeReport(
      "INCOMPLETE",
      null,
      ["MISSING_MANIFEST"],
      null
    );

    console.log("TERMiX AACP PROVIDER EVIDENCE MANIFEST VERIFY v1.0");
    console.log("READ ONLY / FAIL CLOSED");
    console.log("STATE: INCOMPLETE");
    console.log(`REPORT: ${OUTPUT_FILE}`);
    return report;
  }

  try {
    sourceSha = sha256File(INPUT_FILE);
    manifest = readJson(INPUT_FILE);
    verifyRoot(manifest, errors);
  } catch (error) {
    errors.push(
      `INVALID_JSON:${error?.message || String(error)}`
    );
  }

  let state;

  if (errors.length > 0) {
    state = "BLOCKED";
  } else if (manifest.state === "INCOMPLETE") {
    state = "INCOMPLETE";
  } else {
    state = "VERIFIED_READ_ONLY";
  }

  const report = writeReport(
    state,
    sourceSha,
    errors,
    manifest
  );

  console.log(
    "TERMiX AACP PROVIDER EVIDENCE MANIFEST VERIFY v1.0"
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log("==============================================");
  console.log(`STATE: ${report.state}`);
  console.log(`SOURCE STATE: ${report.sourceState}`);
  console.log(`ERRORS: ${report.verification.errorCount}`);
  console.log(`EXECUTION AUTHORIZED: false`);
  console.log("POST: NOT_PERFORMED");
  console.log("WALLET: NOT_USED");
  console.log("SIGNING: NOT_PERFORMED");
  console.log("BROADCAST: NOT_PERFORMED");
  console.log("SUBMISSION: NOT_PERFORMED");
  console.log(`REPORT: ${OUTPUT_FILE}`);

  if (state === "BLOCKED") {
    process.exitCode = 1;
  }

  return report;
}

main();
