import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const PROJECT_ROOT = process.cwd();

function sha256(data) {
  return crypto
    .createHash("sha256")
    .update(data)
    .digest("hex");
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function makeTempDir() {
  return fs.mkdtempSync(
    path.join(os.tmpdir(), "aacp-history-verify-")
  );
}

function runVerifier(outputDir) {
  const result = spawnSync(
    process.execPath,
    [
      "src/aacp-evidence-chain-health-audit-history-verifier.mjs"
    ],
    {
      cwd: PROJECT_ROOT,
      env: {
        ...process.env,
        AACP_OUTPUT_DIR: outputDir
      },
      encoding: "utf8"
    }
  );

  return result;
}

function safeAudit(state = "INCOMPLETE") {
  return {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT",
    generatedAt: "2026-09-08T00:00:00.000Z",
    mode: "READ_ONLY",
    state,
    sourceState: state,
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

    audit: {
      valid: true,
      findings: state === "INCOMPLETE"
        ? ["CHAIN_INCOMPLETE"]
        : [],
      errors: [],
      errorCount: 0
    },

    policy: {
      readOnly: true,
      failClosed: true,
      post: "NOT_PERFORMED",
      wallet: "NOT_USED",
      signing: "NOT_PERFORMED",
      broadcast: "NOT_PERFORMED",
      submission: "NOT_PERFORMED"
    }
  };
}

function safeVerify(state = "INCOMPLETE") {
  return {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_VERIFY",
    generatedAt: "2026-09-08T00:00:01.000Z",
    mode: "READ_ONLY",
    state,
    sourceState: state,
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
      valid: true,
      auditValid: true,
      sourceValid: true,
      crossLayerValid: true
    },

    errors: [],
    errorCount: 0,

    policy: {
      readOnly: true,
      failClosed: true,
      post: "NOT_PERFORMED",
      wallet: "NOT_USED",
      signing: "NOT_PERFORMED",
      broadcast: "NOT_PERFORMED",
      submission: "NOT_PERFORMED"
    }
  };
}

function makeHistory(auditFile, verifyFile, state = "INCOMPLETE") {
  return {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY",
    generatedAt: "2026-09-08T00:00:02.000Z",
    mode: "READ_ONLY",
    state,
    sourceState: state,
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

    snapshots: {
      audit: {
        file: "latest-aacp-evidence-chain-health-audit.json",
        exists: true,
        sha256: sha256(auditFile),
        state,
        sourceState: state,
        auditValid: true,
        errorCount: 0
      },

      verify: {
        file: "latest-aacp-evidence-chain-health-audit-verify.json",
        exists: true,
        sha256: sha256(verifyFile),
        state,
        sourceState: state,
        verificationValid: true,
        errorCount: 0
      }
    },

    consistency: {
      auditExists: true,
      verifyExists: true,
      stateMatch: true,
      sourceStateMatch: true
    },

    errors: [],
    errorCount: 0,

    policy: {
      readOnly: true,
      failClosed: true,
      post: "NOT_PERFORMED",
      wallet: "NOT_USED",
      signing: "NOT_PERFORMED",
      broadcast: "NOT_PERFORMED",
      submission: "NOT_PERFORMED"
    }
  };
}

function writeJson(file, value) {
  fs.writeFileSync(
    file,
    `${JSON.stringify(value, null, 2)}\n`,
    "utf8"
  );
}

function prepareScenario(
  dir,
  {
    audit = safeAudit(),
    verify = safeVerify(),
    historyState = audit.state,
    mutateHistory = null,
    omitHistory = false,
    omitAudit = false,
    omitVerify = false
  } = {}
) {
  const auditFile = path.join(
    dir,
    "latest-aacp-evidence-chain-health-audit.json"
  );

  const verifyFile = path.join(
    dir,
    "latest-aacp-evidence-chain-health-audit-verify.json"
  );

  const historyFile = path.join(
    dir,
    "latest-aacp-evidence-chain-health-audit-history.json"
  );

  writeJson(auditFile, audit);
  writeJson(verifyFile, verify);

  if (omitAudit) {
    fs.unlinkSync(auditFile);
  }

  if (omitVerify) {
    fs.unlinkSync(verifyFile);
  }

  if (!omitHistory) {
    const auditRaw = fs.existsSync(auditFile)
      ? fs.readFileSync(auditFile, "utf8")
      : "";

    const verifyRaw = fs.existsSync(verifyFile)
      ? fs.readFileSync(verifyFile, "utf8")
      : "";

    let history = makeHistory(
      auditRaw,
      verifyRaw,
      historyState
    );

    if (mutateHistory) {
      history = mutateHistory(history);
    }

    writeJson(historyFile, history);
  }
}

