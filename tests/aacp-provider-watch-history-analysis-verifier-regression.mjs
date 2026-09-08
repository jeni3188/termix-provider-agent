import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();

const ANALYZER =
  path.join(
    ROOT,
    "src/aacp-provider-watch-history-analyzer.mjs"
  );

const VERIFIER =
  path.join(
    ROOT,
    "src/aacp-provider-watch-history-analysis-verifier.mjs"
  );

const tempDir = fs.mkdtempSync(
  path.join(
    os.tmpdir(),
    "aacp-analysis-verifier-"
  )
);

const analysisFile = path.join(
  tempDir,
  "latest-provider-watch-history-analysis.json"
);

const verifyFile = path.join(
  tempDir,
  "latest-provider-watch-history-analysis-verify.json"
);

function run(file) {
  return spawnSync(
    process.execPath,
    [file],
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
    throw new Error(message);
  }
}

function write(data) {
  fs.writeFileSync(
    analysisFile,
    `${JSON.stringify(data, null, 2)}\n`,
    "utf8"
  );
}

function baseReport() {
  return {
    version: "1.0.0",
    generatedAt: new Date().toISOString(),

    mode: "READ_ONLY",
    state: "VERIFIED_READ_ONLY",

    source: {
      historyExists: true,
      historyValid: true,
      historySha256:
        crypto
          .createHash("sha256")
          .update("safe-history")
          .digest("hex"),
      verifierExists: true,
      verifierValid: true,
    },

    analysis: {
      reason: "safe",
      events: 2,
      transitions: 1,
      changedEvents: 1,
      unsafeEvents: 0,
      uniqueStates: [
        "READY_READ_ONLY",
        "VERIFIED_READ_ONLY",
      ],
      firstEventAt:
        "2026-09-08T00:00:00.000Z",
      lastEventAt:
        "2026-09-08T00:01:00.000Z",
      anomalies: [
        {
          type: "STATE_TRANSITION",
          index: 1,
          eventId: crypto.randomUUID(),
          from: "READY_READ_ONLY",
          to: "VERIFIED_READ_ONLY",
        },
      ],
      errors: [],
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
  };
}

try {
  fs.rmSync(analysisFile, {
    force: true,
  });

  let result = run(VERIFIER);

  assert(
    result.status === 0,
    "missing analysis verifier should exit cleanly"
  );

  let report = JSON.parse(
    fs.readFileSync(
      verifyFile,
      "utf8"
    )
  );

  assert(
    report.state === "INCOMPLETE",
    "missing analysis → INCOMPLETE"
  );

  console.log(
    "PASS: missing analysis → INCOMPLETE"
  );

  write(baseReport());

  result = run(VERIFIER);

  assert(
    result.status === 0,
    "safe analysis verifier should exit cleanly"
  );

  report = JSON.parse(
    fs.readFileSync(
      verifyFile,
      "utf8"
    )
  );

  assert(
    report.state === "VERIFIED_READ_ONLY",
    "safe analysis → VERIFIED_READ_ONLY"
  );

  console.log(
    "PASS: safe analysis → VERIFIED_READ_ONLY"
  );

  let unsafe = baseReport();

  unsafe.executionAuthorized = true;

  write(unsafe);

  run(VERIFIER);

  report = JSON.parse(
    fs.readFileSync(
      verifyFile,
      "utf8"
    )
  );

  assert(
    report.state === "BLOCKED",
    "executionAuthorized=true → BLOCKED"
  );

  console.log(
    "PASS: executionAuthorized=true → BLOCKED"
  );

  unsafe = baseReport();

  unsafe.safety.signingPerformed = true;

  write(unsafe);

  run(VERIFIER);

  report = JSON.parse(
    fs.readFileSync(
      verifyFile,
      "utf8"
    )
  );

  assert(
    report.state === "BLOCKED",
    "signingPerformed=true → BLOCKED"
  );

  console.log(
    "PASS: signingPerformed=true → BLOCKED"
  );

  unsafe = baseReport();

  unsafe.analysis.unsafeEvents = 1;

  write(unsafe);

  run(VERIFIER);

  report = JSON.parse(
    fs.readFileSync(
      verifyFile,
      "utf8"
    )
  );

  assert(
    report.state === "BLOCKED",
    "unsafe events marked verified → BLOCKED"
  );

  console.log(
    "PASS: unsafe events → BLOCKED"
  );

  unsafe = baseReport();

  unsafe.analysis.events = 0;

  write(unsafe);

  run(VERIFIER);

  report = JSON.parse(
    fs.readFileSync(
      verifyFile,
      "utf8"
    )
  );

  assert(
    report.state === "BLOCKED",
    "zero events marked verified → BLOCKED"
  );

  console.log(
    "PASS: zero events + verified → BLOCKED"
  );

  unsafe = baseReport();

  unsafe.analysis.firstEventAt =
    "2026-09-08T00:02:00.000Z";

  unsafe.analysis.lastEventAt =
    "2026-09-08T00:01:00.000Z";

  write(unsafe);

  run(VERIFIER);

  report = JSON.parse(
    fs.readFileSync(
      verifyFile,
      "utf8"
    )
  );

  assert(
    report.state === "BLOCKED",
    "invalid event range → BLOCKED"
  );

  console.log(
    "PASS: invalid event range → BLOCKED"
  );

  unsafe = baseReport();

  unsafe.source.historySha256 =
    "not-a-sha256";

  write(unsafe);

  run(VERIFIER);

  report = JSON.parse(
    fs.readFileSync(
      verifyFile,
      "utf8"
    )
  );

  assert(
    report.state === "BLOCKED",
    "invalid SHA-256 → BLOCKED"
  );

  console.log(
    "PASS: invalid SHA-256 → BLOCKED"
  );

  report = JSON.parse(
    fs.readFileSync(
      verifyFile,
      "utf8"
    )
  );

  assert(
    report.mode === "READ_ONLY",
    "verifier mode must remain READ_ONLY"
  );

  assert(
    report.executionAuthorized === false,
    "verifier executionAuthorized must remain false"
  );

  for (
    const value of Object.values(
      report.safety
    )
  ) {
    assert(
      value === false,
      "verifier safety invariant violated"
    );
  }

  for (
    const value of Object.values(
      report.sideEffects
    )
  ) {
    assert(
      value === false,
      "verifier side-effect invariant violated"
    );
  }

  console.log(
    "PASS: verifier safety invariants"
  );

  console.log(
    "ALL PROVIDER WATCH HISTORY ANALYSIS VERIFIER TESTS PASSED"
  );
} finally {
  fs.rmSync(tempDir, {
    recursive: true,
    force: true,
  });
}
