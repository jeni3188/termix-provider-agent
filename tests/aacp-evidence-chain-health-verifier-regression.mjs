import fs from "fs";
import path from "path";
import os from "os";
import { spawnSync } from "child_process";

const ROOT = process.cwd();
const VERIFIER = path.join(
  ROOT,
  "src",
  "aacp-evidence-chain-health-verifier.mjs"
);

const EXPECTED_ARTIFACTS = 11;

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

function assert(condition, message) {
  if (!condition) {
    throw new Error(`ASSERT FAILED: ${message}`);
  }
}

function runCase(name, mutateSource = null) {
  const out = fs.mkdtempSync(
    path.join(os.tmpdir(), "aacp-chain-health-")
  );

  const source = path.join(
    out,
    "latest-aacp-evidence-chain-health.json"
  );

  const verify = path.join(
    out,
    "latest-aacp-evidence-chain-health-verify.json"
  );

  const artifacts = Array.from(
    { length: EXPECTED_ARTIFACTS },
    (_, i) => ({
      phase: `PHASE_${i + 12}`,
      key: `artifact${i + 1}`,
      file: `artifact-${i + 1}.json`,
      exists: true,
      valid: true,
      state: "VERIFIED_READ_ONLY",
      sourceState: "VERIFIED_READ_ONLY",
      sha256: "a".repeat(64),
      errors: [],
    })
  );

  const report = {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state: "VERIFIED_READ_ONLY",
    sourceState: "VERIFIED_READ_ONLY",
    executionAuthorized: false,

    safety: { ...SAFETY },

    sideEffects: { ...SAFETY },

    health: {
      artifactsExpected: EXPECTED_ARTIFACTS,
      artifactsPresent: EXPECTED_ARTIFACTS,
      artifactsMissing: 0,
      artifactsBlocked: 0,
      artifactsVerified: EXPECTED_ARTIFACTS,
      missing: [],
      blocked: [],
      errors: [],
      errorCount: 0,
      allArtifactsPresent: true,
      allArtifactsValid: true,
    },

    artifacts,

    policy: { ...POLICY },
  };

  if (mutateSource) {
    mutateSource(report);
  }

  fs.writeFileSync(
    source,
    JSON.stringify(report, null, 2)
  );

  const result = spawnSync(
    process.execPath,
    [VERIFIER],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OUTPUT_DIR: out,
      },
      encoding: "utf8",
    }
  );

  let output = null;

  if (fs.existsSync(verify)) {
    output = JSON.parse(
      fs.readFileSync(verify, "utf8")
    );
  }

  return {
    name,
    result,
    output,
    out,
  };
}

function expectState(
  name,
  expectedState,
  mutate = null,
  expectedExit = 0
) {
  const r = runCase(name, mutate);

  assert(
    r.result.status === expectedExit,
    `${name}: exit=${r.result.status}, expected=${expectedExit}`
  );

  assert(
    r.output,
    `${name}: verifier output missing`
  );

  assert(
    r.output.state === expectedState,
    `${name}: state=${r.output.state}, expected=${expectedState}`
  );

  return r;
}

console.log("AACP EVIDENCE CHAIN HEALTH VERIFIER REGRESSION");
console.log("READ ONLY / FAIL CLOSED");
console.log("==============================================");

let r;

r = expectState(
  "safe complete chain",
  "VERIFIED_READ_ONLY"
);

assert(
  r.output.verification.valid === true,
  "safe complete chain verification.valid"
);

assert(
  r.output.verification.errorCount === 0,
  "safe complete chain errorCount"
);

console.log("PASS: safe complete chain → VERIFIED_READ_ONLY");

r = expectState(
  "safe incomplete chain",
  "INCOMPLETE",
  report => {
    report.state = "INCOMPLETE";
    report.sourceState = "INCOMPLETE";

    report.health.artifactsPresent = 5;
    report.health.artifactsMissing = 6;
    report.health.artifactsVerified = 0;

    report.health.missing = [
      "artifact-6.json",
      "artifact-7.json",
      "artifact-8.json",
      "artifact-9.json",
      "artifact-10.json",
      "artifact-11.json",
    ];

    report.health.allArtifactsPresent = false;

    for (let i = 5; i < report.artifacts.length; i++) {
      report.artifacts[i].exists = false;
      report.artifacts[i].valid = false;
      report.artifacts[i].state = null;
      report.artifacts[i].sourceState = null;
      report.artifacts[i].sha256 = null;
      report.artifacts[i].errors = [
        `MISSING:artifact-${i + 1}.json`,
      ];
    }
  }
);

assert(
  r.output.verification.valid === false,
  "incomplete verification.valid=false"
);

console.log("PASS: safe incomplete chain → INCOMPLETE");

const missingSource = (() => {
  const out = fs.mkdtempSync(
    path.join(os.tmpdir(), "aacp-chain-health-missing-")
  );

  const result = spawnSync(
    process.execPath,
    [VERIFIER],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OUTPUT_DIR: out,
      },
      encoding: "utf8",
    }
  );

  const verify = path.join(
    out,
    "latest-aacp-evidence-chain-health-verify.json"
  );

  assert(
    result.status === 0,
    `missing source exit=${result.status}`
  );

  assert(
    fs.existsSync(verify),
    "missing source verifier output"
  );

  return JSON.parse(
    fs.readFileSync(verify, "utf8")
  );
})();

assert(
  missingSource.state === "INCOMPLETE",
  "missing source → INCOMPLETE"
);

console.log("PASS: missing source → INCOMPLETE");

