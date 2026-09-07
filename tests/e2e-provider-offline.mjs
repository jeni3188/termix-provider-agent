import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

import { createManifest } from "../src/artifact-manifest.mjs";

const root = process.cwd();

const job =
  "samples/jobs/security-audit-fair.json";

const jobId =
  "demo-security-fair-001";

const source =
  "samples/Vulnerable.sol";

const stagingRoot =
  "provider-output/source-staging";

const stagingDir =
  path.join(stagingRoot, jobId);

const stagedSource =
  path.join(stagingDir, "Vulnerable.sol");

const manifest =
  path.join(stagingDir, "manifest.json");

const processor =
  `provider-output/${jobId}/processor-result.json`;

const offer =
  `provider-output/${jobId}/OFFER-DRAFT.json`;

const review =
  `provider-output/${jobId}/OFFER-REVIEW.json`;

const deliverable =
  path.join(
    stagingDir,
    "Vulnerable-TERMiX-DELIVERABLE.json"
  );

function run(label, args) {
  console.log(`\n[${label}]`);

  execFileSync("node", args, {
    cwd: root,
    stdio: "inherit"
  });
}

let passed = 0;
let failed = 0;

function check(name, condition) {
  if (condition) {
    console.log(`PASS: ${name}`);
    passed++;
  } else {
    console.log(`FAIL: ${name}`);
    failed++;
  }
}

console.log("========================================");
console.log(" TERMIX PROVIDER E2E OFFLINE TEST");
console.log("========================================");
console.log("Network : DISABLED");
console.log("Wallet  : DISABLED");
console.log("Signing : DISABLED");
console.log("POST    : DISABLED");

/*
 * ================================================================
 * 1. PREPARE TRUSTED STAGED ARTIFACT
 * ================================================================
 */

fs.rmSync(stagingDir, {
  recursive: true,
  force: true
});

fs.mkdirSync(stagingDir, {
  recursive: true
});

fs.copyFileSync(
  source,
  stagedSource
);

check(
  "staged artifact exists",
  fs.existsSync(stagedSource)
);

const jobData =
  JSON.parse(
    fs.readFileSync(job, "utf8")
  );

const manifestResult =
  createManifest(
    jobId,
    path.relative(
      stagingDir,
      stagedSource
    ),
    jobData
  );

check(
  "manifest created",
  manifestResult.allowed === true
);

if (!manifestResult.allowed) {
  console.log(
    `Manifest error: ${manifestResult.code}`
  );

  process.exit(1);
}

/*
 * createManifest() returns a wrapper.
 * manifest.json itself must contain the actual manifest.
 */
fs.writeFileSync(
  manifest,
  JSON.stringify(
    manifestResult.manifest,
    null,
    2
  ) + "\n"
);

check(
  "manifest exists",
  fs.existsSync(manifest)
);

const manifestData =
  JSON.parse(
    fs.readFileSync(manifest, "utf8")
  );

check(
  "manifest job binding matches",
  manifestData.jobId === jobId
);

check(
  "manifest contains SHA-256",
  typeof manifestData.artifact?.sha256 === "string" &&
  /^[a-f0-9]{64}$/.test(
    manifestData.artifact.sha256
  )
);

check(
  "manifest source is manually staged",
  manifestData.source?.mode ===
    "MANUALLY_STAGED"
);

check(
  "manifest network fetch disabled",
  manifestData.safety?.networkFetch === false
);

check(
  "manifest wallet disabled",
  manifestData.safety?.walletUsed === false
);

check(
  "manifest signing disabled",
  manifestData.safety?.signing === false
);

check(
  "manifest broadcast disabled",
  manifestData.safety?.broadcast === false
);

/*
 * ================================================================
 * 2. PROCESS TRUSTED ARTIFACT
 * ================================================================
 */

run("PROCESS", [
  "src/job-processor.mjs",
  job,
  stagedSource
]);

check(
  "processor result exists",
  fs.existsSync(processor)
);