function readOutput(dir) {
  return JSON.parse(
    fs.readFileSync(
      path.join(
        dir,
        "latest-aacp-evidence-chain-health-audit-history-verify.json"
      ),
      "utf8"
    )
  );
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
test("safe incomplete history → VERIFIED", () => {
  const dir = makeTempDir();

  prepareScenario(dir);

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status === 0, "verifier should exit 0");
  assert(report.state === "INCOMPLETE", "state should remain INCOMPLETE");
  assert(report.sourceState === "INCOMPLETE", "source state should remain INCOMPLETE");
  assert(report.verification.valid === true, "verification should be valid");
  assert(report.errorCount === 0, "error count should be zero");
});

/* 2 */
test("safe verified history → VERIFIED_READ_ONLY", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    audit: safeAudit("VERIFIED_READ_ONLY"),
    verify: safeVerify("VERIFIED_READ_ONLY"),
    historyState: "VERIFIED_READ_ONLY"
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status === 0, "verifier should exit 0");
  assert(
    report.state === "VERIFIED_READ_ONLY",
    "state should be VERIFIED_READ_ONLY"
  );
  assert(
    report.sourceState === "VERIFIED_READ_ONLY",
    "source state should be VERIFIED_READ_ONLY"
  );
  assert(report.verification.valid === true, "verification should be valid");
});

/* 3 */
test("missing history → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    omitHistory: true
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(report.state === "BLOCKED", "state should be BLOCKED");
  assert(
    report.errors.includes("HISTORY:FILE_MISSING"),
    "missing history finding expected"
  );
});

/* 4 */
test("missing audit source → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    omitAudit: true
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(report.state === "BLOCKED", "state should be BLOCKED");
  assert(
    report.errors.includes("AUDIT:FILE_MISSING"),
    "missing audit finding expected"
  );
});

/* 5 */
test("missing verifier source → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    omitVerify: true
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(report.state === "BLOCKED", "state should be BLOCKED");
  assert(
    report.errors.includes("VERIFY:FILE_MISSING"),
    "missing verify finding expected"
  );
});

/* 6 */
test("audit SHA mismatch → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    mutateHistory(history) {
      history.snapshots.audit.sha256 =
        "0000000000000000000000000000000000000000000000000000000000000000";
      return history;
    }
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(
    report.errors.includes("AUDIT:SHA256_MISMATCH"),
    "audit SHA mismatch expected"
  );
});

/* 7 */
test("verify SHA mismatch → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    mutateHistory(history) {
      history.snapshots.verify.sha256 =
        "1111111111111111111111111111111111111111111111111111111111111111";
      return history;
    }
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(
    report.errors.includes("VERIFY:SHA256_MISMATCH"),
    "verify SHA mismatch expected"
  );
});

/* 8 */
test("history state mismatch → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    mutateHistory(history) {
      history.state = "VERIFIED_READ_ONLY";
      return history;
    }
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(
    report.errors.includes("HISTORY:STATE_LINK_MISMATCH"),
    "history state link mismatch expected"
  );
});

/* 9 */
test("snapshot state mismatch → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    mutateHistory(history) {
      history.snapshots.verify.state = "VERIFIED_READ_ONLY";
      return history;
    }
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(
    report.errors.includes("SNAPSHOT:STATE_MISMATCH"),
    "snapshot state mismatch expected"
  );
});

/* 10 */
test("snapshot sourceState mismatch → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    mutateHistory(history) {
      history.snapshots.verify.sourceState = "BLOCKED";
      return history;
    }
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(
    report.errors.includes("SNAPSHOT:SOURCE_STATE_MISMATCH"),
    "snapshot source state mismatch expected"
  );
});

/* 11 */
test("history safety violation → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    mutateHistory(history) {
      history.executionAuthorized = true;
      return history;
    }
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(
    report.errors.includes("HISTORY:EXECUTION_AUTHORIZED"),
    "execution authorization violation expected"
  );
});

