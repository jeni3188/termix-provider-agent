import assert from "node:assert/strict";
import {
  canonicalizeJob,
  fingerprintJob,
  validateJobBinding
} from "../src/job-binding.mjs";

const job = {
  jobId: "demo-security-fair-001",
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Smart Contract Security Audit",
  description:
    "Audit an EVM Solidity smart contract.",
  deadline: 1799000000,
  providerId: null
};

function check(label, condition) {
  console.log(
    `${condition ? "PASS" : "FAIL"}: ${label}`
  );

  return condition;
}

let passed = 0;
let failed = 0;

function test(label, condition) {
  if (check(label, condition)) {
    passed++;
  } else {
    failed++;
  }
}

console.log("========================================");
console.log(" TERMIX JOB BINDING REGRESSION");
console.log(" READ ONLY / NO NETWORK");
console.log("========================================");

const canonical =
  canonicalizeJob(job);

const fingerprint =
  fingerprintJob(job);

test(
  "canonical job representation is deterministic",
  canonical === canonicalizeJob({
    providerId: null,
    deadline: 1799000000,
    description:
      "Audit an EVM Solidity smart contract.",
    title: "Smart Contract Security Audit",
    budget: "500000000",
    strategyType: "PROGRAM",
    status: "OPEN",
    jobId: "demo-security-fair-001"
  })
);

test(
  "fingerprint is SHA-256",
  /^[a-f0-9]{64}$/.test(fingerprint)
);

const manifest = {
  jobId: job.jobId,
  jobBinding: {
    version: "1.0.0",
    fingerprint
  }
};

const valid =
  validateJobBinding(
    manifest,
    job
  );

test(
  "valid job binding is accepted",
  valid.allowed &&
  valid.code === "JOB_BINDING_VALID"
);

const changedBudget = {
  ...job,
  budget: "900000000"
};

const budgetResult =
  validateJobBinding(
    manifest,
    changedBudget
  );

test(
  "changed budget is rejected",
  !budgetResult.allowed &&
  budgetResult.code === "JOB_BINDING_MISMATCH"
);

const changedTitle = {
  ...job,
  title: "Different Job"
};

const titleResult =
  validateJobBinding(
    manifest,
    changedTitle
  );

test(
  "changed title is rejected",
  !titleResult.allowed &&
  titleResult.code === "JOB_BINDING_MISMATCH"
);

const changedDescription = {
  ...job,
  description:
    "Different security scope."
};

const descriptionResult =
  validateJobBinding(
    manifest,
    changedDescription
  );

test(
  "changed description is rejected",
  !descriptionResult.allowed &&
  descriptionResult.code === "JOB_BINDING_MISMATCH"
);

const changedJobId = {
  ...job,
  jobId: "different-job"
};

const idResult =
  validateJobBinding(
    manifest,
    changedJobId
  );

test(
  "changed Job ID is rejected",
  !idResult.allowed &&
  idResult.code === "JOB_BINDING_ID_MISMATCH"
);

const missingBinding =
  validateJobBinding(
    {
      jobId: job.jobId
    },
    job
  );

test(
  "missing fingerprint is rejected",
  !missingBinding.allowed &&
  missingBinding.code === "JOB_BINDING_REQUIRED"
);

const tamperedFingerprint =
  validateJobBinding(
    {
      jobId: job.jobId,
      jobBinding: {
        version: "1.0.0",
        fingerprint:
          "0".repeat(64)
      }
    },
    job
  );

test(
  "tampered fingerprint is rejected",
  !tamperedFingerprint.allowed &&
  tamperedFingerprint.code === "JOB_BINDING_MISMATCH"
);

console.log("");
console.log("========================================");
console.log(" JOB BINDING SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
console.log("");

if (failed === 0) {
  console.log(
    "ALL JOB BINDING TESTS PASSED"
  );
  console.log("");
  console.log(
    "Job identity   : VERIFIED"
  );
  console.log(
    "Fingerprint     : VERIFIED"
  );
  console.log(
    "Metadata change : BLOCKED"
  );
  console.log(
    "Network         : NONE"
  );
  console.log(
    "Wallet          : NOT USED"
  );

  process.exit(0);
}

process.exit(1);
