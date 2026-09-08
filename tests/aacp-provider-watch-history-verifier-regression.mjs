import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const SCRIPT = path.join(
  ROOT,
  "src",
  "aacp-provider-watch-history-verifier.mjs"
);

const TMP = fs.mkdtempSync(
  path.join(
    os.tmpdir(),
    "aacp-watch-history-verify-"
  )
);

const HISTORY = path.join(
  TMP,
  "latest-provider-watch-history.json"
);

const VERIFY = path.join(
  TMP,
  "latest-provider-watch-history-verify.json"
);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function runVerifier() {
  return spawnSync(
    process.execPath,
    [SCRIPT],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OBSERVER_OUTPUT: TMP,
      },
      encoding: "utf8",
    }
  );
}

function writeHistory(data) {
  fs.writeFileSync(
    HISTORY,
    `${JSON.stringify(data, null, 2)}\n`,
    "utf8"
  );
}

function readReport() {
  return JSON.parse(
    fs.readFileSync(VERIFY, "utf8")
  );
}

function baseEvent(overrides = {}) {
  return {
    id: crypto.randomUUID(),
    generatedAt:
      "2026-09-08T00:00:00.000Z",
    state: "VERIFIED_READ_ONLY",
    changed: true,
    changedFields: [
      "INITIAL_SNAPSHOT",
    ],
    watch: {
      exists: true,
      valid: true,
      sha256: "test",
    },
    fingerprint: {
      state: "VERIFIED_READ_ONLY",
      sourceState: "VERIFIED_READ_ONLY",
      mode: "READ_ONLY",
      executionAuthorized: false,
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false,
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
    executionAuthorized: false,
    ...overrides,
  };
}

function historyWithEvent(event) {
  return {
    version: "1.0.0",
    mode: "READ_ONLY",
    events: [event],
  };
}

function testMissingHistory() {
  fs.rmSync(HISTORY, {
    force: true,
  });

  const result = runVerifier();

  assert(
    result.status === 0,
    "missing history verifier crashed"
  );

  const report = readReport();

  assert(
    report.state === "INCOMPLETE",
    "missing history should be INCOMPLETE"
  );

  console.log(
    "PASS: missing history → INCOMPLETE"
  );
}

function testInvalidJson() {
  fs.writeFileSync(
    HISTORY,
    "{invalid-json",
    "utf8"
  );

  const result = runVerifier();

  assert(
    result.status === 0,
    "invalid JSON verifier crashed"
  );

  const report = readReport();

  assert(
    report.state === "BLOCKED",
    "invalid JSON should be BLOCKED"
  );

  console.log(
    "PASS: invalid JSON → BLOCKED"
  );
}

function testEmptyHistory() {
  writeHistory({
    version: "1.0.0",
    events: [],
  });

  runVerifier();

  const report = readReport();

  assert(
    report.state === "INCOMPLETE",
    "empty history should be INCOMPLETE"
  );

  console.log(
    "PASS: empty history → INCOMPLETE"
  );
}

function testValidHistory() {
  writeHistory(
    historyWithEvent(
      baseEvent()
    )
  );

  runVerifier();

  const report = readReport();

  assert(
    report.state === "VERIFIED_READ_ONLY",
    "valid history should verify"
  );

  assert(
    report.integrity.verified === true,
    "integrity should be verified"
  );

  assert(
    report.integrity.fingerprintVerified === true,
    "fingerprint should verify"
  );

  console.log(
    "PASS: valid history → VERIFIED_READ_ONLY"
  );
}

function testDuplicateId() {
  const event = baseEvent();

  writeHistory({
    version: "1.0.0",
    events: [
      event,
      {
        ...event,
        generatedAt:
          "2026-09-08T00:01:00.000Z",
      },
    ],
  });

  runVerifier();

  const report = readReport();

  assert(
    report.state === "BLOCKED",
    "duplicate event ID should be BLOCKED"
  );

  console.log(
    "PASS: duplicate event ID → BLOCKED"
  );
}

function testUnsafeSigning() {
  writeHistory(
    historyWithEvent(
      baseEvent({
        fingerprint: {
          ...baseEvent().fingerprint,
          signingPerformed: true,
        },
      })
    )
  );

  runVerifier();

  const report = readReport();

  assert(
    report.state === "BLOCKED",
    "unsafe signing should be BLOCKED"
  );

  console.log(
    "PASS: unsafe signing → BLOCKED"
  );
}

function testExecutionAuthorized() {
  writeHistory(
    historyWithEvent(
      baseEvent({
        executionAuthorized: true,
      })
    )
  );

  runVerifier();

  const report = readReport();

  assert(
    report.state === "BLOCKED",
    "executionAuthorized=true should be BLOCKED"
  );

  console.log(
    "PASS: executionAuthorized=true → BLOCKED"
  );
}

function testChronology() {
  const first = baseEvent({
    generatedAt:
      "2026-09-08T00:02:00.000Z",
  });

  const second = baseEvent({
    generatedAt:
      "2026-09-08T00:01:00.000Z",
  });

  writeHistory({
    version: "1.0.0",
    events: [first, second],
  });

  runVerifier();

  const report = readReport();

  assert(
    report.state === "BLOCKED",
    "chronology error should be BLOCKED"
  );

  console.log(
    "PASS: invalid chronology → BLOCKED"
  );
}

function testSafetyInvariant() {
  writeHistory(
    historyWithEvent(
      baseEvent()
    )
  );

  runVerifier();

  const report = readReport();

  assert(
    report.executionAuthorized === false,
    "executionAuthorized must be false"
  );

  assert(
    report.safety.postPerformed === false,
    "postPerformed must be false"
  );

  assert(
    report.safety.walletUsed === false,
    "walletUsed must be false"
  );

  assert(
    report.safety.signingPerformed === false,
    "signingPerformed must be false"
  );

  assert(
    report.safety.broadcastPerformed === false,
    "broadcastPerformed must be false"
  );

  assert(
    report.safety.submissionPerformed === false,
    "submissionPerformed must be false"
  );

  console.log(
    "PASS: verifier safety invariants"
  );
}

function testReportGenerated() {
  writeHistory(
    historyWithEvent(
      baseEvent()
    )
  );

  runVerifier();

  assert(
    fs.existsSync(VERIFY),
    "verification report was not generated"
  );

  console.log(
    "PASS: verification report generated"
  );
}

try {
  console.log(
    "AACP PROVIDER WATCH HISTORY VERIFIER REGRESSION"
  );

  testMissingHistory();
  testInvalidJson();
  testEmptyHistory();
  testValidHistory();
  testDuplicateId();
  testUnsafeSigning();
  testExecutionAuthorized();
  testChronology();
  testSafetyInvariant();
  testReportGenerated();

  console.log(
    "ALL PROVIDER WATCH HISTORY VERIFIER TESTS PASSED"
  );
} finally {
  fs.rmSync(TMP, {
    recursive: true,
    force: true,
  });
}