/* 12 */
test("history policy violation → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir, {
    mutateHistory(history) {
      history.policy.post = "PERFORMED";
      return history;
    }
  });

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(
    report.errors.includes("HISTORY:POLICY:post"),
    "policy violation expected"
  );
});

/* 13 */
test("invalid history JSON → BLOCKED", () => {
  const dir = makeTempDir();

  prepareScenario(dir);

  fs.writeFileSync(
    path.join(
      dir,
      "latest-aacp-evidence-chain-health-audit-history.json"
    ),
    "{invalid-json\n",
    "utf8"
  );

  const result = runVerifier(dir);
  const report = readOutput(dir);

  assert(result.status !== 0, "verifier should fail");
  assert(report.state === "BLOCKED", "state should be BLOCKED");
  assert(
    report.errors.includes("HISTORY:INVALID_JSON"),
    "invalid JSON finding expected"
  );
});

/* 14 */
test("history source SHA snapshots match actual files", () => {
  const dir = makeTempDir();

  prepareScenario(dir);

  const result = runVerifier(dir);
  const report = readOutput(dir);

  const auditFile = path.join(
    dir,
    "latest-aacp-evidence-chain-health-audit.json"
  );

  const verifyFile = path.join(
    dir,
    "latest-aacp-evidence-chain-health-audit-verify.json"
  );

  assert(result.status === 0, "verifier should exit 0");

  assert(
    report.sources.audit.sha256 ===
      sha256(fs.readFileSync(auditFile)),
    "audit source SHA mismatch"
  );

  assert(
    report.sources.verify.sha256 ===
      sha256(fs.readFileSync(verifyFile)),
    "verify source SHA mismatch"
  );
});

/* 15 */
test("verification safety invariants remain false", () => {
  const dir = makeTempDir();

  prepareScenario(dir);

  runVerifier(dir);

  const report = readOutput(dir);

  for (const key of [
    "postPerformed",
    "walletUsed",
    "signingPerformed",
    "broadcastPerformed",
    "submissionPerformed"
  ]) {
    assert(
      report.safety[key] === false,
      `safety.${key} must remain false`
    );

    assert(
      report.sideEffects[key] === false,
      `sideEffects.${key} must remain false`
    );
  }

  assert(
    report.executionAuthorized === false,
    "executionAuthorized must remain false"
  );
});

/* 16 */
test("verification policy remains fail closed", () => {
  const dir = makeTempDir();

  prepareScenario(dir);

  runVerifier(dir);

  const report = readOutput(dir);

  assert(report.policy.readOnly === true, "readOnly policy");
  assert(report.policy.failClosed === true, "failClosed policy");
  assert(report.policy.post === "NOT_PERFORMED", "post policy");
  assert(report.policy.wallet === "NOT_USED", "wallet policy");
  assert(report.policy.signing === "NOT_PERFORMED", "signing policy");
  assert(report.policy.broadcast === "NOT_PERFORMED", "broadcast policy");
  assert(report.policy.submission === "NOT_PERFORMED", "submission policy");
});

/* 17 */
test("no network or signing primitives in source", () => {
  const files = [
    "src/aacp-evidence-chain-health-audit-history-verifier.mjs",
    "tests/aacp-evidence-chain-health-audit-history-verifier-regression.mjs"
  ];

  const forbidden = [
    /\bfetch\s*\(/i,
    /\baxios\b/i,
    /\bWebSocket\b/i,
    /\bsendTransaction\b/i,
    /\bsendRawTransaction\b/i,
    /\bprivateKey\b/i,
    /\bmnemonic\b/i,
    /\bseedPhrase\b/i,
    /\bsignTransaction\b/i,
    /\bsignAndSend\b/i,
    /\bsubmitTransaction\b/i
  ];

  for (const relative of files) {
    const content = fs.readFileSync(
      path.join(PROJECT_ROOT, relative),
      "utf8"
    );

    for (const pattern of forbidden) {
      assert(
        !pattern.test(content),
        `${relative} contains forbidden primitive ${pattern}`
      );
    }
  }
});

if (process.exitCode === 1) {
  process.exit(1);
}

console.log(
  "ALL PROVIDER EVIDENCE CHAIN HEALTH AUDIT HISTORY VERIFIER TESTS PASSED"
);
