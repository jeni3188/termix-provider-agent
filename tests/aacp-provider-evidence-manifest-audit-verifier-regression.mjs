import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const SOURCE = path.join(
  ROOT,
  "src",
  "aacp-provider-evidence-manifest-audit-verifier.mjs"
);

const TEMP = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-phase22-")
);

const OUT = path.join(
  TEMP,
  "provider-output",
  "aacp-observer"
);

const MANIFEST = path.join(
  OUT,
  "latest-provider-evidence-manifest.json"
);

const VERIFY = path.join(
  OUT,
  "latest-provider-evidence-manifest-verify.json"
);

const AUDIT = path.join(
  OUT,
  "latest-provider-evidence-manifest-audit.json"
);

const REPORT = path.join(
  OUT,
  "latest-provider-evidence-manifest-audit-verify.json"
);

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

const EXPECTED_FILES = [
  "latest-provider-watch-history.json",
  "latest-provider-watch-history-verify.json",
  "latest-provider-watch-history-analysis.json",
  "latest-provider-watch-history-analysis-verify.json",
  "latest-provider-watch-history-chain-verify.json",
  "latest-provider-watch-history-integrity-audit.json",
  "latest-provider-watch-history-integrity-audit-verify.json",
];

function sha256(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), {
    recursive: true,
  });

  fs.writeFileSync(
    file,
    JSON.stringify(value, null, 2) + "\n",
    "utf8"
  );
}

function baseManifest(state = "VERIFIED_READ_ONLY") {
  return {
    version: "1.0.0",
    type: "AACP_PROVIDER_EVIDENCE_MANIFEST",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state,
    sourceState: state,
    executionAuthorized: false,

    safety: { ...SAFETY },

    sideEffects: { ...SAFETY },

    artifacts: {
      expected: 7,
      present: state === "INCOMPLETE" ? 1 : 7,
      missing: state === "INCOMPLETE" ? 6 : 0,
      uniqueSha256: state === "INCOMPLETE" ? 1 : 7,
      files: EXPECTED_FILES.map(
        (file, index) => ({
          key: `artifact-${index + 1}`,
          file,
          exists: state !== "INCOMPLETE",
          sizeBytes:
            state !== "INCOMPLETE"
              ? 100 + index
              : index === 0
                ? 100
                : null,
          sha256:
            state !== "INCOMPLETE"
              ? "a".repeat(64)
              : index === 0
                ? "a".repeat(64)
                : null,
        })
      ),
    },

    states: {
      history: state,
    },

    consistency: {
      historyVerify: state === "VERIFIED_READ_ONLY",
      analysisVerify: state === "VERIFIED_READ_ONLY",
      integrityVerify: state === "VERIFIED_READ_ONLY",
      chainConsistent: state === "VERIFIED_READ_ONLY",
    },

    errors: state === "INCOMPLETE"
      ? EXPECTED_FILES
          .slice(1)
          .map(
            (file) =>
              `MISSING_FILE:${file}`
          )
      : [],

    policy: { ...POLICY },
  };
}

function baseVerifier(
  state,
  manifestSha
) {
  return {
    version: "1.0.0",
    type:
      "AACP_PROVIDER_EVIDENCE_MANIFEST_VERIFY",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state,
    sourceState: state,
    executionAuthorized: false,

    safety: { ...SAFETY },

    sideEffects: { ...SAFETY },

    source: {
      file: MANIFEST,
      exists: true,
      sha256: manifestSha,
    },

    verification: {
      valid: state === "VERIFIED_READ_ONLY",
      checks: [],
      errors: [],
      errorCount: 0,
    },

    policy: { ...POLICY },
  };
}

