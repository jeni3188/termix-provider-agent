import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VERSION = "1.0.0";

const OUTPUT_DIR =
  process.env.AACP_OUTPUT_DIR ||
  path.join(process.cwd(), "provider-output", "aacp-observer");

const HEALTH_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health.json"
);

const VERIFY_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health-verify.json"
);

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-aacp-evidence-chain-health-audit.json"
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

const EXPECTED_TYPE_HEALTH =
  "AACP_EVIDENCE_CHAIN_HEALTH";

const EXPECTED_TYPE_VERIFY =
  "AACP_EVIDENCE_CHAIN_HEALTH_VERIFY";

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
        errors.push(
          `${prefix}:SIDE_EFFECT:${field}`
        );
      }
    }
  }

  return errors;
}

function verifyPolicy(report, prefix) {
  const errors = [];

  if (!isObject(report?.policy)) {
    return [`${prefix}:POLICY_VIOLATION`];
  }

  for (const [key, expected] of Object.entries(POLICY)) {
    if (report.policy[key] !== expected) {
      errors.push(`${prefix}:POLICY:${key}`);
    }
  }

  return errors;
}

function verifyHealthStructure(report) {
  const errors = [];
  const health = report?.health;

  if (!isObject(health)) {
    return ["HEALTH:INVALID"];
  }

  const numeric = [
    "artifactsExpected",
    "artifactsPresent",
    "artifactsMissing",
    "artifactsBlocked",
    "artifactsVerified",
    "errorCount",
  ];

  for (const field of numeric) {
    if (
      !Number.isInteger(health[field]) ||
      health[field] < 0
    ) {
      errors.push(`HEALTH:INVALID:${field}`);
    }
  }

  for (const field of [
    "missing",
    "blocked",
    "errors",
  ]) {
    if (!Array.isArray(health[field])) {
      errors.push(`HEALTH:INVALID:${field}`);
    }
  }

  for (const field of [
    "allArtifactsPresent",
    "allArtifactsValid",
  ]) {
    if (typeof health[field] !== "boolean") {
      errors.push(`HEALTH:INVALID:${field}`);
    }
  }

  if (
    Number.isInteger(health.artifactsExpected) &&
    health.artifactsExpected !== EXPECTED_ARTIFACTS
  ) {
    errors.push("HEALTH:EXPECTED_COUNT");
  }

  if (
    Number.isInteger(health.artifactsPresent) &&
    Number.isInteger(health.artifactsMissing) &&
    health.artifactsPresent +
      health.artifactsMissing !==
      EXPECTED_ARTIFACTS
  ) {
    errors.push("HEALTH:COUNT_MISMATCH");
  }

  if (
    Array.isArray(health.missing) &&
    Number.isInteger(health.artifactsMissing) &&
    health.missing.length !==
      health.artifactsMissing
  ) {
    errors.push("HEALTH:MISSING_COUNT");
  }

  if (
    Array.isArray(health.blocked) &&
    Number.isInteger(health.artifactsBlocked) &&
    health.blocked.length !==
      health.artifactsBlocked
  ) {
    errors.push("HEALTH:BLOCKED_COUNT");
  }

  if (
    Array.isArray(health.errors) &&
    Number.isInteger(health.errorCount) &&
    health.errors.length !== health.errorCount
  ) {
    errors.push("HEALTH:ERROR_COUNT");
  }

  if (
    Array.isArray(health.missing) &&
    typeof health.allArtifactsPresent ===
      "boolean" &&
    health.allArtifactsPresent !==
      (health.missing.length === 0)
  ) {
    errors.push("HEALTH:ALL_PRESENT");
  }

  if (
    Array.isArray(health.blocked) &&
    typeof health.allArtifactsValid ===
      "boolean" &&
    health.allArtifactsValid !==
      (health.blocked.length === 0)
  ) {
    errors.push("HEALTH:ALL_VALID");
  }

  return errors;
}

