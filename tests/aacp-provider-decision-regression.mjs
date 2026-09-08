import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  decideProvider,
  buildProviderDecision,
  writeProviderDecision
} from "../src/aacp-provider-decision.mjs";

const safety = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false
};

const strongJob = {
  jobId: "decision-strong-001",
  status: "OPEN",
  title: "Smart Contract Security Audit",
  strategyType: "PROGRAM",
  qualification: "STRONG_MATCH",
  score: 100,
  artifactStatus: "TRUSTED_ARTIFACT",
  artifactTrusted: true
};

const weakJob = {
  jobId: "decision-blocked-001",
  status: "OPEN",
  title: "Generic Task",
  strategyType: "PROGRAM",
  qualification: "POOR_MATCH",
  score: 15,
  artifactStatus: "NO_ARTIFACT",
  artifactTrusted: false
};

assert.equal(
  decideProvider({
    state: "BACKEND_UNAVAILABLE",
    jobs: [strongJob],
    safety
  }).decision,
  "BACKEND_UNAVAILABLE"
);

assert.equal(
  decideProvider({
    state: "HEALTHY",
    jobs: [],
    safety
  }).decision,
  "NO_MATCH"
);

assert.equal(
  decideProvider({
    state: "DOWN",
    jobs: [strongJob],
    safety
  }).decision,
  "BLOCKED"
);

assert.equal(
  decideProvider({
    state: "UNKNOWN",
    jobs: [strongJob],
    safety
  }).decision,
  "BLOCKED"
);

assert.equal(
  decideProvider({
    state: "HEALTHY",
    jobs: [strongJob],
    safety: {
      ...safety,
      walletUsed: true
    }
  }).decision,
  "BLOCKED"
);

assert.equal(
  decideProvider({
    state: "HEALTHY",
    jobs: [strongJob],
    safety: {
      ...safety,
      signingPerformed: true
    }
  }).decision,
  "BLOCKED"
);

assert.equal(
  decideProvider({
    state: "HEALTHY",
    jobs: [strongJob],
    safety: {
      ...safety,
      submissionPerformed: true
    }
  }).decision,
  "BLOCKED"
);

const qualified =
  decideProvider({
    state: "HEALTHY",
    jobs: [weakJob, strongJob],
    safety
  });

assert.equal(
  qualified.decision,
  "QUALIFIED"
);

assert.equal(
  qualified.job.jobId,
  "decision-strong-001"
);

const blocked =
  decideProvider({
    state: "HEALTHY",
    jobs: [weakJob],
    safety
  });

assert.equal(
  blocked.decision,
  "BLOCKED"
);

assert.equal(
  blocked.job,
  null
);

const report =
  buildProviderDecision({
    state: "HEALTHY",
    jobs: [weakJob],
    safety
  });

assert.equal(
  report.mode,
  "READ_ONLY"
);

assert.equal(
  report.decision,
  "BLOCKED"
);

assert.equal(
  report.safety.postPerformed,
  false
);

assert.equal(
  report.safety.walletUsed,
  false
);

assert.equal(
  report.safety.signingPerformed,
  false
);

assert.equal(
  report.safety.broadcastPerformed,
  false
);

assert.equal(
  report.safety.submissionPerformed,
  false
);

const outputDir =
  fs.mkdtempSync(
    path.join(
      os.tmpdir(),
      "aacp-provider-decision-"
    )
  );

const written =
  writeProviderDecision(
    {
      state: "HEALTHY",
      jobs: [strongJob],
      safety
    },
    outputDir
  );

assert.ok(
  fs.existsSync(written.file)
);

assert.equal(
  written.decision.decision,
  "QUALIFIED"
);

console.log(
  "AACP PROVIDER DECISION REGRESSION"
);

console.log(
  "PASS: BACKEND_UNAVAILABLE"
);

console.log(
  "PASS: empty jobs → NO_MATCH"
);

console.log(
  "PASS: strong trusted job → QUALIFIED"
);

console.log(
  "PASS: non-qualified job → BLOCKED"
);

console.log(
  "PASS: READ_ONLY report"
);

console.log(
  "PASS: decision file generated"
);

console.log(
  "PASS: POST never performed"
);

console.log(
  "PASS: wallet never used"
);

console.log(
  "PASS: signing never performed"
);

console.log(
  "PASS: broadcast never performed"
);

console.log(
  "PASS: submission never performed"
);

console.log(
  "ALL PROVIDER DECISION TESTS PASSED"
);