function baseAudit(
  state,
  manifestSha,
  verifierSha
) {
  return {
    version: "1.0.0",
    type:
      "AACP_PROVIDER_EVIDENCE_MANIFEST_AUDIT",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state,
    sourceState: state,
    executionAuthorized: false,

    safety: { ...SAFETY },

    sideEffects: { ...SAFETY },

    sources: {
      manifest: {
        file: MANIFEST,
        exists: true,
        sha256: manifestSha,
      },

      verifier: {
        file: VERIFY,
        exists: true,
        sha256: verifierSha,
      },
    },

    metrics: {
      manifestExists: true,
      verifierExists: true,
      manifestState: state,
      verifierState: state,
      manifestSha256: manifestSha,
      verifierSha256: verifierSha,
      expectedArtifacts: 7,
      presentArtifacts:
        state === "INCOMPLETE" ? 1 : 7,
      missingArtifacts:
        state === "INCOMPLETE" ? 6 : 0,
      verifierValid:
        state === "VERIFIED_READ_ONLY",
    },

    errors: [],

    policy: { ...POLICY },
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
        AACP_OUTPUT_DIR: OUT,
      },
      encoding: "utf8",
    }
  );
}

function readReport() {
  return JSON.parse(
    fs.readFileSync(REPORT, "utf8")
  );
}

function reset() {
  fs.rmSync(TEMP, {
    recursive: true,
    force: true,
  });

  fs.mkdirSync(OUT, {
    recursive: true,
  });
}

function assert(
  condition,
  message
) {
  if (!condition) {
    throw new Error(
      `FAIL: ${message}`
    );
  }

  console.log(`PASS: ${message}`);
}

function prepareSafeChain(
  state = "VERIFIED_READ_ONLY"
) {
  reset();

  const manifest =
    baseManifest(state);

  writeJson(
    MANIFEST,
    manifest
  );

  const manifestSha =
    sha256(MANIFEST);

  const verifier =
    baseVerifier(
      state,
      manifestSha
    );

  writeJson(
    VERIFY,
    verifier
  );

  const verifierSha =
    sha256(VERIFY);

  const audit =
    baseAudit(
      state,
      manifestSha,
      verifierSha
    );

  writeJson(
    AUDIT,
    audit
  );
}

