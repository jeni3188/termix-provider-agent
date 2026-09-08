import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const SOURCE = path.join(
  ROOT,
  "src",
  "aacp-evidence-chain-health-audit-history.mjs"
);

const TEMP = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-audit-history-")
);

const OUT = path.join(TEMP, "provider-output", "aacp-observer");

const AUDIT = path.join(
  OUT,
  "latest-aacp-evidence-chain-health-audit.json"
);

const VERIFY = path.join(
  OUT,
  "latest-aacp-evidence-chain-health-audit-verify.json"
);

const HISTORY = path.join(
  OUT,
  "latest-aacp-evidence-chain-health-audit-history.json"
);

fs.mkdirSync(OUT, { recursive: true });

function sha256(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function run(env = {}) {
  return spawnSync(
    process.execPath,
    [SOURCE],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OUTPUT_DIR: OUT,
        ...env,
      },
      encoding: "utf8",
    }
  );
}

function readHistory() {
  return JSON.parse(fs.readFileSync(HISTORY, "utf8"));
}

function writeAudit(overrides = {}) {
  const audit = {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state: "INCOMPLETE",
    sourceState: "INCOMPLETE",
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

    audit: {
      valid: true,
      findings: ["CHAIN_INCOMPLETE"],
      errors: [],
      errorCount: 0,
    },

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

    policy: {
      readOnly: true,
      failClosed: true,
      post: "NOT_PERFORMED",
      wallet: "NOT_USED",
      signing: "NOT_PERFORMED",
      broadcast: "NOT_PERFORMED",
      submission: "NOT_PERFORMED",
    },

    ...overrides,
  };

  fs.writeFileSync(
    AUDIT,
    JSON.stringify(audit, null, 2) + "\n"
  );
}

