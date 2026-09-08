import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";

const OUTPUT_DIR =
  process.env.AACP_OUTPUT_DIR ||
  path.join(process.cwd(), "provider-output", "aacp-observer");

const SOURCE_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health.json"
);

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health-verify.json"
);

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const EXPECTED_ARTIFACTS = 11;

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

function isTimestamp(value) {
  return (
    typeof value === "string" &&
    Number.isFinite(Date.parse(value))
  );
}

function isSha256(value) {
  return (
    typeof value === "string" &&
    /^[a-f0-9]{64}$/i.test(value)
  );
}

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function readJson(file) {
  return JSON.parse(
    fs.readFileSync(file, "utf8")
  );
}

function verifySafety(report) {
  const errors = [];

  if (report.executionAuthorized !== false) {
    errors.push("EXECUTION_AUTHORIZED");
  }

  if (!isObject(report.safety)) {
    errors.push("INVALID_SAFETY");
  } else {
    for (const field of SAFETY_FIELDS) {
      if (report.safety[field] !== false) {
        errors.push(`SAFETY:${field}`);
      }
    }
  }

  if (!isObject(report.sideEffects)) {
    errors.push("INVALID_SIDE_EFFECTS");
  } else {
    for (const field of SAFETY_FIELDS) {
      if (report.sideEffects[field] !== false) {
        errors.push(`SIDE_EFFECT:${field}`);
      }
    }
  }

  return errors;
}

function verifyPolicy(report) {
  const errors = [];

  if (!isObject(report.policy)) {
    return ["POLICY_VIOLATION"];
  }

  for (const [key, expected] of Object.entries(POLICY)) {
    if (report.policy[key] !== expected) {
      errors.push(`POLICY:${key}`);
    }
  }

  return errors;
}

function verifyHealth(report) {
  const errors = [];

  if (!isObject(report.health)) {
    return {
      errors: ["INVALID_HEALTH"],
      expected: null,
      present: null,
      missing: null,
      blocked: null,
      verified: null,
      errorCount: null,
    };
  }

  const health = report.health;

  const numericFields = [
    "artifactsExpected",
    "artifactsPresent",
    "artifactsMissing",
    "artifactsBlocked",
    "artifactsVerified",
    "errorCount",
  ];

  for (const field of numericFields) {
    if (
      !Number.isInteger(health[field]) ||
      health[field] < 0
    ) {
      errors.push(`INVALID_HEALTH:${field}`);
    }
  }

  if (!Array.isArray(health.missing)) {
    errors.push("INVALID_HEALTH:missing");
  }

  if (!Array.isArray(health.blocked)) {
    errors.push("INVALID_HEALTH:blocked");
  }

  if (!Array.isArray(health.errors)) {
    errors.push("INVALID_HEALTH:errors");
  }

  if (typeof health.allArtifactsPresent !== "boolean") {
    errors.push("INVALID_HEALTH:allArtifactsPresent");
  }

  if (typeof health.allArtifactsValid !== "boolean") {
    errors.push("INVALID_HEALTH:allArtifactsValid");
  }

  if (
    Number.isInteger(health.artifactsExpected) &&
    health.artifactsExpected !== EXPECTED_ARTIFACTS
  ) {
    errors.push("INVALID_ARTIFACT_COUNT");
  }

  if (
    Number.isInteger(health.artifactsPresent) &&
    Number.isInteger(health.artifactsMissing) &&
    health.artifactsPresent + health.artifactsMissing !==
      EXPECTED_ARTIFACTS
  ) {
    errors.push("COUNT_MISMATCH");
  }

  if (
    Array.isArray(health.missing) &&
    Number.isInteger(health.artifactsMissing) &&
    health.missing.length !== health.artifactsMissing
  ) {
    errors.push("MISSING_COUNT_MISMATCH");
  }

  if (
    Array.isArray(health.blocked) &&
    Number.isInteger(health.artifactsBlocked) &&
    health.blocked.length !== health.artifactsBlocked
  ) {
    errors.push("BLOCKED_COUNT_MISMATCH");
  }

  if (
    Array.isArray(health.errors) &&
    Number.isInteger(health.errorCount) &&
    health.errors.length !== health.errorCount
  ) {
    errors.push("ERROR_COUNT_MISMATCH");
  }

  if (
    Number.isInteger(health.artifactsPresent) &&
    Number.isInteger(health.artifactsBlocked) &&
    Number.isInteger(health.artifactsVerified) &&
    health.artifactsBlocked + health.artifactsVerified >
      health.artifactsPresent
  ) {
    errors.push("STATUS_COUNT_MISMATCH");
  }

  if (
    Array.isArray(health.missing) &&
    typeof health.allArtifactsPresent === "boolean"
  ) {
    const expectedPresent =
      health.missing.length === 0;

    if (
      health.allArtifactsPresent !== expectedPresent
    ) {
      errors.push("ALL_PRESENT_MISMATCH");
    }
  }

  if (
    Array.isArray(health.blocked) &&
    typeof health.allArtifactsValid === "boolean"
  ) {
    const expectedValid =
      health.blocked.length === 0;

    if (
      health.allArtifactsValid !== expectedValid
    ) {
      errors.push("ALL_VALID_MISMATCH");
    }
  }

  return {
    errors,
    expected: health.artifactsExpected,
    present: health.artifactsPresent,
    missing: health.artifactsMissing,
    blocked: health.artifactsBlocked,
    verified: health.artifactsVerified,
    errorCount: health.errorCount,
  };
}

