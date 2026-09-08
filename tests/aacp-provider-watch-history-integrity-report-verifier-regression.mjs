import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();

const VERIFIER = path.join(
  ROOT,
  "src/aacp-provider-watch-history-integrity-report-verifier.mjs",
);

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });

  fs.writeFileSync(
    file,
    `${JSON.stringify(value, null, 2)}\n`,
    "utf8",
  );
}

function safeAudit() {
  return {
    version: "1.0.0",
    generatedAt: "2026-09-08T00:00:00.000Z",
    mode: "READ_ONLY",
    state: "VERIFIED_READ_ONLY",
    sourceState: "VERIFIED_READ_ONLY",
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
      history: {
        exists: true,
        sha256:
          "1111111111111111111111111111111111111111111111111111111111111111",
      },
      historyVerify: {
        exists: true,
        sha256:
          "2222222222222222222222222222222222222222222222222222222222222222",
      },
      analysis: {
        exists: true,
        sha256:
          "3333333333333333333333333333333333333333333333333333333333333333",
      },
      analysisVerify: {
        exists: true,
        sha256:
          "4444444444444444444444444444444444444444444444444444444444444444",
      },
      chainVerify: {
        exists: true,
        sha256:
          "5555555555555555555555555555555555555555555555555555555555555555",
      },
    },

    integrity: {
      historyExists: true,
      historyEvents: 2,
      errors: [],
      errorCount: 0,
      findings: [],
      findingCount: 0,
      findingTypes: [],
      integrityValid: true,
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
}

function runVerifier(dir) {
  const result = spawnSync(
    process.execPath,
    [VERIFIER],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OBSERVER_OUTPUT: dir,
      },
      encoding: "utf8",
    },
  );

  assert.equal(
    result.error,
    undefined,
    result.error ? String(result.error) : "",
  );

  const outputFile = path.join(
    dir,
    "latest-provider-watch-history-integrity-audit-verify.json",
  );

  assert.equal(
    fs.existsSync(outputFile),
    true,
    `missing verifier output: ${outputFile}`,
  );

  return JSON.parse(
    fs.readFileSync(outputFile, "utf8"),
  );
}

function assertSafety(report) {
  assert.equal(report.mode, "READ_ONLY");
  assert.equal(report.executionAuthorized, false);

  for (const field of [
    "postPerformed",
    "walletUsed",
    "signingPerformed",
    "broadcastPerformed",
    "submissionPerformed",
  ]) {
    assert.equal(
      report.safety[field],
      false,
    );

    assert.equal(
      report.sideEffects[field],
      false,
    );
  }

  assert.equal(report.safety.executionAuthorized, false);

  assert.equal(report.policy.readOnly, true);
  assert.equal(report.policy.failClosed, true);
  assert.equal(report.policy.post, "NOT_PERFORMED");
  assert.equal(report.policy.wallet, "NOT_USED");
  assert.equal(report.policy.signing, "NOT_PERFORMED");
  assert.equal(report.policy.broadcast, "NOT_PERFORMED");
  assert.equal(report.policy.submission, "NOT_PERFORMED");
}

function testSafeAudit() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p18-safe-"),
  );

  try {
    writeJson(
      path.join(
        dir,
        "latest-provider-watch-history-integrity-audit.json",
      ),
      safeAudit(),
    );

    const report = runVerifier(dir);

    assert.equal(
      report.state,
      "VERIFIED_READ_ONLY",
    );

    assert.equal(
      report.verification.valid,
      true,
    );

    assert.equal(
      report.verification.errorCount,
      0,
    );

    assertSafety(report);

    console.log(
      "PASS: safe audit → VERIFIED_READ_ONLY",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function testMissingAudit() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p18-missing-"),
  );

  try {
    const report = runVerifier(dir);

    assert.equal(report.state, "INCOMPLETE");
    assert.equal(
      report.verification.valid,
      false,
    );

    assert.ok(
      report.verification.errors.includes(
        "audit_missing",
      ),
    );

    assertSafety(report);

    console.log(
      "PASS: missing audit → INCOMPLETE",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function testExecutionAuthorized() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p18-exec-"),
  );

  try {
    const audit = safeAudit();

    audit.executionAuthorized = true;

    writeJson(
      path.join(
        dir,
        "latest-provider-watch-history-integrity-audit.json",
      ),
      audit,
    );

    const report = runVerifier(dir);

    assert.equal(report.state, "BLOCKED");
    assert.equal(
      report.verification.valid,
      false,
    );

    assert.ok(
      report.verification.errors.includes(
        "execution_authorized",
      ),
    );

    assertSafety(report);

    console.log(
      "PASS: executionAuthorized=true → BLOCKED",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function testSigningPerformed() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p18-signing-"),
  );

  try {
    const audit = safeAudit();

    audit.safety.signingPerformed = true;

    writeJson(
      path.join(
        dir,
        "latest-provider-watch-history-integrity-audit.json",
      ),
      audit,
    );

    const report = runVerifier(dir);

    assert.equal(report.state, "BLOCKED");

    assert.ok(
      report.verification.errors.includes(
        "unsafe_safety",
      ),
    );

    assertSafety(report);

    console.log(
      "PASS: signingPerformed=true → BLOCKED",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function testCountMismatch() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p18-count-"),
  );

  try {
    const audit = safeAudit();

    audit.integrity.errorCount = 1;

    writeJson(
      path.join(
        dir,
        "latest-provider-watch-history-integrity-audit.json",
      ),
      audit,
    );

    const report = runVerifier(dir);

    assert.equal(report.state, "BLOCKED");

    assert.ok(
      report.verification.errors.includes(
        "error_count_mismatch",
      ),
    );

    assertSafety(report);

    console.log(
      "PASS: integrity count mismatch → BLOCKED",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function testStateMismatch() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p18-state-"),
  );

  try {
    const audit = safeAudit();

    audit.sourceState = "BLOCKED";

    writeJson(
      path.join(
        dir,
        "latest-provider-watch-history-integrity-audit.json",
      ),
      audit,
    );

    const report = runVerifier(dir);

    assert.equal(report.state, "BLOCKED");

    assert.ok(
      report.verification.errors.includes(
        "state_source_state_mismatch",
      ),
    );

    assertSafety(report);

    console.log(
      "PASS: state/sourceState mismatch → BLOCKED",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function testSafetyInvariants() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p18-safety-"),
  );

  try {
    writeJson(
      path.join(
        dir,
        "latest-provider-watch-history-integrity-audit.json",
      ),
      safeAudit(),
    );

    const report = runVerifier(dir);

    assertSafety(report);

    console.log(
      "PASS: integrity report verifier safety invariants",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function main() {
  testSafeAudit();
  testMissingAudit();
  testExecutionAuthorized();
  testSigningPerformed();
  testCountMismatch();
  testStateMismatch();
  testSafetyInvariants();

  console.log(
    "ALL PROVIDER WATCH HISTORY INTEGRITY REPORT VERIFIER TESTS PASSED",
  );
}

main();
