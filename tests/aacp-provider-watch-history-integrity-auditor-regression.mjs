import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const AUDITOR = path.join(
  ROOT,
  "src/aacp-provider-watch-history-integrity-auditor.mjs",
);

const SIDE_EFFECT_FIELDS = [
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
];

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(
    file,
    `${JSON.stringify(value, null, 2)}\n`,
    "utf8",
  );
}

function safeEvent({
  eventId = "event-1",
  generatedAt = "2026-09-08T00:00:00.000Z",
  state = "VERIFIED_READ_ONLY",
  changed = false,
  changedFields = [],
} = {}) {
  return {
    eventId,
    generatedAt,
    state,
    sourceState: state,
    changed,
    changedFields,

    executionAuthorized: false,

    fingerprint: {
      state,
      sourceState: state,
      mode: "READ_ONLY",
      executionAuthorized: false,
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false,
    },
  };
}

function buildHistory(events) {
  return {
    version: "1.0.0",
    generatedAt: "2026-09-08T00:01:00.000Z",
    mode: "READ_ONLY",
    state: events.at(-1)?.state || "VERIFIED_READ_ONLY",
    sourceState: events.at(-1)?.sourceState || "VERIFIED_READ_ONLY",
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

    events,
  };
}

function safeReport({
  state = "VERIFIED_READ_ONLY",
  historySha256 = null,
  analysisSha256 = null,
} = {}) {
  const report = {
    version: "1.0.0",
    generatedAt: "2026-09-08T00:02:00.000Z",
    mode: "READ_ONLY",
    state,
    sourceState: state,
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
  };

  if (historySha256) {
    report.historySha256 = historySha256;
  }

  if (analysisSha256) {
    report.analysisSha256 = analysisSha256;
  }

  return report;
}

function buildAnalysis({
  state = "VERIFIED_READ_ONLY",
  historySha256,
  events = 1,
  transitions = 0,
  changedEvents = 0,
  unsafeEvents = 0,
  anomalies = [],
  errors = [],
} = {}) {
  return {
    version: "1.0.0",
    generatedAt: "2026-09-08T00:03:00.000Z",
    mode: "READ_ONLY",
    state,
    sourceState: state,
    executionAuthorized: false,

    source: {
      historySha256,
    },

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

    analysis: {
      events,
      transitions,
      changedEvents,
      unsafeEvents,
      anomalies,
      errors,
      firstTimestamp: "2026-09-08T00:00:00.000Z",
      lastTimestamp: "2026-09-08T00:00:00.000Z",
    },
  };
}

