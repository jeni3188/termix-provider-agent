import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const SCRIPT = path.join(
  ROOT,
  "src/aacp-provider-watch-history-analyzer.mjs"
);

const tempDir = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-watch-history-analyzer-")
);

const historyFile = path.join(
  tempDir,
  "latest-provider-watch-history.json"
);

const verifyFile = path.join(
  tempDir,
  "latest-provider-watch-history-verify.json"
);

const analysisFile = path.join(
  tempDir,
  "latest-provider-watch-history-analysis.json"
);

function run() {
  return spawnSync(
    process.execPath,
    [SCRIPT],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OBSERVER_OUTPUT: tempDir,
      },
      encoding: "utf8",
    }
  );
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(`FAIL: ${message}`);
  }

  console.log(`PASS: ${message}`);
}

function readReport() {
  return JSON.parse(
    fs.readFileSync(analysisFile, "utf8")
  );
}

function writeHistory(events) {
  fs.writeFileSync(
    historyFile,
    JSON.stringify(
      {
        version: "1.0.0",
        mode: "READ_ONLY",
        events,
      },
      null,
      2
    )
  );
}

function baseEvent(overrides = {}) {
  const now = new Date().toISOString();

  return {
    id: crypto.randomUUID(),
    generatedAt: now,
    state: "VERIFIED_READ_ONLY",
    changed: false,
    changedFields: [],
    watch: {
      exists: true,
      valid: true,
      sha256: "a".repeat(64),
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

try {
  fs.rmSync(historyFile, {
    force: true,
  });

  fs.rmSync(verifyFile, {
    force: true,
  });

  fs.rmSync(analysisFile, {
    force: true,
  });

  let result = run();
  let report = readReport();

  assert(
    result.status === 0,
    "missing history analyzer exits cleanly"
  );

  assert(
    report.state === "INCOMPLETE",
    "missing history → INCOMPLETE"
  );

  const first = baseEvent();

  writeHistory([first]);

  result = run();
  report = readReport();

  assert(
    report.state === "VERIFIED_READ_ONLY",
    "single safe event → VERIFIED_READ_ONLY"
  );

  assert(
    report.analysis.events === 1,
    "single event counted"
  );

  const second = baseEvent({
    generatedAt: new Date(
      Date.now() + 1000
    ).toISOString(),
  });

  writeHistory([first, second]);

  result = run();
  report = readReport();

  assert(
    report.state === "VERIFIED_READ_ONLY",
    "unchanged safe history remains VERIFIED_READ_ONLY"
  );

  assert(
    report.analysis.transitions === 0,
    "unchanged state → zero transitions"
  );

  const transition = baseEvent({
    generatedAt: new Date(
      Date.now() + 2000
    ).toISOString(),
    state: "READY_READ_ONLY",
    fingerprint: {
      ...second.fingerprint,
      state: "READY_READ_ONLY",
    },
  });

  writeHistory([
    first,
    second,
    transition,
  ]);

  result = run();
  report = readReport();

  assert(
    report.analysis.transitions === 1,
    "state transition detected"
  );

  assert(
    report.analysis.anomalies.some(
      (item) =>
        item.type === "STATE_TRANSITION"
    ),
    "state transition anomaly recorded"
  );

  const unsafe = baseEvent({
    generatedAt: new Date(
      Date.now() + 3000
    ).toISOString(),
    safety: {
      executionAuthorized: false,
      postPerformed: false,
      walletUsed: false,
      signingPerformed: true,
      broadcastPerformed: false,
      submissionPerformed: false,
    },
  });

  writeHistory([first, unsafe]);

  result = run();
  report = readReport();

  assert(
    report.state === "BLOCKED",
    "unsafe signing → BLOCKED"
  );

  assert(
    report.analysis.unsafeEvents === 1,
    "unsafe event counted"
  );

  const unauthorized = baseEvent({
    generatedAt: new Date(
      Date.now() + 4000
    ).toISOString(),
    executionAuthorized: true,
    fingerprint: {
      ...first.fingerprint,
      executionAuthorized: true,
    },
  });

  writeHistory([
    first,
    unauthorized,
  ]);

  result = run();
  report = readReport();

  assert(
    report.state === "BLOCKED",
    "executionAuthorized=true → BLOCKED"
  );

  const badChronology = baseEvent({
    generatedAt: "2026-01-01T00:00:00.000Z",
  });

  const later = baseEvent({
    generatedAt: "2025-01-01T00:00:00.000Z",
  });

  writeHistory([
    badChronology,
    later,
  ]);

  result = run();
  report = readReport();

  assert(
    report.state === "BLOCKED",
    "invalid chronology → BLOCKED"
  );

  const unchangedFlag = baseEvent({
    generatedAt: new Date(
      Date.now() + 5000
    ).toISOString(),
    changed: false,
    fingerprint: {
      ...first.fingerprint,
      state: "READY_READ_ONLY",
    },
  });

  writeHistory([
    first,
    unchangedFlag,
  ]);

  result = run();
  report = readReport();

  assert(
    report.analysis.anomalies.some(
      (item) =>
        item.type ===
        "FINGERPRINT_CHANGE_WITHOUT_CHANGED_FLAG"
    ),
    "fingerprint mismatch anomaly detected"
  );

  const safety =
    report.safety || {};

  assert(
    safety.executionAuthorized === false &&
      safety.postPerformed === false &&
      safety.walletUsed === false &&
      safety.signingPerformed === false &&
      safety.broadcastPerformed === false &&
      safety.submissionPerformed === false,
    "analyzer safety invariants"
  );

  assert(
    report.executionAuthorized === false,
    "executionAuthorized=false"
  );

  assert(
    fs.existsSync(analysisFile),
    "analysis report generated"
  );

  console.log(
    "ALL PROVIDER WATCH HISTORY ANALYZER TESTS PASSED"
  );
} finally {
  fs.rmSync(tempDir, {
    recursive: true,
    force: true,
  });
}
