import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();

const SOURCE = path.join(
  ROOT,
  "src/aacp-provider-evidence-manifest-auditor.mjs"
);

const OUTPUT_DIR = fs.mkdtempSync(
  path.join(
    os.tmpdir(),
    "aacp-provider-manifest-audit-"
  )
);

const MANIFEST = path.join(
  OUTPUT_DIR,
  "latest-provider-evidence-manifest.json"
);

const VERIFY = path.join(
  OUTPUT_DIR,
  "latest-provider-evidence-manifest-verify.json"
);

const AUDIT = path.join(
  OUTPUT_DIR,
  "latest-provider-evidence-manifest-audit.json"
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
    JSON.stringify(value, null, 2) +
      "\n",
    "utf8"
  );
}

function writeText(file, text) {
  fs.writeFileSync(
    path.join(OUTPUT_DIR, file),
    text,
    "utf8"
  );
}

function safeManifest() {
  const files = FILES.map(
    (file, index) => {
      const content =
        `fixture-${index}-${file}`;

      writeText(file, content);

      return {
        key: `fixture-${index}`,
        file,
        exists: true,
        sizeBytes:
          Buffer.byteLength(content),
        sha256: sha256(content),
      };
    }
  );

  return {
    version: "1.0.0",
    type:
      "AACP_PROVIDER_EVIDENCE_MANIFEST",
    generatedAt:
      new Date().toISOString(),
    mode: "READ_ONLY",
    state: "VERIFIED_READ_ONLY",
    sourceState:
      "VERIFIED_READ_ONLY",
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
      history:
        "VERIFIED_READ_ONLY",
      historyVerify:
        "VERIFIED_READ_ONLY",
      historyAnalysis:
        "VERIFIED_READ_ONLY",
      historyAnalysisVerify:
        "VERIFIED_READ_ONLY",
      historyChainVerify:
        "VERIFIED_READ_ONLY",
      historyIntegrityAudit:
        "VERIFIED_READ_ONLY",
      historyIntegrityAuditVerify:
        "VERIFIED_READ_ONLY",
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

function safeVerifier() {
  const sourceSha =
    crypto
      .createHash("sha256")
      .update(
        fs.readFileSync(
          MANIFEST
        )
      )
      .digest("hex");

  return {
    version: "1.0.0",
    type:
      "AACP_PROVIDER_EVIDENCE_MANIFEST_VERIFY",
    generatedAt:
      new Date().toISOString(),
    mode: "READ_ONLY",
    state:
      "VERIFIED_READ_ONLY",
    sourceState:
      "VERIFIED_READ_ONLY",
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

    source: {
      file: MANIFEST,
      exists: true,
      sha256: sourceSha,
    },

    verification: {
      valid: true,
      errors: [],
      errorCount: 0,
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

function reset() {
  fs.rmSync(
    OUTPUT_DIR,
    {
      recursive: true,
      force: true,
    }
  );

  fs.mkdirSync(
    OUTPUT_DIR,
    {
      recursive: true,
    }
  );
}

function run() {
  return spawnSync(
    process.execPath,
    [SOURCE],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OUTPUT_DIR:
          OUTPUT_DIR,
      },
      encoding: "utf8",
    }
  );
}

function readAudit() {
  return JSON.parse(
    fs.readFileSync(
      AUDIT,
      "utf8"
    )
  );
}

/* ============================================================
 * TEST 1 — SAFE CHAIN
 * ========================================================== */

reset();

const safe = safeManifest();

writeJson(
  "latest-provider-evidence-manifest.json",
  safe
);

const verifier =
  safeVerifier();

writeJson(
  "latest-provider-evidence-manifest-verify.json",
  verifier
);

let result = run();
let report = readAudit();

assert(
  result.status === 0,
  "safe chain exits successfully"
);

assert(
  report.state ===
    "VERIFIED_READ_ONLY",
  "safe chain → VERIFIED_READ_ONLY"
);

assert(
  report.errors.length === 0,
  "safe chain has zero errors"
);

assert(
  report.metrics.expectedArtifacts === 7,
  "seven artifacts expected"
);

assert(
  report.metrics.presentArtifacts === 7,
  "seven artifacts present"
);

assert(
  report.metrics.missingArtifacts === 0,
  "no artifacts missing"
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
report = readAudit();

assert(
  result.status === 0,
  "missing manifest exits cleanly"
);

assert(
  report.state === "INCOMPLETE",
  "missing manifest → INCOMPLETE"
);

/* ============================================================
 * TEST 3 — EXECUTION AUTHORIZED
 * ========================================================== */

reset();

const unsafeExecution =
  safeManifest();

unsafeExecution.executionAuthorized =
  true;

writeJson(
  "latest-provider-evidence-manifest.json",
  unsafeExecution
);

writeJson(
  "latest-provider-evidence-manifest-verify.json",
  safeVerifier()
);

result = run();
report = readAudit();

assert(
  result.status !== 0,
  "executionAuthorized=true exits blocked"
);

assert(
  report.state === "BLOCKED",
  "executionAuthorized=true → BLOCKED"
);

/* ============================================================
 * TEST 4 — SIGNING
 * ========================================================== */

reset();

const unsafeSigning =
  safeManifest();

unsafeSigning.safety.signingPerformed =
  true;

writeJson(
  "latest-provider-evidence-manifest.json",
  unsafeSigning
);

writeJson(
  "latest-provider-evidence-manifest-verify.json",
  safeVerifier()
);

result = run();
report = readAudit();

assert(
  report.state === "BLOCKED",
  "signingPerformed=true → BLOCKED"
);

/* ============================================================
 * TEST 5 — SHA MISMATCH
 * ========================================================== */

reset();

const shaMismatch =
  safeManifest();

writeJson(
  "latest-provider-evidence-manifest.json",
  shaMismatch
);

const badVerifier =
  safeVerifier();

badVerifier.source.sha256 =
  "0".repeat(64);

writeJson(
  "latest-provider-evidence-manifest-verify.json",
  badVerifier
);

result = run();
report = readAudit();

assert(
  report.state === "BLOCKED",
  "SHA-256 mismatch → BLOCKED"
);

/* ============================================================
 * TEST 6 — STATE MISMATCH
 * ========================================================== */

reset();

const mismatchManifest =
  safeManifest();

writeJson(
  "latest-provider-evidence-manifest.json",
  mismatchManifest
);

const mismatchVerifier =
  safeVerifier();

mismatchVerifier.state =
  "INCOMPLETE";
mismatchVerifier.sourceState =
  "INCOMPLETE";

writeJson(
  "latest-provider-evidence-manifest-verify.json",
  mismatchVerifier
);

result = run();
report = readAudit();

assert(
  report.state === "BLOCKED",
  "cross-layer state mismatch → BLOCKED"
);

/* ============================================================
 * TEST 7 — INVALID JSON
 * ========================================================== */

reset();

writeText(
  "latest-provider-evidence-manifest.json",
  "{ invalid"
);

result = run();
report = readAudit();

assert(
  report.state === "BLOCKED",
  "invalid JSON → BLOCKED"
);

/* ============================================================
 * TEST 8 — WALLET
 * ========================================================== */

reset();

const unsafeWallet =
  safeManifest();

unsafeWallet.safety.walletUsed =
  true;

writeJson(
  "latest-provider-evidence-manifest.json",
  unsafeWallet
);

writeJson(
  "latest-provider-evidence-manifest-verify.json",
  safeVerifier()
);

result = run();
report = readAudit();

assert(
  report.state === "BLOCKED",
  "walletUsed=true → BLOCKED"
);

/* ============================================================
 * TEST 9 — SAFETY INVARIANTS
 * ========================================================== */

assert(
  report.mode === "READ_ONLY",
  "auditor mode is READ_ONLY"
);

assert(
  report.executionAuthorized === false,
  "auditor executionAuthorized=false"
);

assert(
  Object.values(report.safety)
    .every((value) => value === false),
  "auditor safety invariants"
);

assert(
  Object.values(report.sideEffects)
    .every((value) => value === false),
  "auditor side-effect invariants"
);

assert(
  report.policy.readOnly === true &&
  report.policy.failClosed === true &&
  report.policy.post ===
    "NOT_PERFORMED" &&
  report.policy.wallet ===
    "NOT_USED" &&
  report.policy.signing ===
    "NOT_PERFORMED" &&
  report.policy.broadcast ===
    "NOT_PERFORMED" &&
  report.policy.submission ===
    "NOT_PERFORMED",
  "auditor policy invariants"
);

console.log(
  "ALL PROVIDER EVIDENCE MANIFEST AUDITOR TESTS PASSED"
);
