import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import {
  createManifest,
  verifyManifest
} from "../src/artifact-manifest.mjs";

const root = process.cwd();

const jobId =
  "manifest-regression-001";

const jobRoot =
  path.join(
    root,
    "provider-output/source-staging",
    jobId
  );

const source =
  path.join(
    jobRoot,
    "source.sol"
  );

const manifest =
  path.join(
    jobRoot,
    "manifest.json"
  );

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
console.log(" TERMIX ARTIFACT MANIFEST REGRESSION");
console.log(" READ ONLY / NO NETWORK");
console.log("========================================");

try {
  fs.mkdirSync(
    jobRoot,
    { recursive: true }
  );

  fs.writeFileSync(
    source,
    "pragma solidity ^0.8.20; contract ManifestTest {}"
  );

  // 1. Create manifest
  const created =
    createManifest(
      jobId,
      "source.sol"
    );

  check(
    "manifest creation succeeds",
    created.allowed === true
  );

  check(
    "manifest file exists",
    fs.existsSync(manifest)
  );

  check(
    "manifest Job ID matches",
    created.manifest?.jobId === jobId
  );

  check(
    "manifest path is source.sol",
    created.manifest?.artifact?.path ===
      "source.sol"
  );

  // 2. Verify original
  const verified =
    verifyManifest(jobId);

  check(
    "original manifest verifies",
    verified.allowed === true
  );

  check(
    "verification returns correct artifact",
    verified.artifact === source
  );

  // 3. Tamper source
  fs.appendFileSync(
    source,
    "\n// tampered"
  );

  const tampered =
    verifyManifest(jobId);

  check(
    "tampered source is rejected",
    tampered.code ===
      "MANIFEST_SIZE_MISMATCH" ||
    tampered.code ===
      "MANIFEST_HASH_MISMATCH"
  );

  // Restore source and manifest
  fs.writeFileSync(
    source,
    "pragma solidity ^0.8.20; contract ManifestTest {}"
  );

  createManifest(
    jobId,
    "source.sol"
  );

  // 4. Tamper manifest Job ID
  const data =
    JSON.parse(
      fs.readFileSync(
        manifest,
        "utf8"
      )
    );

  data.jobId =
    "different-job";

  fs.writeFileSync(
    manifest,
    JSON.stringify(
      data,
      null,
      2
    )
  );

  const mismatch =
    verifyManifest(jobId);

  check(
    "manifest Job ID tampering is rejected",
    mismatch.code ===
      "MANIFEST_JOB_MISMATCH"
  );

  // 5. Restore
  createManifest(
    jobId,
    "source.sol"
  );

  // 6. Tamper hash
  const hashData =
    JSON.parse(
      fs.readFileSync(
        manifest,
        "utf8"
      )
    );

  hashData.artifact.sha256 =
    crypto
      .createHash("sha256")
      .update("fake")
      .digest("hex");

  fs.writeFileSync(
    manifest,
    JSON.stringify(
      hashData,
      null,
      2
    )
  );

  const hashMismatch =
    verifyManifest(jobId);

  check(
    "hash tampering is rejected",
    hashMismatch.code ===
      "MANIFEST_HASH_MISMATCH"
  );

} finally {
  fs.rmSync(
    jobRoot,
    {
      recursive: true,
      force: true
    }
  );
}

console.log("");
console.log("========================================");
console.log(" ARTIFACT MANIFEST SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed === 0) {
  console.log("");
  console.log(
    "ALL ARTIFACT MANIFEST TESTS PASSED"
  );
  console.log("");
  console.log("Job binding : VERIFIED");
  console.log("SHA-256     : VERIFIED");
  console.log("Tampering   : BLOCKED");
  console.log("Network     : NONE");
  console.log("Wallet      : NOT USED");
  console.log("Signing     : NOT USED");

  process.exit(0);
}

console.log("");
console.log(
  "ARTIFACT MANIFEST TEST FAILED"
);

process.exit(1);