function verifyArtifacts(report) {
  const errors = [];

  if (!Array.isArray(report.artifacts)) {
    return ["INVALID_ARTIFACTS"];
  }

  if (report.artifacts.length !== EXPECTED_ARTIFACTS) {
    errors.push(
      `ARTIFACT_LENGTH:${report.artifacts.length}`
    );
  }

  const phases = new Set();
  const files = new Set();

  for (const artifact of report.artifacts) {
    if (!isObject(artifact)) {
      errors.push("INVALID_ARTIFACT_ENTRY");
      continue;
    }

    if (
      typeof artifact.phase !== "string" ||
      artifact.phase.length === 0
    ) {
      errors.push("INVALID_ARTIFACT_PHASE");
    } else if (phases.has(artifact.phase)) {
      errors.push(
        `DUPLICATE_ARTIFACT_PHASE:${artifact.phase}`
      );
    } else {
      phases.add(artifact.phase);
    }

    if (
      typeof artifact.file !== "string" ||
      artifact.file.length === 0
    ) {
      errors.push("INVALID_ARTIFACT_FILE");
    } else if (files.has(artifact.file)) {
      errors.push(
        `DUPLICATE_ARTIFACT_FILE:${artifact.file}`
      );
    } else {
      files.add(artifact.file);
    }

    if (typeof artifact.exists !== "boolean") {
      errors.push("INVALID_ARTIFACT_EXISTS");
    }

    if (typeof artifact.valid !== "boolean") {
      errors.push("INVALID_ARTIFACT_VALID");
    }

    if (
      artifact.state !== null &&
      !ALLOWED_STATES.has(artifact.state)
    ) {
      errors.push(
        `INVALID_ARTIFACT_STATE:${artifact.state}`
      );
    }

    if (
      artifact.sourceState !== null &&
      typeof artifact.sourceState !== "string"
    ) {
      errors.push("INVALID_ARTIFACT_SOURCE_STATE");
    }

    if (
      artifact.sha256 !== null &&
      !isSha256(artifact.sha256)
    ) {
      errors.push("INVALID_ARTIFACT_SHA256");
    }

    if (!Array.isArray(artifact.errors)) {
      errors.push("INVALID_ARTIFACT_ERRORS");
    }

    if (
      artifact.exists === false &&
      (
        artifact.valid !== false ||
        artifact.state !== null ||
        artifact.sourceState !== null ||
        artifact.sha256 !== null
      )
    ) {
      errors.push("MISSING_ARTIFACT_INCONSISTENT");
    }

    if (
      artifact.exists === true &&
      !isSha256(artifact.sha256)
    ) {
      errors.push("PRESENT_ARTIFACT_SHA256_INVALID");
    }

    if (
      artifact.valid === false &&
      artifact.errors.length === 0
    ) {
      errors.push("INVALID_ARTIFACT_WITHOUT_ERRORS");
    }

    if (
      artifact.valid === true &&
      artifact.errors.length > 0
    ) {
      errors.push("VALID_ARTIFACT_WITH_ERRORS");
    }
  }

  return errors;
}

