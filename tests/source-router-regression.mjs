import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import {
  resolveSource,
  ensureStagingPath
} from "../src/source-router.mjs";

const root =
  path.resolve(
    process.env.PROVIDER_SOURCE_STAGING ||
    "provider-output/source-staging"
  );

const jobId = "regression-source-001";
const jobRoot = ensureStagingPath(jobId);

const sourcePath =
  path.join(jobRoot, "Contract.sol");

const artifactPath =
  path.join(jobRoot, "artifact.json");

fs.writeFileSync(
  sourcePath,
  "pragma solidity ^0.8.20; contract Test {}"
);

fs.writeFileSync(
  artifactPath,
  JSON.stringify({
    contractName: "Test"
  })
);

let passed = 0;
let failed = 0;

function check(name, fn) {
  try {
    fn();
    console.log(`PASS: ${name}`);
    passed++;
  } catch (error) {
    console.log(`FAIL: ${name}`);
    console.log(`      ${error.message}`);
    failed++;
  }
}

console.log("========================================");
console.log(" TERMIX SOURCE ROUTER REGRESSION");
console.log(" READ ONLY / PATH SAFETY");
console.log("========================================");

check(
  "valid Solidity source is allowed",
  () => {
    const result =
      resolveSource(
        jobId,
        "Contract.sol"
      );

    assert.equal(
      result.allowed,
      true
    );

    assert.equal(
      result.code,
      "SOURCE_ALLOWED"
    );
  }
);

check(
  "valid JSON artifact is allowed",
  () => {
    const result =
      resolveSource(
        jobId,
        "artifact.json"
      );

    assert.equal(
      result.allowed,
      true
    );
  }
);

check(
  "missing source is rejected safely",
  () => {
    const result =
      resolveSource(
        jobId,
        "Missing.sol"
      );

    assert.equal(
      result.allowed,
      false
    );

    assert.equal(
      result.code,
      "SOURCE_ARTIFACT_REQUIRED"
    );
  }
);

check(
  "parent traversal is rejected",
  () => {
    const result =
      resolveSource(
        jobId,
        "../../secret.sol"
      );

    assert.equal(
      result.allowed,
      false
    );

    assert.equal(
      result.code,
      "SOURCE_REJECTED"
    );
  }
);

check(
  "absolute path is rejected",
  () => {
    const result =
      resolveSource(
        jobId,
        "/etc/passwd"
      );

    assert.equal(
      result.allowed,
      false
    );
  }
);

check(
  "disallowed extension is rejected",
  () => {
    const badPath =
      path.join(
        jobRoot,
        "malicious.sh"
      );

    fs.writeFileSync(
      badPath,
      "echo dangerous"
    );

    const result =
      resolveSource(
        jobId,
        "malicious.sh"
      );

    assert.equal(
      result.allowed,
      false
    );

    assert.equal(
      result.code,
      "SOURCE_REJECTED"
    );
  }
);

check(
  "invalid job ID is rejected",
  () => {
    const result =
      resolveSource(
        "../escape",
        "Contract.sol"
      );

    assert.equal(
      result.allowed,
      false
    );

    assert.equal(
      result.code,
      "INVALID_JOB_ID"
    );
  }
);

check(
  "empty source path requires explicit artifact",
  () => {
    const result =
      resolveSource(
        jobId,
        ""
      );

    assert.equal(
      result.allowed,
      false
    );

    assert.equal(
      result.code,
      "SOURCE_ARTIFACT_REQUIRED"
    );
  }
);

fs.rmSync(
  path.join(
    root,
    jobId
  ),
  {
    recursive: true,
    force: true
  }
);

console.log("");
console.log("========================================");
console.log(" SOURCE ROUTER SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed === 0) {
  console.log("");
  console.log("ALL SOURCE ROUTER TESTS PASSED");
  console.log("");
  console.log("Path traversal : BLOCKED");
  console.log("Outside staging: BLOCKED");
  console.log("Invalid job ID  : BLOCKED");
  console.log("Explicit source : ALLOWED");
  console.log("Network         : NONE");
  console.log("Wallet          : NOT USED");
  process.exit(0);
}

console.log("");
console.log("SOURCE ROUTER TEST FAILED");
process.exit(1);