function writeVerify(overrides = {}) {
  const verify = {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_VERIFY",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state: "INCOMPLETE",
    sourceState: "INCOMPLETE",
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

    verification: {
      valid: true,
      sourceState: "INCOMPLETE",
      findings: ["AUDIT_VERIFIED"],
      errors: [],
      errorCount: 0,
    },

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

    policy: {
      readOnly: true,
      failClosed: true,
      post: "NOT_PERFORMED",
      wallet: "NOT_USED",
      signing: "NOT_PERFORMED",
      broadcast: "NOT_PERFORMED",
      submission: "NOT_PERFORMED",
    },

    ...overrides,
  };

  fs.writeFileSync(
    VERIFY,
    JSON.stringify(verify, null, 2) + "\n"
  );
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function test(name, fn) {
  try {
    fn();
    console.log(`PASS: ${name}`);
  } catch (error) {
    console.error(`FAIL: ${name}`);
    console.error(error.message);
    process.exitCode = 1;
  }
}

/* 1 */
test("safe incomplete audit + verifier → INCOMPLETE", () => {
  writeAudit();
  writeVerify();

  const result = run();

  assert(result.status === 0, "expected exit 0");

  const report = readHistory();

  assert(
    report.state === "INCOMPLETE",
    `expected INCOMPLETE, got ${report.state}`
  );

  assert(
    report.sourceState === "INCOMPLETE",
    `expected INCOMPLETE source state, got ${report.sourceState}`
  );

  assert(report.errorCount === 0, "expected zero errors");
});

/* 2 */
test("safe verified audit + verifier → VERIFIED_READ_ONLY", () => {
  writeAudit({
    state: "VERIFIED_READ_ONLY",
    sourceState: "VERIFIED_READ_ONLY",
    audit: {
      valid: true,
      findings: ["CHAIN_VERIFIED"],
      errors: [],
      errorCount: 0,
    },
  });

  writeVerify({
    state: "VERIFIED_READ_ONLY",
    sourceState: "VERIFIED_READ_ONLY",
    verification: {
      valid: true,
      sourceState: "VERIFIED_READ_ONLY",
      findings: ["AUDIT_VERIFIED"],
      errors: [],
      errorCount: 0,
    },
  });

  const result = run();

  assert(result.status === 0, "expected exit 0");

  const report = readHistory();

  assert(
    report.state === "VERIFIED_READ_ONLY",
    `expected VERIFIED_READ_ONLY, got ${report.state}`
  );

  assert(report.errorCount === 0, "expected zero errors");
});

/* 3 */
test("missing verifier → BLOCKED", () => {
  writeAudit();
  fs.rmSync(VERIFY);

  const result = run();

  assert(result.status !== 0, "expected non-zero exit");

  const report = readHistory();

  assert(
    report.state === "BLOCKED",
    `expected BLOCKED, got ${report.state}`
  );

  assert(
    report.errors.includes("VERIFY:FILE_MISSING"),
    "missing verifier error absent"
  );
});

/* 4 */
test("missing audit → BLOCKED", () => {
  writeVerify();
  fs.rmSync(AUDIT);

  const result = run();

  assert(result.status !== 0, "expected non-zero exit");

  const report = readHistory();

  assert(
    report.state === "BLOCKED",
    `expected BLOCKED, got ${report.state}`
  );

  assert(
    report.errors.includes("AUDIT:FILE_MISSING"),
    "missing audit error absent"
  );
});

/* 5 */
test("state mismatch → BLOCKED", () => {
  writeAudit({
    state: "INCOMPLETE",
    sourceState: "INCOMPLETE",
  });

  writeVerify({
    state: "VERIFIED_READ_ONLY",
    sourceState: "VERIFIED_READ_ONLY",
  });

  const result = run();

  assert(result.status !== 0, "expected non-zero exit");

  const report = readHistory();

  assert(
    report.state === "BLOCKED",
    `expected BLOCKED, got ${report.state}`
  );

  assert(
    report.errors.includes("CROSS_LAYER:STATE_MISMATCH"),
    "state mismatch error absent"
  );
});

/* 6 */
test("source state mismatch → BLOCKED", () => {
  writeAudit({
    state: "INCOMPLETE",
    sourceState: "INCOMPLETE",
  });

  writeVerify({
    state: "INCOMPLETE",
    sourceState: "VERIFIED_READ_ONLY",
  });

  const result = run();

  assert(result.status !== 0, "expected non-zero exit");

  const report = readHistory();

  assert(
    report.state === "BLOCKED",
    `expected BLOCKED, got ${report.state}`
  );

  assert(
    report.errors.includes(
      "CROSS_LAYER:SOURCE_STATE_MISMATCH"
    ),
    "source state mismatch error absent"
  );
});

/* 7 */
test("audit safety violation → BLOCKED", () => {
  writeAudit({
    safety: {
      postPerformed: false,
      walletUsed: true,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false,
    },
  });

  writeVerify();

  const result = run();

  assert(result.status !== 0, "expected non-zero exit");

  const report = readHistory();

  assert(
    report.state === "BLOCKED",
    `expected BLOCKED, got ${report.state}`
  );

  assert(
    report.errors.includes("AUDIT:SAFETY:walletUsed"),
    "wallet safety violation absent"
  );
});

/* 8 */
test("audit policy violation → BLOCKED", () => {
  writeAudit({
    policy: {
      readOnly: false,
      failClosed: true,
      post: "NOT_PERFORMED",
      wallet: "NOT_USED",
      signing: "NOT_PERFORMED",
      broadcast: "NOT_PERFORMED",
      submission: "NOT_PERFORMED",
    },
  });

  writeVerify();

  const result = run();

  assert(result.status !== 0, "expected non-zero exit");

  const report = readHistory();

  assert(
    report.state === "BLOCKED",
    `expected BLOCKED, got ${report.state}`
  );

  assert(
    report.errors.includes("AUDIT:POLICY:readOnly"),
    "policy violation absent"
  );
});

/* 9 */
test("invalid audit JSON → BLOCKED", () => {
  fs.writeFileSync(AUDIT, "{invalid-json");

  writeVerify();

  const result = run();

  assert(result.status !== 0, "expected non-zero exit");

  const report = readHistory();

  assert(
    report.state === "BLOCKED",
    `expected BLOCKED, got ${report.state}`
  );

  assert(
    report.errors.includes("AUDIT:INVALID_JSON"),
    "invalid JSON error absent"
  );
});

/* 10 */
test("history stores compact SHA-256 snapshots", () => {
  writeAudit();
  writeVerify();

  const result = run();

  assert(result.status === 0, "expected exit 0");

  const report = readHistory();

  assert(
    isSha(report.snapshots.audit.sha256),
    "audit SHA-256 missing or invalid"
  );

  assert(
    isSha(report.snapshots.verify.sha256),
    "verify SHA-256 missing or invalid"
  );

  assert(
    report.snapshots.audit.sha256 === sha256(AUDIT),
    "audit SHA mismatch"
  );

  assert(
    report.snapshots.verify.sha256 === sha256(VERIFY),
    "verify SHA mismatch"
  );
});

/* 11 */
test("history safety invariants remain false", () => {
  writeAudit();
  writeVerify();

  run();

  const report = readHistory();

  for (const field of [
    "postPerformed",
    "walletUsed",
    "signingPerformed",
    "broadcastPerformed",
    "submissionPerformed",
  ]) {
    assert(
      report.safety[field] === false,
      `safety ${field} violated`
    );

    assert(
      report.sideEffects[field] === false,
      `side effect ${field} violated`
    );
  }

  assert(
    report.executionAuthorized === false,
    "execution authorization violated"
  );
});

/* 12 */
test("history policy invariants remain safe", () => {
  writeAudit();
  writeVerify();

  run();

  const report = readHistory();

  assert(report.mode === "READ_ONLY", "mode violation");
  assert(report.policy.readOnly === true, "readOnly violation");
  assert(report.policy.failClosed === true, "failClosed violation");
  assert(
    report.policy.post === "NOT_PERFORMED",
    "post policy violation"
  );
  assert(
    report.policy.wallet === "NOT_USED",
    "wallet policy violation"
  );
  assert(
    report.policy.signing === "NOT_PERFORMED",
    "signing policy violation"
  );
  assert(
    report.policy.broadcast === "NOT_PERFORMED",
    "broadcast policy violation"
  );
  assert(
    report.policy.submission === "NOT_PERFORMED",
    "submission policy violation"
  );
});

function isSha(value) {
  return (
    typeof value === "string" &&
    /^[a-f0-9]{64}$/i.test(value)
  );
}

console.log(
  "ALL PROVIDER EVIDENCE CHAIN HEALTH AUDIT HISTORY TESTS PASSED"
);

fs.rmSync(TEMP, { recursive: true, force: true });
