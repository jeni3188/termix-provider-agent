import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const root = process.cwd();

const jobFile =
  "samples/jobs/security-audit-fair.json";

const rawSource =
  "samples/Vulnerable.sol";

const stagedSource =
  "provider-output/source-staging/demo-security-fair-001/Vulnerable.sol";

const processorResult =
  "provider-output/demo-security-fair-001/processor-result.json";

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

function runProcessor(source) {
  execFileSync(
    process.execPath,
    [
      "src/job-processor.mjs",
      jobFile,
      source
    ],
    {
      cwd: root,
      encoding: "utf8"
    }
  );

  return JSON.parse(
    fs.readFileSync(
      processorResult,
      "utf8"
    )
  );
}

console.log("========================================");
console.log(" ANALYSIS GATE v1 REGRESSION");
console.log("========================================");
console.log("Network : DISABLED");
console.log("Wallet  : DISABLED");
console.log("Signing : DISABLED");
console.log("POST    : DISABLED");
console.log("");

/*
 * TEST 1
 * Raw source must never bypass artifact binding.
 */
console.log("[TEST 1] Raw source must be blocked");

const rawResult =
  runProcessor(rawSource);

check(
  "raw source gate blocked",
  rawResult.artifactGate?.allowed === false
);

check(
  "raw source binding invalid",
  rawResult.artifactGate?.artifactBindingValid === false
);

check(
  "raw source analyzer NOT called",
  rawResult.execution?.analyzerCalled === false
);

check(
  "raw source security assessment absent",
  rawResult.execution?.securityAssessment === false
);

console.log("");

/*
 * TEST 2
 * Trusted staged artifact must open analyzer gate.
 */
console.log("[TEST 2] Trusted artifact must be analyzed");

check(
  "staged artifact exists",
  fs.existsSync(stagedSource)
);

const trustedResult =
  runProcessor(stagedSource);

check(
  "trusted artifact gate allowed",
  trustedResult.artifactGate?.allowed === true
);

check(
  "trusted artifact status",
  trustedResult.artifactGate?.artifactStatus ===
    "TRUSTED_ARTIFACT"
);

check(
  "trusted artifact verified",
  trustedResult.artifactGate?.artifactTrusted === true
);

check(
  "artifact binding valid",
  trustedResult.artifactGate?.artifactBindingValid === true
);

check(
  "trusted analyzer called",
  trustedResult.execution?.analyzerCalled === true
);

check(
  "security assessment performed",
  trustedResult.execution?.securityAssessment === true
);

check(
  "expected findings",
  trustedResult.security?.findings === 6
);

check(
  "expected risk level",
  trustedResult.security?.riskLevel === "CRITICAL"
);

check(
  "expected risk score",
  trustedResult.security?.riskScore === 33
);

console.log("");

/*
 * TEST 3
 * Verify analyzer remains read-only.
 */
console.log("[TEST 3] Safety invariants");

check(
  "wallet not used",
  trustedResult.execution?.walletRequired === false
);

check(
  "submission not performed",
  trustedResult.execution?.offerSubmitted === false
);

check(
  "transaction not signed",
  trustedResult.execution?.transactionSigned === false
);

check(
  "transaction not broadcast",
  trustedResult.execution?.transactionBroadcast === false
);

check(
  "network fetch disabled",
  trustedResult.safety?.networkFetch === false
);

check(
  "wallet disabled",
  trustedResult.safety?.walletUsed === false
);

check(
  "signing disabled",
  trustedResult.safety?.signingPerformed === false
);

check(
  "broadcast disabled",
  trustedResult.safety?.broadcastPerformed === false
);

console.log("");
console.log("========================================");
console.log(" ANALYSIS GATE SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed === 0) {
  console.log("");
  console.log("ALL ANALYSIS GATE TESTS PASSED");
  console.log("");
  console.log("RAW SOURCE       : BLOCKED");
  console.log("TRUSTED ARTIFACT : ALLOWED");
  console.log("ANALYZER         : SAFE");
  console.log("WALLET           : NOT USED");
  console.log("SIGNING          : NOT PERFORMED");
  console.log("BROADCAST        : NOT PERFORMED");
  process.exit(0);
}

console.log("");
console.log("ANALYSIS GATE REGRESSION FAILED");
process.exit(1);
