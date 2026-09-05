import fs from "node:fs";
import { execFileSync } from "node:child_process";

const root = process.cwd();

const job =
  "samples/jobs/security-audit-fair.json";

const source =
  "samples/Vulnerable.sol";

const processor =
  "provider-output/demo-security-fair-001/processor-result.json";

const offer =
  "provider-output/demo-security-fair-001/OFFER-DRAFT.json";

const review =
  "provider-output/demo-security-fair-001/OFFER-REVIEW.json";

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

run("PROCESS", [
  "src/job-processor.mjs",
  job,
  source
]);

check(
  "processor result exists",
  fs.existsSync(processor)
);

if (fs.existsSync(processor)) {
  const result =
    JSON.parse(fs.readFileSync(processor, "utf8"));

  check(
    "job processed",
    result.job?.jobId === "demo-security-fair-001"
  );

  check(
    "decision is OFFER_REVIEW",
    result.execution?.path === "OFFER_REVIEW"
  );

  check(
    "wallet not used",
    result.execution?.walletRequired === false
  );

  check(
    "submission not performed",
    result.execution?.offerSubmitted === false
  );
}

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
    JSON.parse(fs.readFileSync(offer, "utf8"));

  check(
    "draft status pending manual review",
    draft.review?.status === "PENDING_MANUAL_REVIEW"
  );

  check(
    "draft price is 500 USDC",
    draft.pricing?.proposedPriceUSDC === 500
  );
}

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
    JSON.parse(fs.readFileSync(review, "utf8"));

  check(
    "status READY_TO_SUBMIT",
    approved.decision?.status === "READY_TO_SUBMIT"
  );

  check(
    "automatic submission disabled",
    approved.safety?.automaticSubmission === false
  );

  check(
    "automatic signing disabled",
    approved.safety?.automaticSigning === false
  );

  check(
    "automatic broadcast disabled",
    approved.safety?.automaticBroadcast === false
  );
}

console.log("\n========================================");
console.log(" E2E OFFLINE SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed === 0) {
  console.log("");
  console.log("ALL E2E OFFLINE TESTS PASSED");
  console.log("");
  console.log("NETWORK REQUEST : NONE");
  console.log("WALLET          : NOT USED");
  console.log("SIGNING         : NOT USED");
  console.log("SUBMISSION      : NOT PERFORMED");
  process.exit(0);
}

console.log("\nE2E TEST FAILED");
process.exit(1);
