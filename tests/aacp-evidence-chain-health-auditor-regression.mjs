import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import crypto from "node:crypto";

const ROOT = process.cwd();
const SRC = path.join(ROOT, "src", "aacp-evidence-chain-health-auditor.mjs");

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "aacp-health-audit-"));
}

function run(dir) {
  return spawnSync(
    process.execPath,
    [SRC],
    {
      cwd: dir,
      encoding: "utf8",
      env: {
        ...process.env,
        AACP_OUTPUT_DIR: dir,
      },
    }
  );
}

function writeJson(dir, name, value) {
  fs.writeFileSync(
    path.join(dir, name),
    JSON.stringify(value, null, 2)
  );
}

function readJson(dir, name) {
  return JSON.parse(
    fs.readFileSync(path.join(dir, name), "utf8")
  );
}

function sha256File(dir, name) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(path.join(dir, name)))
    .digest("hex");
}

const POLICY = {
  readOnly: true,
  failClosed: true,
  post: "NOT_PERFORMED",
  wallet: "NOT_USED",
  signing: "NOT_PERFORMED",
  broadcast: "NOT_PERFORMED",
  submission: "NOT_PERFORMED",
};

const SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false,
};

const ARTIFACT_NAMES = [
  "latest-provider-watch-history.json",
  "latest-provider-watch-history-verify.json",
  "latest-provider-watch-history-analysis.json",
  "latest-provider-watch-history-analysis-verify.json",
  "latest-provider-watch-history-chain-verify.json",
  "latest-provider-watch-history-integrity-audit.json",
  "latest-provider-watch-history-integrity-audit-verify.json",
  "latest-provider-evidence-manifest.json",
  "latest-provider-evidence-manifest-verify.json",
  "latest-provider-evidence-manifest-audit.json",
  "latest-provider-evidence-manifest-audit-verify.json",
];

function health({
  state = "VERIFIED_READ_ONLY",
  sourceState = state,
  present = 11,
  missing = 0,
  blocked = 0,
  verified = 11,
  errors = [],
} = {}) {
  return {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH",
    generatedAt: "2026-01-01T00:00:00.000Z",
    mode: "READ_ONLY",
    state,
    sourceState,
    executionAuthorized: false,
    safety: SAFETY,
    sideEffects: SAFETY,
    health: {
      artifactsExpected: 11,
      artifactsPresent: present,
      artifactsMissing: missing,
      artifactsBlocked: blocked,
      artifactsVerified: verified,
      missing: missing
        ? ARTIFACT_NAMES.slice(0, missing)
        : [],
      blocked: [],
      errors,
      errorCount: errors.length,
      allArtifactsPresent: missing === 0,
      allArtifactsValid: blocked === 0,
    },
    artifacts: ARTIFACT_NAMES.map((file, i) => ({
      phase: `PHASE_${String(i + 12).padStart(2, "0")}`,
      key: `artifact${i}`,
      file,
      exists: true,
      valid: true,
      state: "VERIFIED_READ_ONLY",
      sourceState: "VERIFIED_READ_ONLY",
      sha256: "a".repeat(64),
      errors: [],
    })),
    policy: POLICY,
  };
}

function verifyReport({
  state = "VERIFIED_READ_ONLY",
  sourceState = state,
  valid = state === "VERIFIED_READ_ONLY",
} = {}) {
  return {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH_VERIFY",
    generatedAt: "2026-01-01T00:00:01.000Z",
    mode: "READ_ONLY",
    state,
    sourceState,
    executionAuthorized: false,
    safety: SAFETY,
    sideEffects: SAFETY,
    source: {
      file: "latest-aacp-evidence-chain-health.json",
      exists: true,
      sha256: "b".repeat(64),
    },
    verification: {
      valid,
      sourceState,
      sourceErrors: [],
      artifactErrors: [],
      errors: [],
      errorCount: 0,
      artifactsExpected: 11,
      artifactsPresent: state === "INCOMPLETE" ? 5 : 11,
      artifactsMissing: state === "INCOMPLETE" ? 6 : 0,
      artifactsBlocked: 0,
      artifactsVerified: state === "INCOMPLETE" ? 0 : 11,
    },
    policy: POLICY,
  };
}

function setupComplete(dir) {
  writeJson(dir, "latest-aacp-evidence-chain-health.json", health());

  const verify = verifyReport();
  verify.source.sha256 = sha256File(
    dir,
    "latest-aacp-evidence-chain-health.json"
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verify
  );
}

function setupIncomplete(dir) {
  writeJson(
    dir,
    "latest-aacp-evidence-chain-health.json",
    health({
      state: "INCOMPLETE",
      sourceState: "INCOMPLETE",
      present: 5,
      missing: 6,
      verified: 0,
    })
  );

  const verify = verifyReport({
    state: "INCOMPLETE",
    sourceState: "INCOMPLETE",
    valid: false,
  });

  verify.source.sha256 = sha256File(
    dir,
    "latest-aacp-evidence-chain-health.json"
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verify
  );
}

function expectState(label, result, expected) {
  if (!result.stdout.includes(`STATE: ${expected}`)) {
    console.error(`FAIL: ${label}`);
    console.error(result.stdout);
    console.error(result.stderr);
    process.exit(1);
  }

  console.log(`PASS: ${label}`);
}

