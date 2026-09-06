import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const ROOT = process.cwd();

const JOB_ID = "real-like-aacp-security-001";
const JOB_FILE = `/tmp/${JOB_ID}.json`;
const INTAKE_NO_ARTIFACT = `/tmp/${JOB_ID}-no-artifact-intake.json`;
const INTAKE_STAGED = `/tmp/${JOB_ID}-staged-intake.json`;
const SOURCE = `/tmp/${JOB_ID}.sol`;

const STAGING =
  path.join(ROOT, "provider-output", "source-staging", JOB_ID);

const RESULT =
  path.join(ROOT, "provider-output", "auto-processor-result.json");

let passed = 0;
let failed = 0;

function pass(name) {
  passed++;
  console.log(`PASS: ${name}`);
}

function fail(name, error = "") {
  failed++;
  console.log(`FAIL: ${name}${error ? ` — ${error}` : ""}`);
}

function assert(condition, name) {
  if (condition) pass(name);
  else fail(name);
}

function run(command, args, env = {}) {
  try {
    return {
      ok: true,
      code: 0,
      stdout: execFileSync(command, args, {
        cwd: ROOT,
        env: { ...process.env, ...env },
        encoding: "utf8"
      })
    };
  } catch (error) {
    return {
      ok: false,
      code: error.status ?? 1,
      stdout: `${error.stdout ?? ""}${error.stderr ?? ""}`
    };
  }
}

console.log("========================================");
console.log(" REAL-LIKE AACP ARTIFACT HANDOFF");
console.log(" READ ONLY / NO NETWORK / NO WALLET");
console.log("========================================");
console.log("");

const job = {
  jobId: JOB_ID,
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Smart Contract Security Audit",
  description:
    "Audit an EVM Solidity smart contract for reentrancy, access control, tx.origin, delegatecall and dangerous calls.",
  deadline: 1799000000,
  providerId: null
};

fs.writeFileSync(JOB_FILE, JSON.stringify(job, null, 2));

assert(fs.existsSync(JOB_FILE), "real-like AACP job fixture exists");

const intakeNoArtifact = {
  intake: "TermiX AACP Job Intake",
  version: "1.3.0",
  backend:
    "https://aacp-backend.termix.live",
  mode: "READ_ONLY",
  jobs: [job],
  summary: {
    uniqueJobs: 1,
    endpointErrors: 0,
    backendAvailable: true
  },
  safety: {
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false,
    submissionPerformed: false
  }
};

fs.writeFileSync(
  INTAKE_NO_ARTIFACT,
  JSON.stringify(intakeNoArtifact, null, 2)
);

assert(
  intakeNoArtifact.jobs.length === 1,
  "job enters intake without artifact"
);

const noArtifact = run(
  "node",
  [
    "src/auto-processor.mjs",
    INTAKE_NO_ARTIFACT
  ]
);

assert(
  noArtifact.code === 2,
  "missing artifact is rejected"
);

assert(
  noArtifact.stdout.includes("SOURCE_REQUIRED"),
  "missing artifact emits SOURCE_REQUIRED"
);

assert(
  !noArtifact.stdout.includes("PROCESSED"),
  "missing artifact is never processed"
);

const artifact = `
// Real-like local AACP artifact fixture.
// Deliberately simple and non-exploitable.

pragma solidity ^0.8.20;

contract RealLikeAuditTarget {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function setOwner(address nextOwner) external {
        require(msg.sender == owner, "not owner");
        owner = nextOwner;
    }
}
`;

fs.mkdirSync(STAGING, { recursive: true });

fs.writeFileSync(SOURCE, artifact);

const intakeResult = run(
  "node",
  [
    "src/artifact-intake.mjs",
    JOB_ID,
    SOURCE,
    "RealLikeAuditTarget.sol",
    JOB_FILE
  ]
);

assert(
  intakeResult.code === 0,
  "valid local artifact intake succeeds"
);

const stagedSource =
  path.join(STAGING, "RealLikeAuditTarget.sol");

const manifest =
  path.join(STAGING, "manifest.json");

assert(
  fs.existsSync(stagedSource),
  "artifact is staged inside job directory"
);

assert(
  fs.existsSync(manifest),
  "manifest is created"
);

const intakeStaged = {
  intake: "TermiX AACP Job Intake",
  version: "1.3.0",
  backend:
    "https://aacp-backend.termix.live",
  mode: "READ_ONLY",
  jobs: [job],
  summary: {
    uniqueJobs: 1,
    endpointErrors: 0,
    backendAvailable: true
  },
  safety: {
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false,
    submissionPerformed: false
  }
};

fs.writeFileSync(
  INTAKE_STAGED,
  JSON.stringify(intakeStaged, null, 2)
);

const stagedResult = run(
  "node",
  [
    "src/auto-processor.mjs",
    INTAKE_STAGED
  ],
  {
    PROVIDER_AUTO_DISCOVER_STAGED: "1"
  }
);

assert(
  stagedResult.code === 0,
  "staged artifact processing exits successfully"
);

assert(
  stagedResult.stdout.includes(
    "STAGED_MANIFEST_ARTIFACT_RESOLVED"
  ),
  "manifest artifact is discovered"
);

assert(
  stagedResult.stdout.includes("MANIFEST_VALID"),
  "manifest is validated"
);

assert(
  stagedResult.stdout.includes(
    "TRUSTED_ARTIFACT_VERIFIED"
  ),
  "trusted artifact is verified"
);

assert(
  stagedResult.stdout.includes("PROCESSED"),
  "valid staged artifact is processed"
);

assert(
  fs.existsSync(RESULT),
  "auto processor result exists"
);

const result = JSON.parse(
  fs.readFileSync(RESULT, "utf8")
);

assert(
  result.version === "1.8.0",
  "auto processor result version is 1.8.0"
);

assert(
  result.execution?.walletRequired === false,
  "wallet remains unused"
);

assert(
  result.execution?.offerSubmitted === false,
  "offer remains unsubmitted"
);

assert(
  result.execution?.transactionSigned === false,
  "transaction remains unsigned"
);

assert(
  result.execution?.transactionBroadcast === false,
  "transaction remains unbroadcast"
);

assert(
  result.execution?.mode === "READ_ONLY",
  "execution remains READ_ONLY"
);

const output =
  `${noArtifact.stdout}\n${stagedResult.stdout}`;

assert(
  !output.includes("LIVE_SUBMISSION"),
  "no live submission is triggered"
);

assert(
  !output.includes("X-Wallet-Signature"),
  "wallet signature header is never generated"
);

assert(
  !output.includes("PRIVATE_KEY"),
  "private key handling is absent"
);

console.log("");
console.log("========================================");
console.log(" REAL-LIKE AACP HANDOFF SUMMARY");
console.log("========================================");
console.log(`Passed : ${passed}`);
console.log(`Failed : ${failed}`);
console.log("");
console.log(
  `No artifact : ${
    noArtifact.code === 2 ? "BLOCKED" : "FAILED"
  }`
);
console.log(
  `Valid artifact : ${
    stagedResult.stdout.includes("PROCESSED")
      ? "PROCESSED"
      : "FAILED"
  }`
);
console.log("Network : NONE");
console.log("Wallet  : NOT USED");
console.log("Signing : NOT USED");
console.log("Broadcast : NOT USED");
console.log("Submission : NOT PERFORMED");

if (failed > 0) {
  console.log("");
  console.log("REAL-LIKE AACP HANDOFF REGRESSION FAILED");
  process.exit(1);
}

console.log("");
console.log("REAL-LIKE AACP HANDOFF REGRESSION PASSED");