{
  const out = fs.mkdtempSync(
    path.join(os.tmpdir(), "aacp-chain-health-invalid-")
  );

  const source = path.join(
    out,
    "latest-aacp-evidence-chain-health.json"
  );

  const verify = path.join(
    out,
    "latest-aacp-evidence-chain-health-verify.json"
  );

  fs.writeFileSync(
    source,
    "{invalid-json"
  );

  const invalidResult = spawnSync(
    process.execPath,
    [VERIFIER],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OUTPUT_DIR: out,
      },
      encoding: "utf8",
    }
  );

  assert(
    invalidResult.status === 1,
    `invalid JSON exit=${invalidResult.status}`
  );

  assert(
    fs.existsSync(verify),
    "invalid JSON verifier output"
  );

  const invalidOutput = JSON.parse(
    fs.readFileSync(verify, "utf8")
  );

  assert(
    invalidOutput.state === "BLOCKED",
    "invalid JSON → BLOCKED"
  );

  console.log(
    "PASS: invalid JSON → BLOCKED"
  );
}

const unsafeCases = [
  ["executionAuthorized=true", report => {
    report.executionAuthorized = true;
  }],

  ["walletUsed=true", report => {
    report.safety.walletUsed = true;
  }],

  ["signingPerformed=true", report => {
    report.safety.signingPerformed = true;
  }],

  ["broadcastPerformed=true", report => {
    report.safety.broadcastPerformed = true;
  }],

  ["submissionPerformed=true", report => {
    report.safety.submissionPerformed = true;
  }],

  ["side effect walletUsed=true", report => {
    report.sideEffects.walletUsed = true;
  }],

  ["policy readOnly=false", report => {
    report.policy.readOnly = false;
  }],

  ["policy failClosed=false", report => {
    report.policy.failClosed = false;
  }],

  ["policy post violation", report => {
    report.policy.post = "PERFORMED";
  }],

  ["policy signing violation", report => {
    report.policy.signing = "PERFORMED";
  }],

  ["policy broadcast violation", report => {
    report.policy.broadcast = "PERFORMED";
  }],
];

for (const [name, mutate] of unsafeCases) {
  const x = expectState(
    name,
    "BLOCKED",
    mutate,
    1
  );

  console.log(
    `PASS: ${name} → BLOCKED`
  );

  assert(
    x.output.executionAuthorized === false,
    `${name}: verifier executionAuthorized=false`
  );
}

r = expectState(
  "health expected count mismatch",
  "BLOCKED",
  report => {
    report.health.artifactsExpected = 10;
  },
  1
);

console.log(
  "PASS: health expected count mismatch → BLOCKED"
);

r = expectState(
  "health present missing mismatch",
  "BLOCKED",
  report => {
    report.health.artifactsPresent = 10;
    report.health.artifactsMissing = 0;
  },
  1
);

console.log(
  "PASS: health present/missing mismatch → BLOCKED"
);

r = expectState(
  "health missing array mismatch",
  "BLOCKED",
  report => {
    report.health.artifactsMissing = 1;
    report.health.missing = [];
  },
  1
);

console.log(
  "PASS: health missing array mismatch → BLOCKED"
);

r = expectState(
  "health valid flag mismatch",
  "BLOCKED",
  report => {
    report.health.allArtifactsPresent = false;
  },
  1
);

console.log(
  "PASS: health allArtifactsPresent mismatch → BLOCKED"
);

r = expectState(
  "artifact invalid without errors",
  "BLOCKED",
  report => {
    report.artifacts[0].valid = false;
    report.artifacts[0].errors = [];
  },
  1
);

console.log(
  "PASS: invalid artifact without errors → BLOCKED"
);

r = expectState(
  "artifact valid with errors",
  "BLOCKED",
  report => {
    report.artifacts[0].errors = [
      "TEST_ERROR",
    ];
  },
  1
);

console.log(
  "PASS: valid artifact with errors → BLOCKED"
);

r = expectState(
  "missing artifact inconsistent",
  "BLOCKED",
  report => {
    report.artifacts[0].exists = false;
    report.artifacts[0].valid = true;
    report.artifacts[0].state = "VERIFIED_READ_ONLY";
    report.artifacts[0].sourceState =
      "VERIFIED_READ_ONLY";
    report.artifacts[0].sha256 =
      "a".repeat(64);
  },
  1
);

console.log(
  "PASS: missing artifact inconsistent → BLOCKED"
);

r = expectState(
  "present artifact invalid sha",
  "BLOCKED",
  report => {
    report.artifacts[0].sha256 = "bad";
  },
  1
);

console.log(
  "PASS: present artifact invalid SHA → BLOCKED"
);

for (const [key, value] of Object.entries(
  POLICY
)) {
  r = expectState(
    `policy invariant ${key}`,
    "VERIFIED_READ_ONLY",
    report => {
      report.policy[key] = value;
    }
  );

  assert(
    r.output.policy[key] === value,
    `policy ${key}`
  );
}

console.log(
  "PASS: policy invariants preserved"
);

r = expectState(
  "output safety invariants",
  "VERIFIED_READ_ONLY"
);

assert(
  r.output.mode === "READ_ONLY",
  "output mode READ_ONLY"
);

assert(
  r.output.executionAuthorized === false,
  "output executionAuthorized=false"
);

for (const [key, value] of Object.entries(SAFETY)) {
  assert(
    r.output.safety[key] === false,
    `output safety ${key}=false`
  );

  assert(
    r.output.sideEffects[key] === false,
    `output sideEffects ${key}=false`
  );
}

console.log(
  "PASS: output safety invariants"
);

console.log("");
console.log(
  "ALL PROVIDER EVIDENCE CHAIN HEALTH VERIFIER TESTS PASSED"
);
