import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const SCRIPT = path.join(
  ROOT,
  "src/aacp-provider-watch-history-chain-verifier.mjs"
);

const TMP = fs.mkdtempSync(
  path.join(
    os.tmpdir(),
    "aacp-chain-verifier-"
  )
);

const OUT = path.join(
  TMP,
  "provider-output"
);

fs.mkdirSync(OUT, { recursive: true });

function write(name, data) {
  fs.writeFileSync(
    path.join(OUT, name),
    JSON.stringify(data, null, 2)
  );
}

function run() {
  return spawnSync(
    process.execPath,
    [SCRIPT],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OBSERVER_OUTPUT: OUT,
      },
      encoding: "utf8",
    }
  );
}

function report() {
  const file = path.join(
    OUT,
    "latest-provider-watch-history-chain-verify.json"
  );

  return JSON.parse(
    fs.readFileSync(file, "utf8")
  );
}

function baseSafety() {
  return {
    executionAuthorized: false,
    postPerformed: false,
    walletUsed: false,
    signingPerformed: false,
    broadcastPerformed: false,
    submissionPerformed: false,
  };
}

function baseSideEffects() {
  return {
    postPerformed: false,
    walletUsed: false,
    signingPerformed: false,
    broadcastPerformed: false,
    submissionPerformed: false,
  };
}

function history() {
  return {
    events: [
      {
        eventId: "event-1",
        generatedAt: "2026-09-08T00:00:00.000Z",
        state: "READY_READ_ONLY",
        changed: false,
      },
    ],
  };
}

function verifyHistory(historySha) {
  return {
    version: "1.0.0",
    mode: "READ_ONLY",
    state: "VERIFIED_READ_ONLY",
    executionAuthorized: false,
    historySha256: historySha,
    safety: baseSafety(),
    sideEffects: baseSideEffects(),
    events: history().events,
  };
}

function analysis(historySha) {
  return {
    version: "1.0.0",
    mode: "READ_ONLY",
    state: "VERIFIED_READ_ONLY",
    executionAuthorized: false,
    historySha256: historySha,
    safety: baseSafety(),
    sideEffects: baseSideEffects(),
    analysis: {
      events: 1,
      transitions: 0,
      changedEvents: 0,
      unsafeEvents: 0,
      anomalies: [],
      errors: [],
    },
  };
}

function analysisVerify(analysisSha, historySha) {
  return {
    version: "1.0.0",
    mode: "READ_ONLY",
    state: "VERIFIED_READ_ONLY",
    executionAuthorized: false,
    analysisSha256: analysisSha,
    historySha256: historySha,
    safety: baseSafety(),
    sideEffects: baseSideEffects(),
    analysis: {
      events: 1,
      transitions: 0,
      changedEvents: 0,
      unsafeEvents: 0,
      anomalies: [],
      errors: [],
    },
  };
}

function sha256File(file) {

  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function testSafeChain() {
  const h = path.join(
    OUT,
    "latest-provider-watch-history.json"
  );

  write(
    "latest-provider-watch-history.json",
    history()
  );

  const historySha = sha256File(h);

  write(
    "latest-provider-watch-history-verify.json",
    verifyHistory(historySha)
  );

  write(
    "latest-provider-watch-history-analysis.json",
    analysis(historySha)
  );

  const a = path.join(
    OUT,
    "latest-provider-watch-history-analysis.json"
  );

  const analysisSha =
    sha256File(a);

  write(
    "latest-provider-watch-history-analysis-verify.json",
    analysisVerify(
      analysisSha,
      historySha
    )
  );

  const result = run();

  assert(
    result.status === 0,
    "safe chain process failed"
  );

  const r = report();

  assert(
    r.state === "VERIFIED_READ_ONLY",
    "safe chain should verify"
  );

  assert(
    r.executionAuthorized === false,
    "execution must remain unauthorized"
  );

  console.log(
    "PASS: safe chain → VERIFIED_READ_ONLY"
  );
}

async function testMissingLayer() {
  fs.rmSync(
    path.join(
      OUT,
      "latest-provider-watch-history.json"
    ),
    { force: true }
  );

  const result = run();
  assert(
    result.status === 0,
    "missing layer process failed"
  );

  const r = report();

  assert(
    r.state === "BLOCKED",
    "missing chain layer must block"
  );

  console.log(
    "PASS: missing history → BLOCKED"
  );

  await testSafeChain();
}

async function testHashMismatch() {
  const file = path.join(
    OUT,
    "latest-provider-watch-history-analysis-verify.json"
  );

  const data = JSON.parse(
    fs.readFileSync(file, "utf8")
  );

  data.historySha256 =
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

  write(
    "latest-provider-watch-history-analysis-verify.json",
    data
  );

  const result = run();
  const r = report();

  assert(
    r.state === "BLOCKED",
    "hash mismatch must block"
  );

  assert(
    r.errors.some((x) =>
      x.includes("SHA256")
    ),
    "hash mismatch error must be recorded"
  );

  console.log(
    "PASS: SHA-256 mismatch → BLOCKED"
  );
}

async function testUnsafeExecution() {
  const file = path.join(
    OUT,
    "latest-provider-watch-history-analysis.json"
  );

  const data = JSON.parse(
    fs.readFileSync(file, "utf8")
  );

  data.executionAuthorized = true;

  write(
    "latest-provider-watch-history-analysis.json",
    data
  );

  const result = run();
  const r = report();

  assert(
    r.state === "BLOCKED",
    "executionAuthorized=true must block"
  );

  console.log(
    "PASS: executionAuthorized=true → BLOCKED"
  );

  await testSafeChain();
}

async function testUnsafeSigning() {
  const file = path.join(
    OUT,
    "latest-provider-watch-history-analysis.json"
  );

  const data = JSON.parse(
    fs.readFileSync(file, "utf8")
  );

  data.safety.signingPerformed = true;

  write(
    "latest-provider-watch-history-analysis.json",
    data
  );

  const result = run();
  const r = report();

  assert(
    r.state === "BLOCKED",
    "signingPerformed=true must block"
  );

  console.log(
    "PASS: signingPerformed=true → BLOCKED"
  );

  await testSafeChain();
}

async function testStateMismatch() {
  const file = path.join(
    OUT,
    "latest-provider-watch-history-analysis-verify.json"
  );

  const data = JSON.parse(
    fs.readFileSync(file, "utf8")
  );

  data.state = "BLOCKED";

  write(
    "latest-provider-watch-history-analysis-verify.json",
    data
  );

  const result = run();
  const r = report();

  assert(
    r.state === "BLOCKED",
    "state mismatch must block"
  );

  console.log(
    "PASS: state mismatch → BLOCKED"
  );
}

async function main() {
  try {
    await testSafeChain();
    await testMissingLayer();
    await testHashMismatch();
    await testUnsafeExecution();
    await testUnsafeSigning();
    await testStateMismatch();

    console.log(
      "PASS: chain verifier safety invariants"
    );

    console.log(
      "ALL PROVIDER WATCH HISTORY CHAIN VERIFIER TESTS PASSED"
    );
  } finally {
    fs.rmSync(TMP, {
      recursive: true,
      force: true,
    });
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