try {
  prepareSafeChain();

  let result = run();
  let report = readReport();

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
    report.verification.valid === true,
    "safe audit verification.valid=true"
  );

  assert(
    report.verification.errors.length === 0,
    "safe audit has zero errors"
  );

  assert(
    report.mode === "READ_ONLY",
    "verifier mode is READ_ONLY"
  );

  assert(
    report.executionAuthorized === false,
    "executionAuthorized=false"
  );

  prepareSafeChain(
    "INCOMPLETE"
  );

  result = run();
  report = readReport();

  assert(
    result.status === 0,
    "incomplete chain exits successfully"
  );

  assert(
    report.state === "INCOMPLETE",
    "incomplete chain → INCOMPLETE"
  );

  assert(
    report.verification.valid === false,
    "incomplete chain verification.valid=false"
  );

  assert(
    report.verification.errors.length === 0,
    "incomplete chain has zero verifier errors"
  );

  prepareSafeChain();

  const manifest =
    JSON.parse(
      fs.readFileSync(
        MANIFEST,
        "utf8"
      )
    );

  manifest.executionAuthorized =
    true;

  writeJson(
    MANIFEST,
    manifest
  );

  result = run();
  report = readReport();

  assert(
    result.status !== 0,
    "executionAuthorized=true exits blocked"
  );

  assert(
    report.state === "BLOCKED",
    "executionAuthorized=true → BLOCKED"
  );

  prepareSafeChain();

  const audit =
    JSON.parse(
      fs.readFileSync(
        AUDIT,
        "utf8"
      )
    );

  audit.safety.signingPerformed =
    true;

  writeJson(
    AUDIT,
    audit
  );

  result = run();
  report = readReport();

  assert(
    result.status !== 0,
    "signingPerformed=true exits blocked"
  );

  assert(
    report.state === "BLOCKED",
    "signingPerformed=true → BLOCKED"
  );

  prepareSafeChain();

  fs.writeFileSync(
    AUDIT,
    "{invalid-json\n",
    "utf8"
  );

  result = run();
  report = readReport();

  assert(
    result.status !== 0,
    "invalid JSON exits blocked"
  );

  assert(
    report.state === "BLOCKED",
    "invalid JSON → BLOCKED"
  );

  prepareSafeChain();

  const verifier =
    JSON.parse(
      fs.readFileSync(
        VERIFY,
        "utf8"
      )
    );

  verifier.source.sha256 =
    "b".repeat(64);

  writeJson(
    VERIFY,
    verifier
  );

  result = run();
  report = readReport();

  assert(
    result.status !== 0,
    "manifest SHA mismatch exits blocked"
  );

  assert(
    report.state === "BLOCKED",
    "manifest SHA mismatch → BLOCKED"
  );

  prepareSafeChain();

  const audit2 =
    JSON.parse(
      fs.readFileSync(
        AUDIT,
        "utf8"
      )
    );

  audit2.state =
    "INCOMPLETE";
  audit2.sourceState =
    "INCOMPLETE";
  audit2.metrics.manifestState =
    "INCOMPLETE";
  audit2.metrics.verifierState =
    "INCOMPLETE";
  audit2.metrics.presentArtifacts =
    1;
  audit2.metrics.missingArtifacts =
    6;
  audit2.metrics.verifierValid =
    false;

  writeJson(
    AUDIT,
    audit2
  );

  result = run();
  report = readReport();

  assert(
    result.status !== 0,
    "cross-layer state mismatch exits blocked"
  );

  assert(
    report.state === "BLOCKED",
    "cross-layer state mismatch → BLOCKED"
  );

  prepareSafeChain();

  const manifest2 =
    JSON.parse(
      fs.readFileSync(
        MANIFEST,
        "utf8"
      )
    );

  manifest2.policy.wallet =
    "USED";

  writeJson(
    MANIFEST,
    manifest2
  );

  result = run();
  report = readReport();

  assert(
    result.status !== 0,
    "wallet policy violation exits blocked"
  );

  assert(
    report.state === "BLOCKED",
    "wallet policy violation → BLOCKED"
  );

  prepareSafeChain();

  const audit3 =
    JSON.parse(
      fs.readFileSync(
        AUDIT,
        "utf8"
      )
    );

  audit3.policy.signing =
    "PERFORMED";

  writeJson(
    AUDIT,
    audit3
  );

  result = run();
  report = readReport();

  assert(
    result.status !== 0,
    "audit policy violation exits blocked"
  );

  assert(
    report.state === "BLOCKED",
    "audit policy violation → BLOCKED"
  );

  prepareSafeChain();

  const verifier2 =
    JSON.parse(
      fs.readFileSync(
        VERIFY,
        "utf8"
      )
    );

  verifier2.verification.valid =
    false;

  writeJson(
    VERIFY,
    verifier2
  );

  result = run();
  report = readReport();

  assert(
    result.status !== 0,
    "verified verifier invalid exits blocked"
  );

  assert(
    report.state === "BLOCKED",
    "verified verifier invalid → BLOCKED"
  );

  prepareSafeChain();

  fs.unlinkSync(AUDIT);

  result = run();
  report = readReport();

  assert(
    result.status === 0,
    "missing audit exits successfully"
  );

  assert(
    report.state === "INCOMPLETE",
    "missing audit → INCOMPLETE"
  );

  assert(
    report.executionAuthorized === false,
    "missing audit executionAuthorized=false"
  );

  console.log(
    "PASS: verifier safety invariants"
  );

  assert(
    report.safety.postPerformed === false &&
    report.safety.walletUsed === false &&
    report.safety.signingPerformed === false &&
    report.safety.broadcastPerformed === false &&
    report.safety.submissionPerformed === false,
    "verifier safety flags all false"
  );

  assert(
    report.sideEffects.postPerformed === false &&
    report.sideEffects.walletUsed === false &&
    report.sideEffects.signingPerformed === false &&
    report.sideEffects.broadcastPerformed === false &&
    report.sideEffects.submissionPerformed === false,
    "verifier side-effect flags all false"
  );

  assert(
    report.policy.readOnly === true &&
    report.policy.failClosed === true &&
    report.policy.post === "NOT_PERFORMED" &&
    report.policy.wallet === "NOT_USED" &&
    report.policy.signing === "NOT_PERFORMED" &&
    report.policy.broadcast === "NOT_PERFORMED" &&
    report.policy.submission === "NOT_PERFORMED",
    "verifier policy invariants"
  );

  console.log(
    "ALL PROVIDER EVIDENCE MANIFEST AUDIT VERIFIER TESTS PASSED"
  );
} finally {
  fs.rmSync(
    TEMP,
    {
      recursive: true,
      force: true,
    }
  );
}
