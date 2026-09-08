import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();

const SOURCE = path.join(
  ROOT,
  "src",
  "aacp-evidence-chain-health-monitor.mjs"
);

const TEMP = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-phase23-")
);

const OUT = path.join(
  TEMP,
  "provider-output",
  "aacp-observer"
);

const REPORT = path.join(
  OUT,
  "latest-aacp-evidence-chain-health.json"
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
  "latest-provider-evidence-manifest.json",
  "latest-provider-evidence-manifest-verify.json",
  "latest-provider-evidence-manifest-audit.json",
  "latest-provider-evidence-manifest-audit-verify.json",
];

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

function sha256(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function makeEvent(
  state = "VERIFIED_READ_ONLY",
  overrides = {}
) {
  return {
    id: crypto.randomUUID(),
    generatedAt: new Date().toISOString(),
    state,
    changed: false,
    changedFields: [],
    watch: {
      exists: true,
      valid: true,
      sha256: "a".repeat(64),
    },
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

function makeHistory(
  events = [makeEvent()]
) {
  return {
    version: "1.0.0",
    events,
    mode: "READ_ONLY",
  };
}

function makeReport(
  type,
  state = "VERIFIED_READ_ONLY",
  overrides = {}
) {
  return {
    version: "1.0.0",
    type,
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state,
    sourceState: state,
    executionAuthorized: false,
    safety: { ...SAFETY },
    sideEffects: { ...SAFETY },
    policy: { ...POLICY },
    ...overrides,
  };
}

function makeManifest(
  state = "VERIFIED_READ_ONLY",
  overrides = {}
) {
  return {
    ...makeReport(
      "AACP_PROVIDER_EVIDENCE_MANIFEST",
      state
    ),
    artifacts: {
      expected: 7,
      present: state === "INCOMPLETE" ? 1 : 7,
      missing: state === "INCOMPLETE" ? 6 : 0,
      uniqueSha256: state === "INCOMPLETE" ? 1 : 7,
      files: [],
    },
    consistency: {
      expectedFiles: true,
      presentCount: true,
      missingCount: true,
      totalCount: true,
    },
    ...overrides,
  };
}

function makeVerifier(
  state = "VERIFIED_READ_ONLY",
  overrides = {}
) {
  return {
    ...makeReport(
      "AACP_PROVIDER_EVIDENCE_MANIFEST_VERIFY",
      state
    ),
    source: {
      file: path.join(OUT, "latest-provider-evidence-manifest.json"),
      exists: true,
      sha256: "a".repeat(64),
    },
    verification: {
      valid: state === "VERIFIED_READ_ONLY",
      errors: [],
      errorCount: 0,
    },
    ...overrides,
  };
}

function makeAudit(
  state = "VERIFIED_READ_ONLY",
  overrides = {}
) {
  return {
    ...makeReport(
      "AACP_PROVIDER_EVIDENCE_MANIFEST_AUDIT",
      state
    ),
    sources: {
      manifest: {
        file: path.join(OUT, "latest-provider-evidence-manifest.json"),
        exists: true,
        sha256: "a".repeat(64),
      },
      verifier: {
        file: path.join(
          OUT,
          "latest-provider-evidence-manifest-verify.json"
        ),
        exists: true,
        sha256: "b".repeat(64),
      },
    },
    metrics: {
      expected: 7,
      present: state === "INCOMPLETE" ? 1 : 7,
      missing: state === "INCOMPLETE" ? 6 : 0,
      verifierValid:
        state === "VERIFIED_READ_ONLY",
    },
    errors: [],
    ...overrides,
  };
}

function prepareSafeChain() {
  fs.rmSync(OUT, {
    recursive: true,
    force: true,
  });

  fs.mkdirSync(OUT, {
    recursive: true,
  });

  writeJson(
    path.join(
      OUT,
      "latest-provider-watch-history.json"
    ),
    makeHistory()
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-watch-history-verify.json"
    ),
    makeReport(
      "AACP_PROVIDER_WATCH_HISTORY_VERIFY"
    )
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-watch-history-analysis.json"
    ),
    makeReport(
      "AACP_PROVIDER_WATCH_HISTORY_ANALYSIS"
    )
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-watch-history-analysis-verify.json"
    ),
    makeReport(
      "AACP_PROVIDER_WATCH_HISTORY_ANALYSIS_VERIFY"
    )
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-watch-history-chain-verify.json"
    ),
    makeReport(
      "AACP_PROVIDER_WATCH_HISTORY_CHAIN_VERIFY"
    )
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-watch-history-integrity-audit.json"
    ),
    makeReport(
      "AACP_PROVIDER_WATCH_HISTORY_INTEGRITY_AUDIT"
    )
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-watch-history-integrity-audit-verify.json"
    ),
    makeReport(
      "AACP_PROVIDER_WATCH_HISTORY_INTEGRITY_AUDIT_VERIFY"
    )
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-evidence-manifest.json"
    ),
    makeManifest()
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-evidence-manifest-verify.json"
    ),
    makeVerifier()
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-evidence-manifest-audit.json"
    ),
    makeAudit()
  );

  writeJson(
    path.join(
      OUT,
      "latest-provider-evidence-manifest-audit-verify.json"
    ),
    makeReport(
      "AACP_PROVIDER_EVIDENCE_MANIFEST_AUDIT_VERIFY"
    )
  );
}