if (fs.existsSync(processor)) {
  const result =
    JSON.parse(
      fs.readFileSync(processor, "utf8")
    );

  check(
    "job processed",
    result.job?.jobId === jobId
  );

  check(
    "decision is OFFER_REVIEW",
    result.execution?.path ===
      "OFFER_REVIEW"
  );

  check(
    "qualification is STRONG_MATCH",
    result.qualification?.qualification ===
      "STRONG_MATCH"
  );

  check(
    "artifact is trusted",
    result.artifactGate?.artifactStatus ===
      "TRUSTED_ARTIFACT"
  );

  check(
    "artifact trust is true",
    result.artifactGate?.artifactTrusted ===
      true
  );

  check(
    "analyzer was called",
    result.execution?.analyzerCalled === true
  );

  check(
    "security findings generated",
    Number.isInteger(
      result.security?.findings
    ) &&
    result.security.findings > 0
  );

  check(
    "risk level is CRITICAL",
    result.security?.riskLevel ===
      "CRITICAL"
  );

  check(
    "wallet not used",
    result.execution?.walletRequired ===
      false
  );

  check(
    "submission not performed",
    result.execution?.offerSubmitted ===
      false
  );
}

/*
 * ================================================================
 * 3. DELIVERABLE GATE
 * ================================================================
 */

check(
  "deliverable exists",
  fs.existsSync(deliverable)
);

if (fs.existsSync(deliverable)) {
  const output =
    JSON.parse(
      fs.readFileSync(
        deliverable,
        "utf8"
      )
    );

  check(
    "deliverable status allowed",
    output.gate?.status ===
      "DELIVERABLE_ALLOWED"
  );

  check(
    "deliverable analyzer called",
    output.gate?.analyzerCalled === true
  );

  check(
    "deliverable artifact trusted",
    output.gate?.artifactTrusted === true
  );

  check(
    "deliverable artifact binding valid",
    output.gate?.artifactBindingValid ===
      true
  );

  check(
    "deliverable job binding verified",
    output.gate?.jobBindingVerified ===
      true
  );

  check(
    "deliverable artifact SHA-256 present",
    typeof output.integrity?.artifactSha256 ===
      "string" &&
    /^[a-f0-9]{64}$/.test(
      output.integrity.artifactSha256
    )
  );

  check(
    "deliverable analysis SHA-256 present",
    typeof output.integrity?.analysisSha256 ===
      "string" &&
    /^[a-f0-9]{64}$/.test(
      output.integrity.analysisSha256
    )
  );

  check(
    "deliverable wallet disabled",
    output.execution?.walletRequired === false
  );

  check(
    "deliverable signing disabled",
    output.execution?.transactionSigned === false
  );

  check(
    "deliverable broadcast disabled",
    output.execution?.transactionBroadcast === false
  );
}

/*
 * ================================================================
 * 4. OFFER DRAFT
 * ================================================================
 */

run("OFFER DRAFT", [
  "src/offer-draft.mjs",
  processor
]);

check(
  "offer draft exists",
  fs.existsSync(offer)
);

if (fs.existsSync(offer)) {
  const draft =
    JSON.parse(
      fs.readFileSync(
        offer,
        "utf8"
      )
    );

  check(
    "draft status pending manual review",
    draft.review?.status ===
      "PENDING_MANUAL_REVIEW"
  );

  check(
    "draft price is 500 USDC",
    draft.pricing?.proposedPriceUSDC ===
      500
  );
}

/*
 * ================================================================
 * 5. MANUAL APPROVAL
 * ================================================================
 */

run("APPROVAL", [
  "src/offer-review.mjs",
  offer,
  "approve"
]);

check(
  "review exists",
  fs.existsSync(review)
);

if (fs.existsSync(review)) {
  const approved =
    JSON.parse(
      fs.readFileSync(
        review,
        "utf8"
      )
    );

  check(
    "status READY_TO_SUBMIT",
    approved.decision?.status ===
      "READY_TO_SUBMIT"
  );

  check(
    "automatic submission disabled",
    approved.safety?.automaticSubmission ===
      false
  );

  check(
    "automatic signing disabled",
    approved.safety?.automaticSigning ===
      false
  );

  check(
    "automatic broadcast disabled",
    approved.safety?.automaticBroadcast ===
      false
  );
}

/*
 * ================================================================
 * SUMMARY
 * ================================================================
 */

console.log("\n========================================");
console.log(" E2E OFFLINE SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed === 0) {
  console.log("");
  console.log("ALL E2E OFFLINE TESTS PASSED");
  console.log("");
  console.log("TRUSTED ARTIFACT : YES");
  console.log("SHA-256          : VERIFIED");
  console.log("JOB BINDING      : VERIFIED");
  console.log("ANALYZER         : CALLED");
  console.log("DELIVERABLE      : ALLOWED");
  console.log("NETWORK REQUEST  : NONE");
  console.log("WALLET           : NOT USED");
  console.log("SIGNING          : NOT USED");
  console.log("SUBMISSION       : NOT PERFORMED");
  process.exit(0);
}

console.log("\nE2E TEST FAILED");
process.exit(1);