function verifyArtifacts(report) {
  const errors = [];
  const artifacts = report?.artifacts;

  if (!Array.isArray(artifacts)) {
    return ["ARTIFACTS:INVALID"];
  }

  if (artifacts.length !== EXPECTED_ARTIFACTS) {
    errors.push(
      `ARTIFACTS:LENGTH:${artifacts.length}`
    );
  }

  const phases = new Set();
  const files = new Set();

  for (const artifact of artifacts) {
    if (!isObject(artifact)) {
      errors.push("ARTIFACTS:INVALID_ENTRY");
      continue;
    }

    if (
      typeof artifact.phase !== "string" ||
      !artifact.phase
    ) {
      errors.push("ARTIFACTS:INVALID_PHASE");
    } else if (phases.has(artifact.phase)) {
      errors.push(
        `ARTIFACTS:DUPLICATE_PHASE:${artifact.phase}`
      );
    } else {
      phases.add(artifact.phase);
    }

    if (
      typeof artifact.key !== "string" ||
      !artifact.key
    ) {
      errors.push("ARTIFACTS:INVALID_KEY");
    }

    if (
      typeof artifact.file !== "string" ||
      !artifact.file
    ) {
      errors.push("ARTIFACTS:INVALID_FILE");
    } else if (files.has(artifact.file)) {
      errors.push(
        `ARTIFACTS:DUPLICATE_FILE:${artifact.file}`
      );
    } else {
      files.add(artifact.file);
    }

    if (typeof artifact.exists !== "boolean") {
      errors.push("ARTIFACTS:INVALID_EXISTS");
    }

    if (typeof artifact.valid !== "boolean") {
      errors.push("ARTIFACTS:INVALID_VALID");
    }

    if (
      artifact.state !== null &&
      !ALLOWED_STATES.has(artifact.state)
    ) {
      errors.push(
        `ARTIFACTS:INVALID_STATE:${artifact.state}`
      );
    }

    if (
      artifact.sourceState !== null &&
      typeof artifact.sourceState !== "string"
    ) {
      errors.push(
        "ARTIFACTS:INVALID_SOURCE_STATE"
      );
    }

    if (
      artifact.sha256 !== null &&
      !isSha256(artifact.sha256)
    ) {
      errors.push("ARTIFACTS:INVALID_SHA256");
    }

    if (!Array.isArray(artifact.errors)) {
      errors.push("ARTIFACTS:INVALID_ERRORS");
      continue;
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
      errors.push(
        "ARTIFACTS:MISSING_INCONSISTENT"
      );
    }

    if (
      artifact.exists === true &&
      !isSha256(artifact.sha256)
    ) {
      errors.push(
        "ARTIFACTS:PRESENT_SHA256_INVALID"
      );
    }

    if (
      artifact.valid === false &&
      artifact.errors.length === 0
    ) {
      errors.push(
        "ARTIFACTS:INVALID_WITHOUT_ERRORS"
      );
    }

    if (
      artifact.valid === true &&
      artifact.errors.length > 0
    ) {
      errors.push(
        "ARTIFACTS:VALID_WITH_ERRORS"
      );
    }
  }

  return errors;
}

function verifyHealthReport(report) {
  const errors = [];

  if (!isObject(report)) {
    return ["HEALTH_REPORT:INVALID_ROOT"];
  }

  if (report.version !== VERSION) {
    errors.push("HEALTH_REPORT:VERSION");
  }

  if (report.type !== EXPECTED_TYPE_HEALTH) {
    errors.push("HEALTH_REPORT:TYPE");
  }

  if (!isTimestamp(report.generatedAt)) {
    errors.push("HEALTH_REPORT:TIMESTAMP");
  }

  if (!ALLOWED_STATES.has(report.state)) {
    errors.push("HEALTH_REPORT:STATE");
  }

  if (
    typeof report.sourceState !== "string" ||
    !ALLOWED_STATES.has(report.sourceState)
  ) {
    errors.push("HEALTH_REPORT:SOURCE_STATE");
  }

  if (report.mode !== "READ_ONLY") {
    errors.push("HEALTH_REPORT:MODE");
  }

  errors.push(
    ...verifySafety(report, "HEALTH_REPORT")
  );

  errors.push(
    ...verifyPolicy(report, "HEALTH_REPORT")
  );

  errors.push(
    ...verifyHealthStructure(report)
  );

  errors.push(
    ...verifyArtifacts(report)
  );

  return errors;
}

