import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const ROOT_DIR = process.env.AACP_OUTPUT_DIR
  ? path.resolve(process.env.AACP_OUTPUT_DIR)
  : path.resolve("provider-output/aacp-observer");

const HISTORY_FILE = path.join(
  ROOT_DIR,
  "latest-aacp-evidence-chain-health-audit-history.json"
);

const AUDIT_FILE = path.join(
  ROOT_DIR,
  "latest-aacp-evidence-chain-health-audit.json"
);

const VERIFY_FILE = path.join(
  ROOT_DIR,
  "latest-aacp-evidence-chain-health-audit-verify.json"
);

const OUTPUT_FILE = path.join(
  ROOT_DIR,
  "latest-aacp-evidence-chain-health-audit-history-verify.json"
);

const ALLOWED_STATES = new Set([
  "INCOMPLETE",
  "BLOCKED",
  "VERIFIED_READ_ONLY"
]);

const REQUIRED_FALSE_FLAGS = [
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed"
];

const REQUIRED_POLICY = {
  readOnly: true,
  failClosed: true,
  post: "NOT_PERFORMED",
  wallet: "NOT_USED",
  signing: "NOT_PERFORMED",
  broadcast: "NOT_PERFORMED",
  submission: "NOT_PERFORMED"
};

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function exists(file) {
  return fs.existsSync(file);
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function addError(errors, code) {
  if (!errors.includes(code)) {
    errors.push(code);
  }
}

function verifySafety(report, prefix, errors) {
  if (!report || typeof report !== "object") {
    addError(errors, `${prefix}:INVALID_OBJECT`);
    return;
  }

  for (const field of REQUIRED_FALSE_FLAGS) {
    if (report.safety?.[field] !== false) {
      addError(errors, `${prefix}:SAFETY:${field}`);
    }

    if (report.sideEffects?.[field] !== false) {
      addError(errors, `${prefix}:SIDE_EFFECTS:${field}`);
    }
  }

  if (report.executionAuthorized !== false) {
    addError(errors, `${prefix}:EXECUTION_AUTHORIZED`);
  }
}

function verifyPolicy(report, prefix, errors) {
  if (!report || typeof report !== "object") {
    addError(errors, `${prefix}:INVALID_OBJECT`);
    return;
  }

  for (const [key, expected] of Object.entries(REQUIRED_POLICY)) {
    if (report.policy?.[key] !== expected) {
      addError(errors, `${prefix}:POLICY:${key}`);
    }
  }
}

function verifyRoot(report, errors) {
  if (!report || typeof report !== "object") {
    addError(errors, "HISTORY:INVALID_OBJECT");
    return;
  }

  if (report.version !== "1.0.0") {
    addError(errors, "HISTORY:VERSION");
  }

  if (report.type !== "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY") {
    addError(errors, "HISTORY:TYPE");
  }

  if (report.mode !== "READ_ONLY") {
    addError(errors, "HISTORY:MODE");
  }

  if (!ALLOWED_STATES.has(report.state)) {
    addError(errors, "HISTORY:STATE");
  }

  if (!ALLOWED_STATES.has(report.sourceState)) {
    addError(errors, "HISTORY:SOURCE_STATE");
  }

  if (report.executionAuthorized !== false) {
    addError(errors, "HISTORY:EXECUTION_AUTHORIZED");
  }

  verifySafety(report, "HISTORY", errors);
  verifyPolicy(report, "HISTORY", errors);
}

function verifySnapshotShape(snapshot, kind, errors) {
  if (!snapshot || typeof snapshot !== "object") {
    addError(errors, `${kind}:SNAPSHOT_INVALID`);
    return;
  }

  if (typeof snapshot.file !== "string") {
    addError(errors, `${kind}:FILE`);
  }

  if (snapshot.exists !== true) {
    addError(errors, `${kind}:EXISTS`);
  }

  if (
    typeof snapshot.sha256 !== "string" ||
    !/^[a-f0-9]{64}$/.test(snapshot.sha256)
  ) {
    addError(errors, `${kind}:SHA256`);
  }

  if (!ALLOWED_STATES.has(snapshot.state)) {
    addError(errors, `${kind}:STATE`);
  }

  if (!ALLOWED_STATES.has(snapshot.sourceState)) {
    addError(errors, `${kind}:SOURCE_STATE`);
  }
}

function verifyConsistency(report, errors) {
  if (!report.consistency || typeof report.consistency !== "object") {
    addError(errors, "CONSISTENCY:OBJECT");
    return;
  }

  if (report.consistency.auditExists !== true) {
    addError(errors, "CONSISTENCY:AUDIT_EXISTS");
  }

  if (report.consistency.verifyExists !== true) {
    addError(errors, "CONSISTENCY:VERIFY_EXISTS");
  }

  if (report.consistency.stateMatch !== true) {
    addError(errors, "CONSISTENCY:STATE_MATCH");
  }

  if (report.consistency.sourceStateMatch !== true) {
    addError(errors, "CONSISTENCY:SOURCE_STATE_MATCH");
  }
}

function verifyUpstreamSnapshot(report, errors) {
  const auditSnapshot = report.snapshots?.audit;
  const verifySnapshot = report.snapshots?.verify;

  verifySnapshotShape(auditSnapshot, "AUDIT", errors);
  verifySnapshotShape(verifySnapshot, "VERIFY", errors);

  if (!exists(AUDIT_FILE)) {
    addError(errors, "AUDIT:FILE_MISSING");
  }

  if (!exists(VERIFY_FILE)) {
    addError(errors, "VERIFY:FILE_MISSING");
  }

  if (exists(AUDIT_FILE) && auditSnapshot?.sha256) {
    const actual = sha256File(AUDIT_FILE);

    if (actual !== auditSnapshot.sha256) {
      addError(errors, "AUDIT:SHA256_MISMATCH");
    }
  }

  if (exists(VERIFY_FILE) && verifySnapshot?.sha256) {
    const actual = sha256File(VERIFY_FILE);

    if (actual !== verifySnapshot.sha256) {
      addError(errors, "VERIFY:SHA256_MISMATCH");
    }
  }

  if (
    auditSnapshot &&
    verifySnapshot &&
    auditSnapshot.state !== verifySnapshot.state
  ) {
    addError(errors, "SNAPSHOT:STATE_MISMATCH");
  }

  if (
    auditSnapshot &&
    verifySnapshot &&
    auditSnapshot.sourceState !== verifySnapshot.sourceState
  ) {
    addError(errors, "SNAPSHOT:SOURCE_STATE_MISMATCH");
  }

  if (
    report.state !== auditSnapshot?.state ||
    report.state !== verifySnapshot?.state
  ) {
    addError(errors, "HISTORY:STATE_LINK_MISMATCH");
  }

  if (
    report.sourceState !== auditSnapshot?.sourceState ||
    report.sourceState !== verifySnapshot?.sourceState
  ) {
    addError(errors, "HISTORY:SOURCE_STATE_LINK_MISMATCH");
  }
}

function verifyAuditSnapshotSemantics(report, errors) {
  const audit = report.snapshots?.audit;

  if (!audit) {
    return;
  }

  if (audit.auditValid !== true) {
    addError(errors, "AUDIT:AUDIT_VALID");
  }

  if (
    audit.errorCount !== 0 &&
    audit.errorCount !== null
  ) {
    addError(errors, "AUDIT:ERROR_COUNT");
  }
}

function verifyVerifySnapshotSemantics(report, errors) {
  const verify = report.snapshots?.verify;

  if (!verify) {
    return;
  }

  if (verify.verificationValid !== true) {
    addError(errors, "VERIFY:VERIFICATION_VALID");
  }

  if (
    verify.errorCount !== 0 &&
    verify.errorCount !== null
  ) {
    addError(errors, "VERIFY:ERROR_COUNT");
  }
}

function buildReport() {
  const errors = [];

  let history = null;
  const historyExists = exists(HISTORY_FILE);

  if (!historyExists) {
    addError(errors, "HISTORY:FILE_MISSING");
  } else {
    try {
      history = readJson(HISTORY_FILE);
    } catch {
      addError(errors, "HISTORY:INVALID_JSON");
    }
  }

  if (history) {
    try {
      verifyRoot(history, errors);
      verifyConsistency(history, errors);
      verifyUpstreamSnapshot(history, errors);
      verifyAuditSnapshotSemantics(history, errors);
      verifyVerifySnapshotSemantics(history, errors);
    } catch (error) {
      addError(errors, "VERIFIER:INTERNAL_ERROR");

      if (error instanceof Error && error.message) {
        addError(errors, `VERIFIER:ERROR:${error.message}`);
      }
    }
  }

  const state =
    errors.length === 0
      ? history?.state ?? "INCOMPLETE"
      : "BLOCKED";

  const sourceState =
    errors.length === 0
      ? history?.sourceState ?? "INCOMPLETE"
      : history?.sourceState ?? "BLOCKED";

  const safeExists = (file) => {
    try {
      return exists(file);
    } catch {
      return false;
    }
  };

  const safeSha256 = (file) => {
    try {
      return safeExists(file)
        ? sha256File(file)
        : null;
    } catch {
      return null;
    }
  };

  return {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_VERIFY",
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
      submissionPerformed: false
    },

    sideEffects: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false
    },

    verification: {
      valid: errors.length === 0,
      historyExists,
      auditExists: safeExists(AUDIT_FILE),
      verifyExists: safeExists(VERIFY_FILE)
    },

    sources: {
      history: {
        file: "latest-aacp-evidence-chain-health-audit-history.json",
        exists: historyExists,
        sha256: safeSha256(HISTORY_FILE)
      },

      audit: {
        file: "latest-aacp-evidence-chain-health-audit.json",
        exists: safeExists(AUDIT_FILE),
        sha256: safeSha256(AUDIT_FILE)
      },

      verify: {
        file: "latest-aacp-evidence-chain-health-audit-verify.json",
        exists: safeExists(VERIFY_FILE),
        sha256: safeSha256(VERIFY_FILE)
      }
    },

    errors,
    errorCount: errors.length,

    policy: {
      ...REQUIRED_POLICY
    }
  };
}

function main() {
  fs.mkdirSync(ROOT_DIR, { recursive: true });

  const report = buildReport();

  fs.writeFileSync(
    OUTPUT_FILE,
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8"
  );

  console.log("TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT HISTORY VERIFY v1.0");
  console.log("READ ONLY / FAIL CLOSED");
  console.log(`STATE: ${report.state}`);
  console.log(`SOURCE STATE: ${report.sourceState}`);
  console.log(`VALID: ${report.verification.valid}`);
  console.log(`ERRORS: ${report.errorCount}`);
  console.log(`EXECUTION AUTHORIZED: ${report.executionAuthorized}`);
  console.log(`REPORT: ${OUTPUT_FILE}`);

  return report.errorCount === 0 ? 0 : 1;
}

process.exitCode = main();
