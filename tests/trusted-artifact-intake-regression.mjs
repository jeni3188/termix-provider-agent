import fs from "node:fs";
import path from "node:path";

import {
  intake
} from "../src/artifact-intake.mjs";

import {
  verifyTrustedArtifactReference
} from "../src/trusted-artifact.mjs";

import {
  getStagingPath
} from "../src/source-router.mjs";

const root = process.cwd();

const job = {
  jobId: "trusted-intake-regression-001",
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Trusted Artifact Intake Regression",
  description:
    "Regression test for post-intake artifact tampering.",
  deadline: 1799000000,
  providerId: null
};

const jobId = job.jobId;

const workDir = path.join(
  "/tmp",
  "trusted-artifact-intake-regression"
);

fs.rmSync(workDir, {
  recursive: true,
  force: true
});

fs.mkdirSync(workDir, {
  recursive: true
});

const source = path.join(
  workDir,
  "Contract.sol"
);

fs.writeFileSync(
  source,
  `pragma solidity ^0.8.20;

contract SafeFixture {
    function ping() external pure returns (uint256) {
        return 1;
    }
}
`
);

let passed = 0;
let failed = 0;

function assert(condition, name) {
  if (condition) {
    console.log(`PASS: ${name}`);
    passed++;
  } else {
    console.error(`FAIL: ${name}`);
    failed++;
  }
}

/*
 * Step 1:
 * Perform normal local artifact intake.
 */
const result = intake(
  jobId,
  source,
  "Contract.sol",
  job
);

assert(
  result.allowed === true,
  "initial artifact intake succeeds"
);

assert(
  result.code === "INTAKE_READY",
  "initial intake returns INTAKE_READY"
);

const trusted =
  result.intake?.manifest?.trustedArtifact;

assert(
  typeof trusted?.sha256 === "string" &&
  trusted.sha256.length === 64,
  "intake stores trusted artifact SHA-256"
);

assert(
  Number.isInteger(trusted?.size) &&
  trusted.size > 0,
  "intake stores trusted artifact size"
);

const staging =
  getStagingPath(jobId);

const staged =
  path.join(staging, "Contract.sol");

assert(
  fs.existsSync(staged),
  "staged artifact exists"
);

/*
 * Step 2:
 * Verify immediately after intake.
 */
const reference = {
  version: trusted.version,
  jobId,
  source: {
    mode: "LOCAL_STAGING_ONLY"
  },
  artifact: {
    path: trusted.path,
    size: trusted.size,
    sha256: trusted.sha256
  }
};

const verified =
  verifyTrustedArtifactReference(
    jobId,
    reference
  );

assert(
  verified.allowed === true,
  "post-intake artifact verifies"
);

assert(
  verified.code ===
    "TRUSTED_ARTIFACT_VERIFIED",
  "post-intake verification succeeds"
);

/*
 * Step 3:
 * Tamper with the staged artifact.
 *
 * Keep the same file size so the test specifically
 * exercises SHA-256 integrity verification.
 */
const original =
  fs.readFileSync(staged, "utf8");

const tampered =
  original.replace(
    "return 1;",
    "return 2;"
  );

assert(
  tampered.length === original.length,
  "tamper preserves artifact size"
);

fs.writeFileSync(
  staged,
  tampered
);

/*
 * Step 4:
 * Re-verify.
 */
const afterTamper =
  verifyTrustedArtifactReference(
    jobId,
    reference
  );

assert(
  afterTamper.allowed === false,
  "post-intake tampering is blocked"
);

assert(
  afterTamper.code ===
    "TRUSTED_ARTIFACT_HASH_MISMATCH",
  "post-intake tampering produces hash mismatch"
);

/*
 * Security invariant:
 * A tampered artifact must never be treated as
 * analyzer-ready.
 */
assert(
  afterTamper.allowed !== true,
  "tampered artifact cannot reach analyzer gate"
);

assert(
  afterTamper.safety?.walletUsed !== true,
  "tampering does not require wallet"
);

assert(
  afterTamper.safety?.signing !== true,
  "tampering does not trigger signing"
);

assert(
  afterTamper.safety?.broadcast !== true,
  "tampering does not trigger broadcast"
);

fs.rmSync(workDir, {
  recursive: true,
  force: true
});

fs.rmSync(
  getStagingPath(jobId),
  {
    recursive: true,
    force: true
  }
);

console.log("");
console.log("========================================");
console.log("TRUSTED ARTIFACT + INTAKE REGRESSION");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed > 0) {
  process.exit(1);
}

console.log("");
console.log("TRUSTED ARTIFACT INTAKE REGRESSION PASSED");
console.log("Initial Intake : READY");
console.log("Integrity      : VERIFIED");
console.log("Tampering      : BLOCKED");
console.log("Analyzer Gate  : BLOCKED");
console.log("Network        : NONE");
console.log("Wallet         : NOT USED");
console.log("Signing        : NOT USED");
console.log("Broadcast      : NOT USED");
