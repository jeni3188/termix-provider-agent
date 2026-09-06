import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import {
  createManifest
} from "../src/artifact-manifest.mjs";

const root = process.cwd();

const stagingRoot =
  path.join(
    root,
    "provider-output/source-staging"
  );

const jobId = "integration-source-001";

const jobRoot =
  path.join(stagingRoot, jobId);

const sourcePath =
  path.join(jobRoot, "Contract.sol");

const intake =
  "/tmp/auto-source-routing-intake.json";

const resultFile =
  path.join(
    root,
    "provider-output/auto-processor-result.json"
  );

function runAuto(intakeFile, source) {
  return spawnSync(
    process.execPath,
    [
      "src/auto-processor.mjs",
      intakeFile,
      source
    ],
    {
      cwd: root,
      encoding: "utf8"
    }
  );
}

function readResult() {
  return JSON.parse(
    fs.readFileSync(
      resultFile,
      "utf8"
    )
  );
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
console.log(" AUTO PROCESSOR SOURCE ROUTING");
console.log(" INTEGRATION REGRESSION");
console.log(" READ ONLY / NO NETWORK");
console.log("========================================");

try {
  fs.mkdirSync(
    jobRoot,
    { recursive: true }
  );

  fs.writeFileSync(
    sourcePath,
    "pragma solidity ^0.8.20; contract Test {}"
  );

  // Production-equivalent staging:
  // source must be accompanied by a valid artifact manifest
  // bound to the exact Job metadata used by the processor.
  const job = {
    jobId,
    status: "OPEN",
    strategyType: "PROGRAM",
    budget: "500000000",
    title: "Source Routing Regression",
    description: "Test",
    deadline: 1799000000,
    providerId: null
  };

  const manifest =
    createManifest(
      jobId,
      "Contract.sol",
      job
    );

  check(
    "valid staged source manifest is created",
    manifest.allowed === true
  );

  fs.writeFileSync(
    intake,
    JSON.stringify({
      summary: {
        backendAvailable: true
      },
      jobs: [
        job
      ]
    }, null, 2)
  );

  // 1. Valid staged source + valid manifest
  const valid =
    runAuto(
      intake,
      "Contract.sol"
    );

  const validOutput =
    `${valid.stdout}\n${valid.stderr}`;

  const validResult =
    readResult();

  check(
    "valid staged source exits 0",
    valid.status === 0
  );

  check(
    "valid staged source is processed",
    validOutput.includes(
      "Status : PROCESSED"
    )
  );

  check(
    "aggregate reports one processed job",
    validResult.results?.filter(x => x.status === "PROCESSED").length === 1
  );

  // 2. Traversal
  const traversal =
    runAuto(
      intake,
      "../../samples/Vulnerable.sol"
    );

  const traversalOutput =
    `${traversal.stdout}\n${traversal.stderr}`;

  const traversalResult =
    readResult();

  check(
    "traversal exits safely",
    traversal.status === 0
  );

  check(
    "traversal is rejected",
    traversalOutput.includes(
      "SOURCE_REJECTED"
    )
  );

  check(
    "traversal is not processed",
    traversalResult.results?.filter(x => x.status === "PROCESSED").length === 0
  );

  check(
    "traversal is not reported as failed",
    traversalResult.results?.filter(x => x.status === "FAILED").length === 0
  );

  // 3. Invalid job ID
  fs.writeFileSync(
    intake,
    JSON.stringify({
      summary: {
        backendAvailable: true
      },
      jobs: [
        {
          jobId: "../../escape",
          status: "OPEN",
          title: "Invalid Job ID",
          budget: "500000000"
        }
      ]
    }, null, 2)
  );

  const invalid =
    runAuto(
      intake,
      "Contract.sol"
    );

  const invalidOutput =
    `${invalid.stdout}\n${invalid.stderr}`;

  const invalidResult =
    readResult();

  check(
    "invalid job ID exits safely",
    invalid.status === 0
  );

  check(
    "invalid job ID is rejected",
    invalidOutput.includes(
      "INVALID_JOB_ID"
    )
  );

  check(
    "invalid job ID is not processed",
    invalidResult.results?.filter(x => x.status === "PROCESSED").length === 0
  );

  check(
    "invalid job ID is not reported as failed",
    invalidResult.results?.filter(x => x.status === "FAILED").length === 0
  );

} finally {
  fs.rmSync(
    jobRoot,
    {
      recursive: true,
      force: true
    }
  );

  fs.rmSync(
    intake,
    {
      force: true
    }
  );
}

console.log("");
console.log("========================================");
console.log(" SOURCE ROUTING INTEGRATION SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed === 0) {
  console.log("");
  console.log(
    "ALL SOURCE ROUTING INTEGRATION TESTS PASSED"
  );
  console.log("");
  console.log("Valid source  : PROCESSED");
  console.log("Traversal     : BLOCKED");
  console.log("Invalid ID    : BLOCKED");
  console.log("Network       : NONE");
  console.log("Wallet        : NOT USED");
  console.log("Signing       : NOT USED");
  process.exit(0);
}

console.log("");
console.log(
  "SOURCE ROUTING INTEGRATION TEST FAILED"
);

process.exit(1);