function verifyVerifyReport(report) {
  const errors = [];

  if (!isObject(report)) {
    return ["VERIFY_REPORT:INVALID_ROOT"];
  }

  if (report.version !== VERSION) {
    errors.push("VERIFY_REPORT:VERSION");
  }

  if (report.type !== EXPECTED_TYPE_VERIFY) {
    errors.push("VERIFY_REPORT:TYPE");
  }

  if (!isTimestamp(report.generatedAt)) {
    errors.push("VERIFY_REPORT:TIMESTAMP");
  }

  if (!ALLOWED_STATES.has(report.state)) {
    errors.push("VERIFY_REPORT:STATE");
  }

  if (
    typeof report.sourceState !== "string" ||
    !ALLOWED_STATES.has(report.sourceState)
  ) {
    errors.push("VERIFY_REPORT:SOURCE_STATE");
  }

  if (report.mode !== "READ_ONLY") {
    errors.push("VERIFY_REPORT:MODE");
  }

  errors.push(
    ...verifySafety(report, "VERIFY_REPORT")
  );

  errors.push(
    ...verifyPolicy(report, "VERIFY_REPORT")
  );

  if (!isObject(report.source)) {
    errors.push("VERIFY_REPORT:SOURCE");
  } else {
    if (
      report.source.file !==
      path.basename(HEALTH_FILE)
    ) {
      errors.push("VERIFY_REPORT:SOURCE_FILE");
    }

    if (
      report.source.exists !== true
    ) {
      errors.push("VERIFY_REPORT:SOURCE_MISSING");
    }

    if (
      !isSha256(report.source.sha256)
    ) {
      errors.push("VERIFY_REPORT:SOURCE_SHA256");
    }
  }

  if (!isObject(report.verification)) {
    errors.push("VERIFY_REPORT:VERIFICATION");
  } else {
    const v = report.verification;

    if (typeof v.valid !== "boolean") {
      errors.push(
        "VERIFY_REPORT:VERIFICATION_VALID"
      );
    }

    if (
      typeof v.sourceState !== "string"
    ) {
      errors.push(
        "VERIFY_REPORT:VERIFICATION_SOURCE_STATE"
      );
    }

    for (const field of [
      "sourceErrors",
      "artifactErrors",
      "errors",
    ]) {
      if (!Array.isArray(v[field])) {
        errors.push(
          `VERIFY_REPORT:VERIFICATION_${field}`
        );
      }
    }

    if (
      !Number.isInteger(v.errorCount) ||
      v.errorCount < 0
    ) {
      errors.push(
        "VERIFY_REPORT:VERIFICATION_ERROR_COUNT"
      );
    }

    if (
      Array.isArray(v.errors) &&
      Number.isInteger(v.errorCount) &&
      v.errors.length !== v.errorCount
    ) {
      errors.push(
        "VERIFY_REPORT:VERIFICATION_ERROR_COUNT_MISMATCH"
      );
    }

    for (const field of [
      "artifactsExpected",
      "artifactsPresent",
      "artifactsMissing",
      "artifactsBlocked",
      "artifactsVerified",
    ]) {
      if (
        !Number.isInteger(v[field]) ||
        v[field] < 0
      ) {
        errors.push(
          `VERIFY_REPORT:INVALID_${field}`
        );
      }
    }
  }

  return errors;
}

function crossCheck(
  health,
  verify,
  healthSha
) {
  const errors = [];

  if (
    verify.source.sha256 !== healthSha
  ) {
    errors.push("CROSS_LAYER:SOURCE_SHA256");
  }

  if (
    verify.sourceState !== health.sourceState
  ) {
    errors.push("CROSS_LAYER:SOURCE_STATE");
  }

  if (
    verify.state !== health.state
  ) {
    errors.push("CROSS_LAYER:STATE");
  }

  if (
    verify.verification.sourceState !==
    health.sourceState
  ) {
    errors.push(
      "CROSS_LAYER:VERIFICATION_SOURCE_STATE"
    );
  }

  if (
    verify.verification.artifactsExpected !==
    health.health.artifactsExpected
  ) {
    errors.push(
      "CROSS_LAYER:EXPECTED_COUNT"
    );
  }

  if (
    verify.verification.artifactsPresent !==
    health.health.artifactsPresent
  ) {
    errors.push(
      "CROSS_LAYER:PRESENT_COUNT"
    );
  }

  if (
    verify.verification.artifactsMissing !==
    health.health.artifactsMissing
  ) {
    errors.push(
      "CROSS_LAYER:MISSING_COUNT"
    );
  }

  if (
    verify.verification.artifactsBlocked !==
    health.health.artifactsBlocked
  ) {
    errors.push(
      "CROSS_LAYER:BLOCKED_COUNT"
    );
  }

  if (
    verify.verification.artifactsVerified !==
    health.health.artifactsVerified
  ) {
    errors.push(
      "CROSS_LAYER:VERIFIED_COUNT"
    );
  }

  if (
    health.state === "VERIFIED_READ_ONLY" &&
    verify.verification.valid !== true
  ) {
    errors.push(
      "CROSS_LAYER:VERIFIED_INVALID"
    );
  }

  if (
    health.state === "INCOMPLETE" &&
    verify.verification.valid !== false
  ) {
    errors.push(
      "CROSS_LAYER:INCOMPLETE_INVALID"
    );
  }

  if (
    health.state === "BLOCKED" &&
    verify.state !== "BLOCKED"
  ) {
    errors.push(
      "CROSS_LAYER:BLOCKED_STATE"
    );
  }

  return errors;
}