function runAuditor(dir) {
  const result = spawnSync(
    process.execPath,
    [AUDITOR],
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

  return {
    stdout: result.stdout,
    stderr: result.stderr,
    status: result.status,
    reportFile: path.join(
      dir,
      "latest-provider-watch-history-integrity-audit.json",
    ),
  };
}

function readReport(file) {
  assert.equal(
    fs.existsSync(file),
    true,
    `missing report: ${file}`,
  );

  return JSON.parse(
    fs.readFileSync(file, "utf8"),
  );
}

function assertSafety(report) {
  assert.equal(report.mode, "READ_ONLY");
  assert.equal(report.executionAuthorized, false);

  assert.equal(
    report.safety.executionAuthorized,
    false,
  );

  for (const field of SIDE_EFFECT_FIELDS) {
    assert.equal(
      report.safety[field],
      false,
      `unsafe safety flag: ${field}`,
    );

    assert.equal(
      report.sideEffects[field],
      false,
      `unsafe side effect: ${field}`,
    );
  }

  assert.equal(report.policy.readOnly, true);
  assert.equal(report.policy.failClosed, true);
  assert.equal(report.policy.post, "NOT_PERFORMED");
  assert.equal(report.policy.wallet, "NOT_USED");
  assert.equal(report.policy.signing, "NOT_PERFORMED");
  assert.equal(report.policy.broadcast, "NOT_PERFORMED");
  assert.equal(report.policy.submission, "NOT_PERFORMED");
}

function prepareSafeChain(dir) {
  const events = [
    safeEvent({
      eventId: "event-1",
      generatedAt: "2026-09-08T00:00:00.000Z",
    }),
    safeEvent({
      eventId: "event-2",
      generatedAt: "2026-09-08T00:01:00.000Z",
      changed: true,
      changedFields: ["state"],
    }),
  ];

  const history = buildHistory(events);

  writeJson(
    path.join(dir, "latest-provider-watch-history.json"),
    history,
  );

  const historyFile = path.join(
    dir,
    "latest-provider-watch-history.json",
  );

  const historySha256 = sha256File(historyFile);

  writeJson(
    path.join(
      dir,
      "latest-provider-watch-history-verify.json",
    ),
    {
      version: "1.0.0",
      generatedAt: "2026-09-08T00:04:00.000Z",
      mode: "READ_ONLY",
      state: "VERIFIED_READ_ONLY",
      sourceState: "VERIFIED_READ_ONLY",
      executionAuthorized: false,
      events: 2,
      historySha256,

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
    },
  );

  const analysis = buildAnalysis({
    historySha256,
    events: 2,
    transitions: 1,
    changedEvents: 1,
  });

  writeJson(
    path.join(
      dir,
      "latest-provider-watch-history-analysis.json",
    ),
    analysis,
  );

  const analysisFile = path.join(
    dir,
    "latest-provider-watch-history-analysis.json",
  );

  const analysisSha256 = sha256File(analysisFile);

  writeJson(
    path.join(
      dir,
      "latest-provider-watch-history-analysis-verify.json",
    ),
    safeReport({
      historySha256,
      analysisSha256,
    }),
  );

  writeJson(
    path.join(
      dir,
      "latest-provider-watch-history-chain-verify.json",
    ),
    safeReport({
      state: "VERIFIED_READ_ONLY",
      historySha256,
    }),
  );
}

function testSafeChain() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p17-safe-"),
  );

  try {
    prepareSafeChain(dir);

    const result = runAuditor(dir);
    assert.equal(result.status, 0);

    const report = readReport(result.reportFile);

    assert.equal(
      report.state,
      "VERIFIED_READ_ONLY",
    );

    assert.equal(
      report.integrity.integrityValid,
      true,
    );

    assert.equal(
      report.integrity.errorCount,
      0,
    );

    assert.equal(
      report.integrity.historyEvents,
      2,
    );

    assertSafety(report);

    console.log(
      "PASS: safe chain → VERIFIED_READ_ONLY",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function testMissingHistory() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p17-missing-"),
  );

  try {
    const result = runAuditor(dir);
    assert.equal(result.status, 0);

    const report = readReport(result.reportFile);

    assert.equal(report.state, "BLOCKED");
    assert.equal(
      report.integrity.integrityValid,
      false,
    );

    assert.ok(
      report.integrity.errors.includes(
        "history_missing",
      ),
    );

    assertSafety(report);

    console.log(
      "PASS: missing history → BLOCKED",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function testHashMismatch() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p17-hash-"),
  );

  try {
    prepareSafeChain(dir);

    const verifyFile = path.join(
      dir,
      "latest-provider-watch-history-verify.json",
    );

    const verify = JSON.parse(
      fs.readFileSync(verifyFile, "utf8"),
    );

    verify.historySha256 =
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

    writeJson(verifyFile, verify);

    const result = runAuditor(dir);
    const report = readReport(result.reportFile);

    assert.equal(report.state, "BLOCKED");
    assert.equal(
      report.integrity.integrityValid,
      false,
    );

    assert.ok(
      report.integrity.errors.some(
        (error) =>
          error.startsWith("history_hash_mismatch"),
      ),
    );

    assertSafety(report);

    console.log(
      "PASS: SHA-256 mismatch → BLOCKED",
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
    path.join(os.tmpdir(), "termix-p17-exec-"),
  );

  try {
    prepareSafeChain(dir);

    const analysisFile = path.join(
      dir,
      "latest-provider-watch-history-analysis.json",
    );

    const analysis = JSON.parse(
      fs.readFileSync(analysisFile, "utf8"),
    );

    analysis.executionAuthorized = true;

    writeJson(analysisFile, analysis);

    const result = runAuditor(dir);
    const report = readReport(result.reportFile);

    assert.equal(report.state, "BLOCKED");
    assert.equal(
      report.integrity.integrityValid,
      false,
    );

    assert.ok(
      report.integrity.errors.includes(
        "analysis_execution_authorized",
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
    path.join(os.tmpdir(), "termix-p17-signing-"),
  );

  try {
    prepareSafeChain(dir);

    const chainFile = path.join(
      dir,
      "latest-provider-watch-history-chain-verify.json",
    );

    const chain = JSON.parse(
      fs.readFileSync(chainFile, "utf8"),
    );

    chain.safety.signingPerformed = true;

    writeJson(chainFile, chain);

    const result = runAuditor(dir);
    const report = readReport(result.reportFile);

    assert.equal(report.state, "BLOCKED");
    assert.equal(
      report.integrity.integrityValid,
      false,
    );

    assert.ok(
      report.integrity.errors.includes(
        "chain_verify_unsafe_safety",
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

function testStateMismatch() {
  const dir = fs.mkdtempSync(
    path.join(os.tmpdir(), "termix-p17-state-"),
  );

  try {
    prepareSafeChain(dir);

    const chainFile = path.join(
      dir,
      "latest-provider-watch-history-chain-verify.json",
    );

    const chain = JSON.parse(
      fs.readFileSync(chainFile, "utf8"),
    );

    chain.state = "BLOCKED";
    chain.sourceState = "BLOCKED";

    writeJson(chainFile, chain);

    const result = runAuditor(dir);
    const report = readReport(result.reportFile);

    assert.equal(report.state, "BLOCKED");
    assert.equal(
      report.integrity.integrityValid,
      false,
    );

    assert.ok(
      report.integrity.errors.includes(
        "cross_layer_state_mismatch",
      ),
    );

    assertSafety(report);

    console.log(
      "PASS: state mismatch → BLOCKED",
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
    path.join(os.tmpdir(), "termix-p17-safety-"),
  );

  try {
    prepareSafeChain(dir);

    const result = runAuditor(dir);
    const report = readReport(result.reportFile);

    assertSafety(report);

    console.log(
      "PASS: integrity auditor safety invariants",
    );
  } finally {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
    });
  }
}

function main() {
  testSafeChain();
  testMissingHistory();
  testHashMismatch();
  testExecutionAuthorized();
  testSigningPerformed();
  testStateMismatch();
  testSafetyInvariants();

  console.log(
    "ALL PROVIDER WATCH HISTORY INTEGRITY AUDITOR TESTS PASSED",
  );
}

main();