function verifySource(report) {
  const errors = [];

  if (!isObject(report)) {
    return ["INVALID_ROOT"];
  }

  if (report.version !== VERSION) {
    errors.push("INVALID_VERSION");
  }

  if (
    report.type !==
    "AACP_EVIDENCE_CHAIN_HEALTH"
  ) {
    errors.push("INVALID_TYPE");
  }

  if (!isTimestamp(report.generatedAt)) {
    errors.push("INVALID_TIMESTAMP");
  }

  if (!ALLOWED_STATES.has(report.state)) {
    errors.push("INVALID_STATE");
  }

  if (
    typeof report.sourceState !== "string" ||
    !ALLOWED_STATES.has(report.sourceState)
  ) {
    errors.push("INVALID_SOURCE_STATE");
  }

  if (report.mode !== "READ_ONLY") {
    errors.push("MODE_NOT_READ_ONLY");
  }

  errors.push(...verifySafety(report));
  errors.push(...verifyPolicy(report));

  return errors;
}

function deriveVerificationState(
  source,
  sourceErrors,
  health
) {
  if (sourceErrors.length > 0) {
    return "BLOCKED";
  }

  if (
    health.blocked !== null &&
    health.blocked > 0
  ) {
    return "BLOCKED";
  }

  if (source.state === "BLOCKED") {
    return "BLOCKED";
  }

  if (
    health.missing !== null &&
    health.missing > 0
  ) {
    return "INCOMPLETE";
  }

  if (source.state === "INCOMPLETE") {
    return "INCOMPLETE";
  }

  if (
    source.state === "VERIFIED_READ_ONLY" &&
    health.expected === EXPECTED_ARTIFACTS &&
    health.present === EXPECTED_ARTIFACTS &&
    health.missing === 0 &&
    health.blocked === 0 &&
    health.errorCount === 0
  ) {
    return "VERIFIED_READ_ONLY";
  }

  if (
    source.state === "READY_READ_ONLY" ||
    source.state === "BACKEND_UNAVAILABLE"
  ) {
    return source.state;
  }

  return "READY_READ_ONLY";
}

function buildReport({
  state,
  sourceState,
  sourceSha,
  sourceExists,
  sourceErrors,
  artifactErrors,
  health,
}) {
  const errors = [
    ...sourceErrors,
    ...artifactErrors,
  ];

  return {
    version: VERSION,
    type: "AACP_EVIDENCE_CHAIN_HEALTH_VERIFY",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state,
    sourceState,
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
      file: path.basename(SOURCE_FILE),
      exists: sourceExists,
      sha256: sourceExists ? sourceSha : null,
    },

    verification: {
      valid:
        state === "VERIFIED_READ_ONLY",
      sourceState,
      sourceErrors,
      artifactErrors,
      errors,
      errorCount: errors.length,
      artifactsExpected: health.expected,
      artifactsPresent: health.present,
      artifactsMissing: health.missing,
      artifactsBlocked: health.blocked,
      artifactsVerified: health.verified,
    },

    policy: {
      ...POLICY,
    },
  };
}