function run(overrides = {}) {
  const result = spawnSync(
    process.execPath,
    [SOURCE],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OUTPUT_DIR: OUT,
        ...overrides,
      },
      encoding: "utf8",
    }
  );

  let report = null;

  if (fs.existsSync(REPORT)) {
    report = JSON.parse(
      fs.readFileSync(REPORT, "utf8")
    );
  }

  return {
    result,
    report,
  };
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(`FAIL: ${message}`);
  }

  console.log(`PASS: ${message}`);
}

/*
 * 1. Safe complete chain.
 */
prepareSafeChain();

let r = run();

assert(
  r.result.status === 0,
  "safe chain exits successfully"
);

assert(
  r.report.state === "VERIFIED_READ_ONLY",
  "safe chain → VERIFIED_READ_ONLY"
);

assert(
  r.report.health.artifactsExpected === 11,
  "eleven artifacts expected"
);

assert(
  r.report.health.artifactsPresent === 11,
  "eleven artifacts present"
);

assert(
  r.report.health.artifactsMissing === 0,
  "safe chain has zero missing artifacts"
);

assert(
  r.report.health.artifactsBlocked === 0,
  "safe chain has zero blocked artifacts"
);

assert(
  r.report.health.errorCount === 0,
  "safe chain has zero errors"
);

/*
 * 2. Realistic incomplete chain.
 */
prepareSafeChain();

for (const file of EXPECTED_FILES.slice(0, 7)) {
  const full = path.join(OUT, file);

  if (fs.existsSync(full)) {
    fs.rmSync(full);
  }
}

r = run();

assert(
  r.result.status === 0,
  "incomplete chain exits successfully"
);

assert(
  r.report.state === "INCOMPLETE",
  "incomplete chain → INCOMPLETE"
);

assert(
  r.report.health.artifactsBlocked === 0,
  "incomplete chain has zero blocked artifacts"
);

/*
 * 3. Unsafe Phase 12 event.
 */
prepareSafeChain();

const historyFile = path.join(
  OUT,
  "latest-provider-watch-history.json"
);

const unsafeHistory = makeHistory([
  makeEvent(
    "INCOMPLETE",
    {
      executionAuthorized: true,
    }
  ),
]);

writeJson(
  historyFile,
  unsafeHistory
);

r = run();

assert(
  r.result.status === 1,
  "unsafe history exits blocked"
);

assert(
  r.report.state === "BLOCKED",
  "unsafe history → BLOCKED"
);

/*
 * 4. Invalid JSON.
 */
prepareSafeChain();

fs.writeFileSync(
  path.join(
    OUT,
    "latest-provider-evidence-manifest.json"
  ),
  "{invalid-json",
  "utf8"
);

r = run();

assert(
  r.result.status === 1,
  "invalid JSON exits blocked"
);

assert(
  r.report.state === "BLOCKED",
  "invalid JSON → BLOCKED"
);

/*
 * 5. Unsafe manifest.
 */
prepareSafeChain();

const manifestFile = path.join(
  OUT,
  "latest-provider-evidence-manifest.json"
);

const unsafeManifest = makeManifest(
  "VERIFIED_READ_ONLY",
  {
    executionAuthorized: true,
  }
);

writeJson(
  manifestFile,
  unsafeManifest
);

r = run();

assert(
  r.result.status === 1,
  "executionAuthorized=true exits blocked"
);

