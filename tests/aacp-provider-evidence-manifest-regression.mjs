import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { spawnSync } from "node:child_process";

const ROOT = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-provider-evidence-")
);

const OUTPUT_DIR = path.join(
  ROOT,
  "provider-output",
  "aacp-observer"
);

const SOURCE = path.resolve(
  "src/aacp-provider-evidence-manifest.mjs"
);

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

function writeJson(file, data) {
  fs.writeFileSync(
    path.join(OUTPUT_DIR, file),
    JSON.stringify(data, null, 2) + "\n"
  );
}

function safeReport(state = "VERIFIED_READ_ONLY") {
  return {
    version: "1.0.0",
    mode: "READ_ONLY",
    state,
    sourceState: state,
    generatedAt: new Date().toISOString(),
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
  };
}

function run() {
  return spawnSync(
    process.execPath,
    [SOURCE],
    {
      cwd: process.cwd(),
      env: {
        ...process.env,
        AACP_PROVIDER_OUTPUT_DIR: OUTPUT_DIR,
      },
      encoding: "utf8",
    }
  );
}

function readManifest() {
  return JSON.parse(
    fs.readFileSync(
      path.join(
        OUTPUT_DIR,
        "latest-provider-evidence-manifest.json"
      ),
      "utf8"
    )
  );
}