// 1. Complete safe chain
{
  const dir = tmp();
  setupComplete(dir);

  const result = run(dir);

  expectState(
    "safe complete chain → VERIFIED_READ_ONLY",
    result,
    "VERIFIED_READ_ONLY"
  );
}

// 2. Incomplete safe chain
{
  const dir = tmp();
  setupIncomplete(dir);

  const result = run(dir);

  expectState(
    "safe incomplete chain → INCOMPLETE",
    result,
    "INCOMPLETE"
  );
}

// 3. Missing Phase 23
{
  const dir = tmp();

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verifyReport()
  );

  const result = run(dir);

  expectState(
    "missing health report → INCOMPLETE",
    result,
    "INCOMPLETE"
  );
}

// 4. Missing Phase 24
{
  const dir = tmp();

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health.json",
    health()
  );

  const result = run(dir);

  expectState(
    "missing health verifier → INCOMPLETE",
    result,
    "INCOMPLETE"
  );
}

// 5. Invalid JSON
{
  const dir = tmp();

  fs.writeFileSync(
    path.join(dir, "latest-aacp-evidence-chain-health.json"),
    "{invalid"
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verifyReport()
  );

  const result = run(dir);

  expectState(
    "invalid health JSON → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 6. executionAuthorized violation
{
  const dir = tmp();

  const h = health();
  h.executionAuthorized = true;

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health.json",
    h
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verifyReport()
  );

  const result = run(dir);

  expectState(
    "executionAuthorized=true → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 7. wallet violation
{
  const dir = tmp();

  const h = health();
  h.safety.walletUsed = true;

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health.json",
    h
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verifyReport()
  );

  const result = run(dir);

  expectState(
    "walletUsed=true → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 8. signing violation
{
  const dir = tmp();

  const h = health();
  h.safety.signingPerformed = true;

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health.json",
    h
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verifyReport()
  );

  const result = run(dir);

  expectState(
    "signingPerformed=true → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 9. broadcast violation
{
  const dir = tmp();

  const h = health();
  h.safety.broadcastPerformed = true;

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health.json",
    h
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verifyReport()
  );

  const result = run(dir);

  expectState(
    "broadcastPerformed=true → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 10. submission violation
{
  const dir = tmp();

  const h = health();
  h.safety.submissionPerformed = true;

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health.json",
    h
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verifyReport()
  );

  const result = run(dir);

  expectState(
    "submissionPerformed=true → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 11. policy violation
{
  const dir = tmp();

  const h = health();
  h.policy.readOnly = false;

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health.json",
    h
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verifyReport()
  );

  const result = run(dir);

  expectState(
    "policy readOnly=false → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 12. cross-layer state mismatch
{
  const dir = tmp();

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health.json",
    health({
      state: "VERIFIED_READ_ONLY",
      sourceState: "VERIFIED_READ_ONLY",
    })
  );

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verifyReport({
      state: "INCOMPLETE",
      sourceState: "INCOMPLETE",
      valid: false,
    })
  );

  const result = run(dir);

  expectState(
    "health/verifier state mismatch → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 13. verifier valid=true while health incomplete
{
  const dir = tmp();

  setupIncomplete(dir);

  const verify = verifyReport({
    state: "INCOMPLETE",
    sourceState: "INCOMPLETE",
    valid: true,
  });

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verify
  );

  const result = run(dir);

  expectState(
    "INCOMPLETE + verifier valid=true → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 14. verifier valid=false while health verified
{
  const dir = tmp();

  setupComplete(dir);

  const verify = verifyReport({
    state: "VERIFIED_READ_ONLY",
    sourceState: "VERIFIED_READ_ONLY",
    valid: false,
  });

  writeJson(
    dir,
    "latest-aacp-evidence-chain-health-verify.json",
    verify
  );

  const result = run(dir);

  expectState(
    "VERIFIED + verifier valid=false → BLOCKED",
    result,
    "BLOCKED"
  );
}

// 15. policy invariant preservation
{
  const dir = tmp();
  setupIncomplete(dir);

  const result = run(dir);

  const output = readJson(
    dir,
    "latest-aacp-evidence-chain-health-audit.json"
  );

  if (
    output.mode !== "READ_ONLY" ||
    output.executionAuthorized !== false ||
    output.safety.postPerformed !== false ||
    output.safety.walletUsed !== false ||
    output.safety.signingPerformed !== false ||
    output.safety.broadcastPerformed !== false ||
    output.safety.submissionPerformed !== false ||
    output.policy.readOnly !== true ||
    output.policy.failClosed !== true ||
    output.policy.post !== "NOT_PERFORMED" ||
    output.policy.wallet !== "NOT_USED" ||
    output.policy.signing !== "NOT_PERFORMED" ||
    output.policy.broadcast !== "NOT_PERFORMED" ||
    output.policy.submission !== "NOT_PERFORMED"
  ) {
    console.error("FAIL: audit policy/safety invariants");
    process.exit(1);
  }

  console.log("PASS: audit policy/safety invariants");
}

console.log("ALL PROVIDER EVIDENCE CHAIN HEALTH AUDITOR TESTS PASSED");
