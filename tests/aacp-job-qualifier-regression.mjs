import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  qualifyJobs,
  writeQualification
} from "../src/aacp-job-qualifier.mjs";

import {
  createManifest
} from "../src/artifact-manifest.mjs";

import {
  createTrustedArtifactReference
} from "../src/trusted-artifact.mjs";

import {
  getStagingPath
} from "../src/source-router.mjs";

let passed = 0;
let failed = 0;

function test(name, condition) {
  if (condition) {
    console.log(`PASS: ${name}`);
    passed++;
  } else {
    console.log(`FAIL: ${name}`);
    failed++;
  }
}

console.log("========================================");
console.log(" AACP JOB QUALIFIER v2 REGRESSION");
console.log(" OFFLINE / READ ONLY");
console.log("========================================");

const tempDir = fs.mkdtempSync(
  path.join(
    os.tmpdir(),
    "aacp-qualifier-v2-"
  )
);

/*
 * Strong job.
 *
 * IMPORTANT:
 * source metadata alone must NOT make
 * the artifact trusted.
 */
const strongJob = {
  jobId: "security-strong-v2-001",
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Smart Contract Security Audit",
  description:
    "Audit Solidity smart contract for reentrancy and access control.",
  source: "Vulnerable.sol"
};

/*
 * Missing artifact job.
 */
const missingJob = {
  jobId: "security-missing-artifact-v2-001",
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Smart Contract Security Audit",
  description:
    "Find reentrancy and access control vulnerabilities."
};

/*
 * Poor capability match.
 */
const poorJob = {
  jobId: "graphic-design-v2-001",
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Graphic Design",
  description:
    "Create a logo and marketing banner."
};

/*
 * Closed job.
 */
const closedJob = {
  jobId: "closed-v2-001",
  status: "COMPLETED",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Smart Contract Security Audit",
  description:
    "Audit Solidity contract."
};

/*
 * First prove that metadata reference alone
 * does NOT produce a trusted artifact.
 */
const metadataOnly =
  qualifyJobs([strongJob])[0];

test(
  "metadata-only source is NOT trusted",
  metadataOnly.artifactTrusted === false
);

test(
  "metadata-only source classified as ARTIFACT_MISSING",
  metadataOnly.qualification === "ARTIFACT_MISSING"
);

/*
 * Now create a real local staged artifact
 * for the same job.
 */
const stagingDir =
  getStagingPath(
    strongJob.jobId
  );

fs.mkdirSync(
  stagingDir,
  { recursive: true }
);

const sourcePath =
  path.join(
    stagingDir,
    "Vulnerable.sol"
  );

fs.writeFileSync(
  sourcePath,
  `pragma solidity ^0.8.20;

contract Vulnerable {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function withdraw() external {
        payable(msg.sender).transfer(
            address(this).balance
        );
    }
}
`
);

/*
 * Create a job-bound manifest.
 */
const manifest =
  createManifest(
    strongJob.jobId,
    "Vulnerable.sol",
    strongJob
  );

test(
  "manifest created",
  manifest.allowed === true
);

test(
  "manifest contains job binding",
  Boolean(
    manifest.manifest?.jobBinding?.fingerprint
  )
);

/*
 * Create trusted reference from the staged artifact.
 */
const trustedReference =
  createTrustedArtifactReference(
    strongJob.jobId,
    "Vulnerable.sol"
  );

test(
  "trusted artifact reference created",
  trustedReference.allowed === true
);

test(
  "trusted reference contains SHA-256",
  /^[a-f0-9]{64}$/.test(
    trustedReference.reference?.artifact?.sha256 || ""
  )
);

/*
 * Qualify the job with the valid artifact.
 */
const qualifiedStrong =
  qualifyJobs([
    strongJob
  ])[0];

test(
  "strong security job classified",
  qualifiedStrong.qualification ===
    "STRONG_MATCH"
);

test(
  "security capability detected",
  qualifiedStrong.score >= 50
);

test(
  "trusted artifact detected",
  qualifiedStrong.artifactStatus ===
    "TRUSTED_ARTIFACT"
);

test(
  "artifact is trusted",
  qualifiedStrong.artifactTrusted === true
);

test(
  "trusted artifact SHA-256 present",
  /^[a-f0-9]{64}$/.test(
    qualifiedStrong.artifactSha256 || ""
  )
);

/*
 * Missing artifact remains blocked.
 */
const missing =
  qualifyJobs([
    missingJob
  ])[0];

test(
  "missing artifact classified",
  missing.qualification ===
    "ARTIFACT_MISSING"
);

test(
  "missing artifact is not trusted",
  missing.artifactTrusted === false
);

/*
 * Poor capability remains rejected.
 */
const poor =
  qualifyJobs([
    poorJob
  ])[0];

test(
  "poor capability match rejected",
  poor.qualification ===
    "POOR_MATCH"
);

/*
 * Invalid status remains rejected.
 */
const closed =
  qualifyJobs([
    closedJob
  ])[0];

test(
  "invalid status rejected",
  closed.qualification ===
    "INELIGIBLE_STATUS"
);

/*
 * Snapshot regression.
 */
const outputDir =
  path.join(
    tempDir,
    "snapshot"
  );

const written =
  writeQualification(
    [
      strongJob,
      missingJob,
      poorJob,
      closedJob
    ],
    outputDir
  );

test(
  "qualification snapshot written",
  fs.existsSync(written.file)
);

const snapshot =
  JSON.parse(
    fs.readFileSync(
      written.file,
      "utf8"
    )
  );

test(
  "snapshot version is 2.0.0",
  snapshot.version === "2.0.0"
);

test(
  "artifact trust mode recorded",
  snapshot.artifactTrust ===
    "MANIFEST_SHA256_JOB_BINDING"
);

test(
  "snapshot is READ_ONLY",
  snapshot.mode ===
    "READ_ONLY"
);

test(
  "trusted artifact count is correct",
  snapshot.summary.strongMatch === 1
);

test(
  "artifact missing count is correct",
  snapshot.summary.artifactMissing === 1
);

/*
 * Safety gates.
 */
test(
  "POST never performed",
  snapshot.safety.postPerformed === false
);

test(
  "wallet never used",
  snapshot.safety.walletUsed === false
);

test(
  "signing never performed",
  snapshot.safety.signingPerformed === false
);

test(
  "broadcast never performed",
  snapshot.safety.broadcastPerformed === false
);

test(
  "submission never performed",
  snapshot.safety.submissionPerformed === false
);

console.log("");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
console.log("========================================");

if (failed > 0) {
  process.exit(1);
}

console.log("");
console.log("AACP JOB QUALIFIER v2 REGRESSION PASSED");
console.log("");
console.log("Network     : NONE");
console.log("POST        : NOT PERFORMED");
console.log("Wallet      : NOT USED");
console.log("Signing     : NOT PERFORMED");
console.log("Broadcast   : NOT PERFORMED");
console.log("Submission  : NOT PERFORMED");
