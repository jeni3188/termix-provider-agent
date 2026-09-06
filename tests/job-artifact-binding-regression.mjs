import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  intake
} from "../src/artifact-intake.mjs";
import {
  verifyManifest
} from "../src/artifact-manifest.mjs";

const jobId = "binding-integration-001";
const staging =
  path.resolve(
    "provider-output/source-staging",
    jobId
  );

const source =
  path.resolve(
    "samples/Vulnerable.sol"
  );

const job = {
  jobId,
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Smart Contract Security Audit",
  description:
    "Audit an EVM Solidity smart contract.",
  deadline: 1799000000,
  providerId: null
};

fs.rmSync(staging, {
  recursive: true,
  force: true
});

let passed = 0;
let failed = 0;

function test(label, condition) {
  if (condition) {
    console.log(`PASS: ${label}`);
    passed++;
  } else {
    console.log(`FAIL: ${label}`);
    failed++;
  }
}

console.log("========================================");
console.log(" JOB ↔ ARTIFACT BINDING REGRESSION");
console.log(" READ ONLY / NO NETWORK");
console.log("========================================");

const accepted =
  intake(
    jobId,
    source,
    null,
    job
  );

test(
  "valid job + artifact is accepted",
  accepted.allowed &&
  accepted.code === "INTAKE_READY"
);

test(
  "manifest contains job binding",
  typeof accepted.intake?.manifest?.jobBinding
    ?.fingerprint === "string"
);

const verified =
  verifyManifest(
    jobId,
    job
  );

test(
  "valid job binding verifies",
  verified.allowed &&
  verified.code === "MANIFEST_VALID"
);

const changedBudget = {
  ...job,
  budget: "900000000"
};

const budgetResult =
  verifyManifest(
    jobId,
    changedBudget
  );

test(
  "changed budget is blocked",
  !budgetResult.allowed &&
  budgetResult.code === "JOB_BINDING_MISMATCH"
);

const changedTitle = {
  ...job,
  title: "Different Scope"
};

const titleResult =
  verifyManifest(
    jobId,
    changedTitle
  );

test(
  "changed title is blocked",
  !titleResult.allowed &&
  titleResult.code === "JOB_BINDING_MISMATCH"
);

const changedDescription = {
  ...job,
  description:
    "Different audit scope."
};

const descriptionResult =
  verifyManifest(
    jobId,
    changedDescription
  );

test(
  "changed description is blocked",
  !descriptionResult.allowed &&
  descriptionResult.code === "JOB_BINDING_MISMATCH"
);

const wrongJob = {
  ...job,
  jobId: "different-job"
};

const wrongIdResult =
  verifyManifest(
    jobId,
    wrongJob
  );

test(
  "different Job ID is blocked",
  !wrongIdResult.allowed &&
  wrongIdResult.code === "JOB_BINDING_ID_MISMATCH"
);

const missingJob =
  intake(
    jobId,
    source
  );

test(
  "intake without job metadata is blocked",
  !missingJob.allowed &&
  missingJob.code === "JOB_METADATA_REQUIRED"
);

test(
  "network remains disabled",
  accepted.safety?.networkFetch === false &&
  accepted.safety?.networkRequest === false
);

test(
  "wallet remains unused",
  accepted.safety?.walletUsed === false
);

test(
  "signing remains disabled",
  accepted.safety?.signing === false
);

test(
  "broadcast remains disabled",
  accepted.safety?.broadcast === false
);

test(
  "automatic submission remains disabled",
  accepted.safety?.automaticSubmission === false
);

console.log("");
console.log("========================================");
console.log(" JOB ↔ ARTIFACT SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
console.log("");

if (failed === 0) {
  console.log(
    "ALL JOB ↔ ARTIFACT BINDING TESTS PASSED"
  );
  console.log("");
  console.log("Job identity : VERIFIED");
  console.log("Artifact     : VERIFIED");
  console.log("Fingerprint  : VERIFIED");
  console.log("Metadata     : TAMPER BLOCKED");
  console.log("Network      : NONE");
  console.log("Wallet       : NOT USED");
  console.log("Signing      : NOT USED");
  console.log("Broadcast    : NOT USED");
  process.exit(0);
}

process.exit(1);
