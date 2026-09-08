import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import crypto from "node:crypto";

const ROOT = process.cwd();
const SOURCE = path.join(
  ROOT,
  "src/aacp-provider-evidence-manifest-verifier.mjs"
);

const OUTPUT_DIR = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-provider-manifest-verify-")
);

const MANIFEST = path.join(
  OUTPUT_DIR,
  "latest-provider-evidence-manifest.json"
);

const VERIFY = path.join(
  OUTPUT_DIR,
  "latest-provider-evidence-manifest-verify.json"
);

const FILES = [
  "latest-provider-watch-history.json",
  "latest-provider-watch-history-verify.json",
  "latest-provider-watch-history-analysis.json",
  "latest-provider-watch-history-analysis-verify.json",
  "latest-provider-watch-history-chain-verify.json",
  "latest-provider-watch-history-integrity-audit.json",
  "latest-provider-watch-history-integrity-audit-verify.json",
];

function assert(condition, message) {
  if (!condition) {
    throw new Error(`FAIL: ${message}`);
  }

  console.log(`PASS: ${message}`);
}

function sha256(text) {
  return crypto
    .createHash("sha256")
    .update(text)
    .digest("hex");
}

function writeJson(file, value) {
  fs.writeFileSync(
    path.join(OUTPUT_DIR, file),
    JSON.stringify(value, null, 2) + "\n",
    "utf8"
  );
}

function safeManifest() {
  const files = FILES.map((file, index) => {
    const content = `fixture-${index}-${file}`;

    fs.writeFileSync(
      path.join(OUTPUT_DIR, file),
      content,
      "utf8"
    );

    return {
      key: `fixture-${index}`,
      file,
      exists: true,
      sizeBytes: Buffer.byteLength(content),
      sha256: sha256(content),
    };
  });

  return {
    version: "1.0.0",
    type: "AACP_PROVIDER_EVIDENCE_MANIFEST",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state: "VERIFIED_READ_ONLY",
    sourceState: "VERIFIED_READ_ONLY",
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

    artifacts: {
      expected: 7,
      present: 7,
      missing: 0,
      uniqueSha256: 7,
      files,
    },

    states: {
      history: "VERIFIED_READ_ONLY",
      historyVerify: "VERIFIED_READ_ONLY",
      historyAnalysis: "VERIFIED_READ_ONLY",
      historyAnalysisVerify: "VERIFIED_READ_ONLY",
      historyChainVerify: "VERIFIED_READ_ONLY",
      historyIntegrityAudit: "VERIFIED_READ_ONLY",
      historyIntegrityAuditVerify: "VERIFIED_READ_ONLY",
    },

    consistency: {
      historyVerify: true,
      analysisVerify: true,
      integrityVerify: true,
      chainConsistent: true,
    },

    errors: [],

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

function run() {
  return spawnSync(
    process.execPath,
    [SOURCE],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_PROVIDER_OUTPUT_DIR: OUTPUT_DIR,
      },
      encoding: "utf8",
    }
  );
}

function readVerify() {
  return JSON.parse(
    fs.readFileSync(VERIFY, "utf8")
  );
}

function reset() {
  for (const file of fs.readdirSync(OUTPUT_DIR)) {
    fs.rmSync(path.join(OUTPUT_DIR, file), {
      recursive: true,
      force: true,
    });
  }
}

/* ============================================================
 * TEST 1 — SAFE MANIFEST
 * ========================================================== */

reset();

writeJson(
  "latest-provider-evidence-manifest.json",
  safeManifest()
);

let result = run();
let report = readVerify();

assert(
  result.status === 0,
  "safe manifest exits successfully"
);

assert(
  report.state === "VERIFIED_READ_ONLY",
  "safe manifest → VERIFIED_READ_ONLY"
);

assert(
  report.verification.valid === true,
  "safe manifest verification.valid=true"
);

assert(
  report.verification.errorCount === 0,
  "safe manifest has zero errors"
);

assert(
  report.mode === "READ_ONLY",
  "safe report mode is READ_ONLY"
);

assert(
  report.executionAuthorized === false,
  "executionAuthorized=false"
);

/* ============================================================
 * TEST 2 — MISSING MANIFEST
 * ========================================================== */

reset();

result = run();
report = readVerify();

assert(
  result.status === 0,
  "missing manifest exits cleanly"
);

assert(
  report.state === "INCOMPLETE",
  "missing manifest → INCOMPLETE"
);

/* ============================================================
 * TEST 3 — UNSAFE EXECUTION
 * ========================================================== */

reset();