assert(
  r.report.state === "BLOCKED",
  "executionAuthorized=true → BLOCKED"
);

/*
 * 6. Wallet safety violation.
 */
prepareSafeChain();

writeJson(
  manifestFile,
  makeManifest(
    "VERIFIED_READ_ONLY",
    {
      safety: {
        ...SAFETY,
        walletUsed: true,
      },
    }
  )
);

r = run();

assert(
  r.result.status === 1,
  "walletUsed=true exits blocked"
);

assert(
  r.report.state === "BLOCKED",
  "walletUsed=true → BLOCKED"
);

/*
 * 7. Signing safety violation.
 */
prepareSafeChain();

writeJson(
  manifestFile,
  makeManifest(
    "VERIFIED_READ_ONLY",
    {
      safety: {
        ...SAFETY,
        signingPerformed: true,
      },
    }
  )
);

r = run();

assert(
  r.result.status === 1,
  "signingPerformed=true exits blocked"
);

assert(
  r.report.state === "BLOCKED",
  "signingPerformed=true → BLOCKED"
);

/*
 * 8. Policy violation.
 */
prepareSafeChain();

writeJson(
  manifestFile,
  makeManifest(
    "VERIFIED_READ_ONLY",
    {
      policy: {
        ...POLICY,
        wallet: "USED",
      },
    }
  )
);

r = run();

assert(
  r.result.status === 1,
  "policy violation exits blocked"
);

assert(
  r.report.state === "BLOCKED",
  "policy violation → BLOCKED"
);

/*
 * 9. Phase 22 unsafe.
 */
prepareSafeChain();

const auditVerifyFile = path.join(
  OUT,
  "latest-provider-evidence-manifest-audit-verify.json"
);

writeJson(
  auditVerifyFile,
  makeReport(
    "AACP_PROVIDER_EVIDENCE_MANIFEST_AUDIT_VERIFY",
    "VERIFIED_READ_ONLY",
    {
      safety: {
        ...SAFETY,
        broadcastPerformed: true,
      },
    }
  )
);

r = run();

assert(
  r.result.status === 1,
  "Phase 22 unsafe exits blocked"
);

assert(
  r.report.state === "BLOCKED",
  "Phase 22 unsafe → BLOCKED"
);

/*
 * 10. Missing every artifact.
 */
fs.rmSync(OUT, {
  recursive: true,
  force: true,
});

r = run();

assert(
  r.result.status === 0,
  "all artifacts missing exits successfully"
);

assert(
  r.report.state === "INCOMPLETE",
  "all artifacts missing → INCOMPLETE"
);

assert(
  r.report.health.artifactsPresent === 0,
  "all artifacts missing → zero present"
);

assert(
  r.report.health.artifactsMissing === 11,
  "all artifacts missing → eleven missing"
);

assert(
  r.report.health.artifactsBlocked === 0,
  "all artifacts missing → zero blocked"
);

/*
 * 11. Output safety invariants.
 */
assert(
  r.report.mode === "READ_ONLY",
  "monitor mode is READ_ONLY"
);

assert(
  r.report.executionAuthorized === false,
  "monitor executionAuthorized=false"
);

for (const field of [
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
]) {
  assert(
    r.report.safety[field] === false,
    `monitor safety ${field}=false`
  );

  assert(
    r.report.sideEffects[field] === false,
    `monitor side-effect ${field}=false`
  );
}

/*
 * 12. Policy invariants.
 */
assert(
  r.report.policy.readOnly === true,
  "monitor policy readOnly=true"
);

assert(
  r.report.policy.failClosed === true,
  "monitor policy failClosed=true"
);

assert(
  r.report.policy.post === "NOT_PERFORMED",
  "monitor policy post=NOT_PERFORMED"
);

assert(
  r.report.policy.wallet === "NOT_USED",
  "monitor policy wallet=NOT_USED"
);

assert(
  r.report.policy.signing === "NOT_PERFORMED",
  "monitor policy signing=NOT_PERFORMED"
);

assert(
  r.report.policy.broadcast === "NOT_PERFORMED",
  "monitor policy broadcast=NOT_PERFORMED"
);

assert(
  r.report.policy.submission === "NOT_PERFORMED",
  "monitor policy submission=NOT_PERFORMED"
);

console.log(
  "ALL AACP EVIDENCE CHAIN HEALTH MONITOR TESTS PASSED"
);