function reset() {
  fs.rmSync(OUTPUT_DIR, {
    recursive: true,
    force: true,
  });

  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

const FILES = [
  "latest-provider-watch-history.json",
  "latest-provider-watch-history-verify.json",
  "latest-provider-watch-history-analysis.json",
  "latest-provider-watch-history-analysis-verify.json",
  "latest-provider-watch-history-chain-verify.json",
  "latest-provider-watch-history-integrity-audit.json",
  "latest-provider-watch-history-integrity-audit-verify.json",
];

function createSafeChain() {
  // Phase 12 raw history has a different schema from provider reports.
  writeJson(
    "latest-provider-watch-history.json",
    {
      version: "1.0.0",
      mode: "READ_ONLY",
      events: [
        {
          id: "phase19-fixture-event",
          generatedAt: "2026-01-01T00:00:00.000Z",
          state: "VERIFIED_READ_ONLY",
          changed: true,
          changedFields: ["INITIAL_SNAPSHOT"],
          watch: {
            exists: true,
            valid: true,
            sha256:
              "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
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
            submissionPerformed: false
          },
          safety: {
            executionAuthorized: false,
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
          executionAuthorized: false
        }
      ]
    }
  );

  // Phase 13–18 artifacts are provider reports.
  for (const [index, file] of FILES.slice(1).entries()) {
    const report = safeReport();

    // Keep each fixture byte-distinct so the manifest can
    // legitimately verify unique SHA-256 fingerprints.
    report.fixtureArtifact = file;
    report.fixtureIndex = index;

    // Phase 18 verification report exposes verification.valid.
    if (
      file ===
      "latest-provider-watch-history-integrity-audit-verify.json"
    ) {
      report.verification = {
        valid: true,
        checks: [],
        errors: []
      };
    }

    writeJson(file, report);
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(`FAIL: ${message}`);
  }

  console.log(`PASS: ${message}`);
}

/* ============================================================
 * TEST 1 — SAFE CHAIN
 * ========================================================== */

reset();
createSafeChain();

let result = run();
let manifest = readManifest();


assert(
  result.status === 0,
  "safe evidence chain exits successfully"
);

assert(
  manifest.state === "VERIFIED_READ_ONLY",
  "safe evidence chain → VERIFIED_READ_ONLY"
);

assert(
  manifest.artifacts.expected === 7,
  "seven artifacts expected"
);

assert(
  manifest.artifacts.present === 7,
  "seven artifacts present"
);

assert(
  manifest.artifacts.missing === 0,
  "no artifacts missing"
);

assert(
  manifest.errors.length === 0,
  "safe chain has zero errors"
);

/* ============================================================
 * TEST 2 — MISSING ARTIFACT
 * ========================================================== */

reset();
createSafeChain();

fs.unlinkSync(
  path.join(
    OUTPUT_DIR,
    "latest-provider-watch-history.json"
  )
);

result = run();
manifest = readManifest();

assert(
  manifest.state === "INCOMPLETE",
  "missing artifact → INCOMPLETE"
);

/* ============================================================
 * TEST 3 — UNSAFE EXECUTION
 * ========================================================== */

reset();
createSafeChain();

const unsafe = safeReport();
unsafe.executionAuthorized = true;

writeJson(
  "latest-provider-watch-history.json",
  unsafe
);

result = run();
manifest = readManifest();

assert(
  manifest.state === "BLOCKED",
  "executionAuthorized=true → BLOCKED"
);

/* ============================================================
 * TEST 4 — UNSAFE SIGNING
 * ========================================================== */

reset();
createSafeChain();

const unsafeSigning = safeReport();
unsafeSigning.safety.signingPerformed = true;

writeJson(
  "latest-provider-watch-history-analysis.json",
  unsafeSigning
);

result = run();
manifest = readManifest();

assert(
  manifest.state === "BLOCKED",
  "signingPerformed=true → BLOCKED"
);

/* ============================================================
 * TEST 5 — STATE MISMATCH
 * ========================================================== */

reset();
createSafeChain();

writeJson(
  "latest-provider-watch-history-verify.json",
  safeReport("BLOCKED")
);

result = run();
manifest = readManifest();

assert(
  manifest.state === "BLOCKED",
  "cross-layer state mismatch → BLOCKED"
);

/* ============================================================
 * TEST 6 — INVALID JSON
 * ========================================================== */

reset();
createSafeChain();

fs.writeFileSync(
  path.join(
    OUTPUT_DIR,
    "latest-provider-watch-history-chain-verify.json"
  ),
  "{invalid-json"
);

result = run();
manifest = readManifest();

assert(
  manifest.state === "BLOCKED",
  "invalid JSON → BLOCKED"
);

/* ============================================================
 * TEST 7 — WALLET SAFETY
 * ========================================================== */

reset();
createSafeChain();

const unsafeWallet = safeReport();
unsafeWallet.safety.walletUsed = true;

writeJson(
  "latest-provider-watch-history-integrity-audit.json",
  unsafeWallet
);

result = run();
manifest = readManifest();

assert(
  manifest.state === "BLOCKED",
  "walletUsed=true → BLOCKED"
);

/* ============================================================
 * TEST 8 — POLICY INVARIANTS
 * ========================================================== */

reset();
createSafeChain();

result = run();
manifest = readManifest();

assert(
  manifest.mode === "READ_ONLY",
  "manifest mode is READ_ONLY"
);

assert(
  manifest.executionAuthorized === false,
  "executionAuthorized=false"
);

assert(
  manifest.safety.postPerformed === false &&
  manifest.safety.walletUsed === false &&
  manifest.safety.signingPerformed === false &&
  manifest.safety.broadcastPerformed === false &&
  manifest.safety.submissionPerformed === false,
  "manifest safety invariants"
);

assert(
  manifest.sideEffects.postPerformed === false &&
  manifest.sideEffects.walletUsed === false &&
  manifest.sideEffects.signingPerformed === false &&
  manifest.sideEffects.broadcastPerformed === false &&
  manifest.sideEffects.submissionPerformed === false,
  "manifest side-effect invariants"
);

assert(
  manifest.policy.readOnly === true &&
  manifest.policy.failClosed === true &&
  manifest.policy.post === "NOT_PERFORMED" &&
  manifest.policy.wallet === "NOT_USED" &&
  manifest.policy.signing === "NOT_PERFORMED" &&
  manifest.policy.broadcast === "NOT_PERFORMED" &&
  manifest.policy.submission === "NOT_PERFORMED",
  "manifest policy invariants"
);

console.log(
  "ALL PROVIDER EVIDENCE MANIFEST TESTS PASSED"
);

fs.rmSync(ROOT, {
  recursive: true,
  force: true,
});