const unsafe = safeManifest();
unsafe.executionAuthorized = true;

writeJson(
  "latest-provider-evidence-manifest.json",
  unsafe
);

result = run();
report = readVerify();

assert(
  result.status !== 0,
  "executionAuthorized=true exits blocked"
);

assert(
  report.state === "BLOCKED",
  "executionAuthorized=true → BLOCKED"
);

/* ============================================================
 * TEST 4 — UNSAFE SIGNING
 * ========================================================== */

reset();

const signing = safeManifest();
signing.safety.signingPerformed = true;

writeJson(
  "latest-provider-evidence-manifest.json",
  signing
);

result = run();
report = readVerify();

assert(
  report.state === "BLOCKED",
  "signingPerformed=true → BLOCKED"
);

/* ============================================================
 * TEST 5 — INVALID JSON
 * ========================================================== */

reset();

fs.writeFileSync(
  MANIFEST,
  "{invalid-json",
  "utf8"
);

result = run();
report = readVerify();

assert(
  result.status !== 0,
  "invalid JSON exits blocked"
);

assert(
  report.state === "BLOCKED",
  "invalid JSON → BLOCKED"
);

/* ============================================================
 * TEST 6 — INVALID SHA
 * ========================================================== */

reset();

const badSha = safeManifest();
badSha.artifacts.files[0].sha256 = "abc";

writeJson(
  "latest-provider-evidence-manifest.json",
  badSha
);

result = run();
report = readVerify();

assert(
  report.state === "BLOCKED",
  "invalid SHA-256 → BLOCKED"
);

/* ============================================================
 * TEST 7 — VERIFIED WITH MISSING ARTIFACT
 * ========================================================== */

reset();

const incompleteVerified = safeManifest();
incompleteVerified.artifacts.missing = 1;

writeJson(
  "latest-provider-evidence-manifest.json",
  incompleteVerified
);

result = run();
report = readVerify();

assert(
  report.state === "BLOCKED",
  "verified manifest with missing artifact → BLOCKED"
);

/* ============================================================
 * TEST 8 — INCOMPLETE IS VALID
 * ========================================================== */

reset();

const incomplete = safeManifest();

incomplete.state = "INCOMPLETE";
incomplete.sourceState = "INCOMPLETE";
incomplete.artifacts.present = 1;
incomplete.artifacts.missing = 6;
incomplete.artifacts.uniqueSha256 = 1;
incomplete.artifacts.files =
  incomplete.artifacts.files.map(
    (file, index) =>
      index === 0
        ? file
        : {
            ...file,
            exists: false,
            sizeBytes: null,
            sha256: null,
          }
  );

incomplete.states = {
  history: "INCOMPLETE",
};

incomplete.consistency = {
  historyVerify: false,
  analysisVerify: false,
  integrityVerify: false,
  chainConsistent: true,
};

writeJson(
  "latest-provider-evidence-manifest.json",
  incomplete
);

result = run();
report = readVerify();

assert(
  result.status === 0,
  "incomplete manifest exits successfully"
);

assert(
  report.state === "INCOMPLETE",
  "incomplete manifest → INCOMPLETE"
);

/* ============================================================
 * TEST 9 — POLICY VIOLATION
 * ========================================================== */

reset();

const badPolicy = safeManifest();
badPolicy.policy.wallet = "USED";

writeJson(
  "latest-provider-evidence-manifest.json",
  badPolicy
);

result = run();
report = readVerify();

assert(
  report.state === "BLOCKED",
  "policy violation → BLOCKED"
);

/* ============================================================
 * TEST 10 — SAFETY INVARIANTS
 * ========================================================== */

assert(
  report.mode === "READ_ONLY",
  "verifier mode is READ_ONLY"
);

assert(
  report.executionAuthorized === false,
  "verifier executionAuthorized=false"
);

assert(
  report.safety.postPerformed === false &&
  report.safety.walletUsed === false &&
  report.safety.signingPerformed === false &&
  report.safety.broadcastPerformed === false &&
  report.safety.submissionPerformed === false,
  "verifier safety invariants"
);

assert(
  report.sideEffects.postPerformed === false &&
  report.sideEffects.walletUsed === false &&
  report.sideEffects.signingPerformed === false &&
  report.sideEffects.broadcastPerformed === false &&
  report.sideEffects.submissionPerformed === false,
  "verifier side-effect invariants"
);

console.log(
  "ALL PROVIDER EVIDENCE MANIFEST VERIFIER TESTS PASSED"
);

fs.rmSync(OUTPUT_DIR, {
  recursive: true,
  force: true,
});
