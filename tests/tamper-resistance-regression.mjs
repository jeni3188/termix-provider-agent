import fs from "node:fs";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";

const root = process.cwd();

const jobFile =
  "samples/jobs/security-audit-fair.json";

const artifact =
  "provider-output/source-staging/demo-security-fair-001/Vulnerable.sol";

const manifest =
  "provider-output/source-staging/demo-security-fair-001/manifest.json";

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

function sha256(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function runProcessor() {
  execFileSync(
    process.execPath,
    [
      "src/job-processor.mjs",
      jobFile,
      artifact
    ],
    {
      cwd: root,
      encoding: "utf8",
      stdio: "inherit"
    }
  );

  return JSON.parse(
    fs.readFileSync(
      processorResult,
      "utf8"
    )
  );
}

if (!fs.existsSync(artifact)) {
  console.error("Artifact missing.");
  process.exit(1);
}

if (!fs.existsSync(manifest)) {
  console.error("Manifest missing.");
  process.exit(1);
}

const originalBytes =
  fs.readFileSync(artifact);

const originalHash =
  sha256(artifact);

let tampered = false;

console.log("========================================");
console.log(" TAMper-RESISTANCE REGRESSION");
console.log("========================================");
console.log("Network : DISABLED");
console.log("Wallet  : DISABLED");
console.log("Signing : DISABLED");
console.log("POST    : DISABLED");
console.log("");

try {
  /*
   * TEST 1
   * Baseline trusted artifact.
   */
  console.log("[TEST 1] Baseline trusted artifact");

  const baseline =
    runProcessor();

  check(
    "baseline artifact trusted",
    baseline.artifactGate?.artifactTrusted === true
  );

  check(
    "baseline binding valid",
    baseline.artifactGate?.artifactBindingValid === true
  );

  check(
    "baseline analyzer called",
    baseline.execution?.analyzerCalled === true
  );

  const manifestData =
    JSON.parse(
      fs.readFileSync(
        manifest,
        "utf8"
      )
    );

  const manifestHash =
    manifestData.artifact?.sha256 ??
    manifestData.sha256 ??
    null;

  check(
    "manifest contains SHA-256",
    typeof manifestHash === "string"
  );

  check(
    "baseline artifact hash matches manifest",
    manifestHash === originalHash
  );

  console.log("");

  /*
   * TEST 2
   * Tamper with artifact.
   */
  console.log("[TEST 2] Tamper artifact");

  fs.appendFileSync(
    artifact,
    "\n// TAMPER TEST - MUST BE REJECTED\n"
  );

  tampered = true;

  const tamperedHash =
    sha256(artifact);

  check(
    "artifact hash changed",
    tamperedHash !== originalHash
  );

  check(
    "tampered hash differs from manifest",
    tamperedHash !== manifestHash
  );

  console.log(
    `Original SHA-256 : ${originalHash}`
  );

  console.log(
    `Tampered SHA-256 : ${tamperedHash}`
  );

  console.log("");

  /*
   * TEST 3
   * Tampered artifact must close the gate.
   */
  console.log("[TEST 3] Tampered artifact must be blocked");

  const blocked =
    runProcessor();

  check(
    "tampered artifact not trusted",
    blocked.artifactGate?.artifactTrusted === false
  );

  check(
    "tampered artifact gate blocked",
    blocked.artifactGate?.allowed === false
  );

  check(
    "tampered analyzer NOT called",
    blocked.execution?.analyzerCalled === false
  );

  check(
    "tampered security assessment absent",
    blocked.execution?.securityAssessment === false
  );

  check(
    "tampered artifact binding invalid",
    blocked.artifactGate?.artifactBindingValid === false
  );

  console.log("");

  /*
   * TEST 4
   * Restore original bytes.
   */
  console.log("[TEST 4] Restore original artifact");

  fs.writeFileSync(
    artifact,
    originalBytes
  );

  tampered = false;

  const restoredHash =
    sha256(artifact);

  check(
    "artifact restored",
    restoredHash === originalHash
  );

  check(
    "restored hash matches manifest",
    restoredHash === manifestHash
  );

  console.log("");

  /*
   * TEST 5
   * Analyzer must work again after restoration.
   */
  console.log("[TEST 5] Restored artifact");

  const restored =
    runProcessor();

  check(
    "restored artifact trusted",
    restored.artifactGate?.artifactTrusted === true
  );

  check(
    "restored binding valid",
    restored.artifactGate?.artifactBindingValid === true
  );

  check(
    "restored analyzer called",
    restored.execution?.analyzerCalled === true
  );

  check(
    "restored findings correct",
    restored.security?.findings === 6
  );

  check(
    "restored risk correct",
    restored.security?.riskLevel === "CRITICAL"
  );

  check(
    "restored risk score correct",
    restored.security?.riskScore === 33
  );

  console.log("");

  /*
   * TEST 6
   * Safety invariants.
   */
  console.log("[TEST 6] Safety invariants");

  check(
    "wallet not used",
    restored.execution?.walletRequired === false
  );

  check(
    "submission not performed",
    restored.execution?.offerSubmitted === false
  );

  check(
    "transaction not signed",
    restored.execution?.transactionSigned === false
  );

  check(
    "transaction not broadcast",
    restored.execution?.transactionBroadcast === false
  );

  check(
    "network fetch disabled",
    restored.safety?.networkFetch === false
  );

} finally {
  /*
   * Absolute cleanup guarantee.
   */
  if (tampered) {
    fs.writeFileSync(
      artifact,
      originalBytes
    );

    console.log("");
    console.log(
      "CLEANUP: original artifact restored."
    );
  }
}

console.log("");
console.log("========================================");
console.log(" TAMPER-RESISTANCE SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed === 0) {
  console.log("");
  console.log("ALL TAMPER-RESISTANCE TESTS PASSED");
  console.log("");
  console.log("ORIGINAL ARTIFACT : VERIFIED");
  console.log("TAMPERED ARTIFACT : BLOCKED");
  console.log("ANALYZER          : FAIL-CLOSED");
  console.log("RESTORATION       : VERIFIED");
  console.log("WALLET            : NOT USED");
  console.log("SIGNING           : NOT PERFORMED");
  console.log("BROADCAST         : NOT PERFORMED");
  process.exit(0);
}

console.log("");
console.log("TAMPER-RESISTANCE REGRESSION FAILED");
process.exit(1);