function buildReport({
  state,
  sourceState,
  healthSha,
  verifySha,
  healthExists,
  verifyExists,
  errors,
  findings,
}) {
  return {
    version: VERSION,
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT",
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

    sources: {
      health: {
        file: path.basename(HEALTH_FILE),
        exists: healthExists,
        sha256: healthExists
          ? healthSha
          : null,
      },
      verify: {
        file: path.basename(VERIFY_FILE),
        exists: verifyExists,
        sha256: verifyExists
          ? verifySha
          : null,
      },
    },

    audit: {
      valid: errors.length === 0,
      findings,
      errors,
      errorCount: errors.length,
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

  const healthExists =
    fs.existsSync(HEALTH_FILE);

  const verifyExists =
    fs.existsSync(VERIFY_FILE);

  if (!healthExists || !verifyExists) {
    const missing = [];

    if (!healthExists) {
      missing.push(
        `MISSING:${path.basename(HEALTH_FILE)}`
      );
    }

    if (!verifyExists) {
      missing.push(
        `MISSING:${path.basename(VERIFY_FILE)}`
      );
    }

    const report = buildReport({
      state: "INCOMPLETE",
      sourceState: "INCOMPLETE",
      healthSha: null,
      verifySha: null,
      healthExists,
      verifyExists,
      errors: [],
      findings: missing,
    });

    fs.writeFileSync(
      OUTPUT_FILE,
      JSON.stringify(report, null, 2) + "\n",
      "utf8"
    );

    printReport(report);
    return;
  }

  const healthSha = sha256File(HEALTH_FILE);
  const verifySha = sha256File(VERIFY_FILE);

  let health;
  let verify;

  try {
    health = readJson(HEALTH_FILE);
  } catch {
    const report = buildReport({
      state: "BLOCKED",
      sourceState: "BLOCKED",
      healthSha,
      verifySha,
      healthExists: true,
      verifyExists: true,
      errors: [
        "HEALTH:INVALID_JSON",
      ],
      findings: [],
    });

    fs.writeFileSync(
      OUTPUT_FILE,
      JSON.stringify(report, null, 2) + "\n",
      "utf8"
    );

    printReport(report);
    process.exitCode = 1;
    return;
  }

  try {
    verify = readJson(VERIFY_FILE);
  } catch {
    const report = buildReport({
      state: "BLOCKED",
      sourceState: "BLOCKED",
      healthSha,
      verifySha,
      healthExists: true,
      verifyExists: true,
      errors: [
        "VERIFY:INVALID_JSON",
      ],
      findings: [],
    });

    fs.writeFileSync(
      OUTPUT_FILE,
      JSON.stringify(report, null, 2) + "\n",
      "utf8"
    );

    printReport(report);
    process.exitCode = 1;
    return;
  }

  const errors = [
    ...verifyHealthReport(health),
    ...verifyVerifyReport(verify),
  ];

  if (
    errors.length === 0 &&
    isObject(health) &&
    isObject(verify)
  ) {
    errors.push(
      ...crossCheck(
        health,
        verify,
        healthSha
      )
    );
  }

  const findings = [];

  if (
    health.state === "INCOMPLETE" ||
    verify.state === "INCOMPLETE"
  ) {
    findings.push(
      "CHAIN_INCOMPLETE"
    );
  }

  if (
    health.state === "VERIFIED_READ_ONLY" &&
    verify.state === "VERIFIED_READ_ONLY"
  ) {
    findings.push(
      "CHAIN_VERIFIED"
    );
  }

  if (
    health.health?.artifactsMissing > 0
  ) {
    findings.push(
      "ARTIFACTS_MISSING"
    );
  }

  if (
    health.health?.artifactsBlocked > 0
  ) {
    findings.push(
      "ARTIFACTS_BLOCKED"
    );
  }

  const state =
    errors.length > 0
      ? "BLOCKED"
      : health.state === "INCOMPLETE" ||
        verify.state === "INCOMPLETE"
        ? "INCOMPLETE"
        : health.state;

  const sourceState =
    errors.length > 0
      ? "BLOCKED"
      : verify.sourceState;

  const report = buildReport({
    state,
    sourceState,
    healthSha,
    verifySha,
    healthExists: true,
    verifyExists: true,
    errors,
    findings,
  });

  fs.writeFileSync(
    OUTPUT_FILE,
    JSON.stringify(report, null, 2) + "\n",
    "utf8"
  );

  printReport(report);

  if (state === "BLOCKED") {
    process.exitCode = 1;
  }
}

function printReport(report) {
  console.log(
    "TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT v1.0"
  );
  console.log(
    "READ ONLY / FAIL CLOSED"
  );
  console.log(
    "==========================================="
  );
  console.log(
    `STATE: ${report.state}`
  );
  console.log(
    `SOURCE STATE: ${report.sourceState}`
  );
  console.log(
    `ERRORS: ${report.audit.errorCount}`
  );
  console.log(
    `FINDINGS: ${report.audit.findings.length}`
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

main();
