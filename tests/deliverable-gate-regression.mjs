import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";

import { createDeliverable } from "../src/deliverable-gate.mjs";
import {
  createManifest
} from "../src/artifact-manifest.mjs";

const jobId = "demo-deliverable-gate-001";

const stagingDir =
  path.resolve(
    "provider-output",
    "source-staging",
    jobId
  );

const artifactPath =
  path.join(
    stagingDir,
    "Vulnerable.sol"
  );

const manifestPath =
  path.join(
    stagingDir,
    "manifest.json"
  );

const job = {
  jobId,
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Smart Contract Security Audit",
  description:
    "Audit an EVM Solidity smart contract for security vulnerabilities."
};

const source = `
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Vulnerable {
    address public owner;

    function withdraw(address payable to) external {
        to.call{value: address(this).balance}("");
    }
}
`;

let passed = 0;
let failed = 0;

function pass(name) {
  passed++;
  console.log(`PASS: ${name}`);
}

function fail(name, error) {
  failed++;
  console.error(`FAIL: ${name}`);
  if (error) {
    console.error(error);
  }
}

function expect(name, fn) {
  try {
    fn();
    pass(name);
  } catch (error) {
    fail(name, error.message);
  }
}

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

fs.rmSync(
  stagingDir,
  {
    recursive: true,
    force: true
  }
);

fs.mkdirSync(
  stagingDir,
  {
    recursive: true
  }
);

fs.writeFileSync(
  artifactPath,
  source
);

/*
 * Create trusted manifest.
 */
const manifestResult =
  createManifest(
    jobId,
    artifactPath,
    job
  );

if (!manifestResult.allowed) {
  throw new Error(
    `manifest creation failed: ${manifestResult.code}`
  );
}

/*
 * createManifest() returns a result wrapper.
 * manifest.json itself must contain only the
 * actual manifest object consumed by verifyManifest().
 */
fs.writeFileSync(
  manifestPath,
  JSON.stringify(
    manifestResult.manifest,
    null,
    2
  ) + "\n"
);

/*
 * Obtain real analyzer output.
 */
const analysisRaw =
  execFileSync(
    process.execPath,
    [
      "src/analyze.mjs",
      artifactPath
    ],
    {
      encoding: "utf8"
    }
  );

const analysis =
  JSON.parse(
    analysisRaw
  );

/*
 * 1. Valid trusted artifact + valid analysis.
 */
expect(
  "trusted artifact + valid analysis is allowed",
  () => {
    const result =
      createDeliverable({
        job,
        artifactPath,
        analysis,
        analyzerCalled: true
      });

    if (!result.allowed) {
      throw new Error(
        `expected ALLOW, got ${result.code}`
      );
    }

    if (
      result.code !==
      "DELIVERABLE_ALLOWED"
    ) {
      throw new Error(
        `unexpected code: ${result.code}`
      );
    }
  }
);

/*
 * 2. Missing analysis.
 */
expect(
  "missing analysis is blocked",
  () => {
    const result =
      createDeliverable({
        job,
        artifactPath,
        analysis: null,
        analyzerCalled: false
      });

    if (result.allowed) {
      throw new Error(
        "missing analysis was incorrectly allowed"
      );
    }
  }
);

/*
 * 3. Tamper artifact after manifest creation.
 */
const original =
  fs.readFileSync(
    artifactPath
  );

fs.appendFileSync(
  artifactPath,
  "\n// TAMPERED\n"
);

expect(
  "tampered artifact is blocked",
  () => {
    const result =
      createDeliverable({
        job,
        artifactPath,
        analysis,
        analyzerCalled: true
      });

    if (result.allowed) {
      throw new Error(
        "tampered artifact was incorrectly allowed"
      );
    }

    if (
      result.code !==
      "ARTIFACT_VERIFICATION_FAILED"
    ) {
      throw new Error(
        `unexpected tamper code: ${result.code}`
      );
    }
  }
);

/*
 * Restore artifact.
 */
fs.writeFileSync(
  artifactPath,
  original
);

/*
 * 4. Restored artifact works again.
 */
expect(
  "restored artifact is allowed again",
  () => {
    const result =
      createDeliverable({
        job,
        artifactPath,
        analysis,
        analyzerCalled: true
      });

    if (!result.allowed) {
      throw new Error(
        `restored artifact blocked: ${result.code}`
      );
    }
  }
);

/*
 * 5. Raw source outside staging cannot be used.
 */
const rawSource =
  path.resolve(
    "samples",
    "Vulnerable.sol"
  );

expect(
  "raw source path is blocked",
  () => {
    const result =
      createDeliverable({
        job,
        artifactPath: rawSource,
        analysis,
        analyzerCalled: true
      });

    if (result.allowed) {
      throw new Error(
        "raw source was incorrectly allowed"
      );
    }
  }
);

/*
 * 6. Modified job binding must fail.
 */
const modifiedJob = {
  ...job,
  title:
    "Different Job"
};

expect(
  "modified job binding is blocked",
  () => {
    const result =
      createDeliverable({
        job: modifiedJob,
        artifactPath,
        analysis,
        analyzerCalled: true
      });

    if (result.allowed) {
      throw new Error(
        "modified job binding was incorrectly allowed"
      );
    }
  }
);

/*
 * 7. Valid integrity fingerprint exists.
 */
expect(
  "artifact SHA-256 fingerprint is present",
  () => {
    const hash =
      sha256File(
        artifactPath
      );

    if (
      !/^[a-f0-9]{64}$/.test(hash)
    ) {
      throw new Error(
        "invalid SHA-256 fingerprint"
      );
    }
  }
);

console.log("");
console.log(
  `Passed: ${passed} Failed: ${failed}`
);

process.exit(
  failed === 0
    ? 0
    : 1
);
