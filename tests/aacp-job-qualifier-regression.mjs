import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  qualifyJobs,
  writeQualification
} from "../src/aacp-job-qualifier.mjs";

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
console.log(" AACP JOB QUALIFIER REGRESSION");
console.log(" OFFLINE / READ ONLY");
console.log("========================================");

const jobs = [
  {
    jobId: "security-strong-001",
    status: "OPEN",
    strategyType: "PROGRAM",
    budget: "500000000",
    title: "Smart Contract Security Audit",
    description:
      "Audit Solidity smart contract for reentrancy and access control.",
    source: "Vulnerable.sol"
  },
  {
    jobId: "security-missing-artifact-001",
    status: "OPEN",
    strategyType: "PROGRAM",
    budget: "500000000",
    title: "Smart Contract Security Audit",
    description:
      "Find reentrancy and access control vulnerabilities."
  },
  {
    jobId: "graphic-design-001",
    status: "OPEN",
    strategyType: "PROGRAM",
    budget: "500000000",
    title: "Graphic Design",
    description:
      "Create a logo and marketing banner."
  },
  {
    jobId: "closed-001",
    status: "COMPLETED",
    strategyType: "PROGRAM",
    budget: "500000000",
    title: "Smart Contract Security Audit",
    description: "Audit Solidity contract."
  }
];

const results = qualifyJobs(jobs);

test(
  "strong security job classified",
  results[0].qualification === "STRONG_MATCH"
);

test(
  "security capability detected",
  results[0].score >= 50
);

test(
  "artifact reference detected",
  results[0].artifactAvailable === true
);

test(
  "missing artifact classified",
  results[1].qualification === "ARTIFACT_MISSING"
);

test(
  "poor capability match rejected",
  results[2].qualification === "POOR_MATCH"
);

test(
  "invalid status rejected",
  results[3].qualification === "INELIGIBLE_STATUS"
);

const tempDir = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-qualifier-")
);

const written = writeQualification(
  jobs,
  tempDir
);

test(
  "qualification snapshot written",
  fs.existsSync(written.file)
);

const snapshot =
  JSON.parse(fs.readFileSync(written.file, "utf8"));

test(
  "snapshot version is 1.0.0",
  snapshot.version === "1.0.0"
);

test(
  "snapshot is READ_ONLY",
  snapshot.mode === "READ_ONLY"
);

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
console.log("AACP JOB QUALIFIER REGRESSION PASSED");
console.log("");
console.log("Network     : NONE");
console.log("POST        : NOT PERFORMED");
console.log("Wallet      : NOT USED");
console.log("Signing     : NOT PERFORMED");
console.log("Broadcast   : NOT PERFORMED");
console.log("Submission  : NOT PERFORMED");
