import assert from "node:assert/strict";
import {
  buildQualifiedJobReport
} from "../src/aacp-qualified-job-report.mjs";

const safety = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false
};

const jobs = [
  {
    jobId: "security-strong-001",
    status: "OPEN",
    strategyType: "PROGRAM",
    title: "Smart Contract Security Audit",
    description: "Audit Solidity contract for reentrancy and access control",
    budget: 500000000,
    qualification: {
      score: 100,
      qualification: "STRONG_MATCH",
      securityMatch: true,
      artifactStatus: "TRUSTED_ARTIFACT",
      artifactTrusted: true
    }
  },
  {
    jobId: "security-blocked-001",
    status: "OPEN",
    strategyType: "PROGRAM",
    title: "Solidity Security Review",
    description: "Review smart contract vulnerabilities",
    budget: 500000000,
    qualification: {
      score: 85,
      qualification: "ARTIFACT_MISSING",
      securityMatch: true,
      artifactStatus: "NO_ARTIFACT",
      artifactTrusted: false
    }
  },
  {
    jobId: "general-001",
    status: "OPEN",
    strategyType: "PROGRAM",
    title: "Website Design",
    description: "Build a marketing website",
    budget: 200000000,
    qualification: {
      score: 20,
      qualification: "POOR_MATCH",
      securityMatch: false,
      artifactStatus: "NO_ARTIFACT",
      artifactTrusted: false
    }
  },
  {
    jobId: "security-strong-001",
    status: "OPEN",
    strategyType: "PROGRAM",
    title: "Duplicate",
    description: "Duplicate job",
    budget: 500000000,
    qualification: {
      score: 100,
      qualification: "STRONG_MATCH",
      securityMatch: true,
      artifactStatus: "TRUSTED_ARTIFACT",
      artifactTrusted: true
    }
  }
];

const report = buildQualifiedJobReport({
  state: "HEALTHY",
  previousState: "DOWN",
  recovered: true,
  jobs,
  safety
});

assert.equal(report.state, "HEALTHY");
assert.equal(report.recovered, true);

assert.equal(report.summary.observed, 4);
assert.equal(report.summary.unique, 3);
assert.equal(report.summary.qualified, 1);
assert.equal(report.summary.blocked, 2);

assert.equal(report.qualified.length, 1);
assert.equal(
  report.qualified[0].jobId,
  "security-strong-001"
);

assert.equal(
  report.qualified[0].qualification,
  "STRONG_MATCH"
);

assert.equal(
  report.qualified[0].artifact,
  "TRUSTED_ARTIFACT"
);

assert.equal(
  report.qualified[0].trusted,
  true
);

assert.equal(
  report.blocked.length,
  2
);

assert.ok(
  report.blocked.some(
    x => x.reason === "ARTIFACT_MISSING"
  )
);

assert.ok(
  report.blocked.some(
    x => x.reason === "POOR_MATCH"
  )
);

assert.deepEqual(report.safety, safety);

console.log("========================================");
console.log(" AACP QUALIFIED JOB REPORT REGRESSION");
console.log(" READ ONLY / NO SUBMISSION");
console.log("========================================");
console.log("PASS: recovery state preserved");
console.log("PASS: observed job count");
console.log("PASS: duplicate removed");
console.log("PASS: strong job qualified");
console.log("PASS: missing artifact blocked");
console.log("PASS: poor match blocked");
console.log("PASS: trusted artifact preserved");
console.log("PASS: safety invariants preserved");
console.log("");
console.log("AACP QUALIFIED JOB REPORT REGRESSION PASSED");