function main() {
  fs.mkdirSync(
    OUTPUT_DIR,
    { recursive: true }
  );

  if (!fs.existsSync(SOURCE_FILE)) {
    const report = buildReport({
      state: "INCOMPLETE",
      sourceState: "INCOMPLETE",
      sourceSha: null,
      sourceExists: false,
      sourceErrors: [],
      artifactErrors: [
        `MISSING:${path.basename(SOURCE_FILE)}`,
      ],
      health: {
        expected: null,
        present: null,
        missing: null,
        blocked: null,
        verified: null,
        errorCount: null,
      },
    });

    fs.writeFileSync(
      OUTPUT_FILE,
      JSON.stringify(report, null, 2) + "\n",
      "utf8"
    );

    console.log(
      "TERMiX AACP EVIDENCE CHAIN HEALTH VERIFY v1.0"
    );
    console.log("READ ONLY / FAIL CLOSED");
    console.log("============================================");
    console.log("STATE: INCOMPLETE");
    console.log(
      "SOURCE: MISSING"
    );
    console.log(
      "EXECUTION AUTHORIZED: false"
    );

    return;
  }

  let source;

  try {
    source = readJson(SOURCE_FILE);
  } catch {
    const report = buildReport({
      state: "BLOCKED",
      sourceState: "BLOCKED",
      sourceSha: sha256File(SOURCE_FILE),
      sourceExists: true,
      sourceErrors: [
        `INVALID_JSON:${path.basename(SOURCE_FILE)}`,
      ],
      artifactErrors: [],
      health: {
        expected: null,
        present: null,
        missing: null,
        blocked: null,
        verified: null,
        errorCount: null,
      },
    });

    fs.writeFileSync(
      OUTPUT_FILE,
      JSON.stringify(report, null, 2) + "\n",
      "utf8"
    );

    console.log(
      "TERMiX AACP EVIDENCE CHAIN HEALTH VERIFY v1.0"
    );
    console.log("READ ONLY / FAIL CLOSED");
    console.log("============================================");
    console.log("STATE: BLOCKED");
    console.log(
      "SOURCE: INVALID_JSON"
    );
    console.log(
      "EXECUTION AUTHORIZED: false"
    );

    process.exitCode = 1;
    return;
  }

  const sourceErrors = verifySource(source);
  const health = verifyHealth(source);
  const artifactErrors = verifyArtifacts(source);

  const allErrors = [
    ...sourceErrors,
    ...health.errors,
    ...artifactErrors,
  ];

  const state = deriveVerificationState(
    source,
    allErrors,
    health
  );

  const sourceState =
    ALLOWED_STATES.has(source.state)
      ? source.state
      : "BLOCKED";

  const report = buildReport({
    state,
    sourceState,
    sourceSha: sha256File(SOURCE_FILE),
    sourceExists: true,
    sourceErrors: [
      ...sourceErrors,
      ...health.errors,
    ],
    artifactErrors,
    health,
  });

  fs.writeFileSync(
    OUTPUT_FILE,
    JSON.stringify(report, null, 2) + "\n",
    "utf8"
  );

  console.log(
    "TERMiX AACP EVIDENCE CHAIN HEALTH VERIFY v1.0"
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log("============================================");
  console.log(`STATE: ${state}`);
  console.log(
    `SOURCE STATE: ${sourceState}`
  );
  console.log(
    `ARTIFACTS EXPECTED: ${health.expected ?? "null"}`
  );
  console.log(
    `ARTIFACTS PRESENT: ${health.present ?? "null"}`
  );
  console.log(
    `ARTIFACTS MISSING: ${health.missing ?? "null"}`
  );
  console.log(
    `ARTIFACTS BLOCKED: ${health.blocked ?? "null"}`
  );
  console.log(
    `ARTIFACTS VERIFIED: ${health.verified ?? "null"}`
  );
  console.log(
    `ERRORS: ${report.verification.errorCount}`
  );
  console.log(
    "EXECUTION AUTHORIZED: false"
  );
  console.log(
    `REPORT: ${OUTPUT_FILE}`
  );

  if (state === "BLOCKED") {
    process.exitCode = 1;
  }
}

main();
