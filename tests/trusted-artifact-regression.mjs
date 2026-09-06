import fs from "node:fs";
import path from "node:path";
import {
  createTrustedArtifactReference,
  verifyTrustedArtifactReference
} from "../src/trusted-artifact.mjs";
import {
  ensureStagingPath,
  getStagingPath
} from "../src/source-router.mjs";

const root = process.cwd();
const jobId = "trusted-artifact-regression-001";
const staging = getStagingPath(jobId);

fs.rmSync(staging, {
  recursive: true,
  force: true
});

ensureStagingPath(jobId);

const source = path.join(
  staging,
  "Contract.sol"
);

fs.writeFileSync(
  source,
  `pragma solidity ^0.8.20;

contract SafeFixture {
    function ping() external pure returns (uint256) {
        return 1;
    }
}
`
);

let passed = 0;
let failed = 0;

function assert(condition, name) {
  if (condition) {
    console.log(`PASS: ${name}`);
    passed++;
  } else {
    console.error(`FAIL: ${name}`);
    failed++;
  }
}

const created =
  createTrustedArtifactReference(
    jobId,
    "Contract.sol"
  );

assert(
  created.allowed === true,
  "trusted reference is created"
);

assert(
  created.code ===
    "TRUSTED_ARTIFACT_REFERENCE_CREATED",
  "trusted reference creation code"
);

assert(
  created.reference?.artifact?.sha256?.length === 64,
  "trusted reference contains SHA-256"
);

assert(
  created.reference?.artifact?.size > 0,
  "trusted reference contains artifact size"
);

const verified =
  verifyTrustedArtifactReference(
    jobId,
    created.reference
  );

assert(
  verified.allowed === true,
  "matching artifact is verified"
);

assert(
  verified.code ===
    "TRUSTED_ARTIFACT_VERIFIED",
  "matching artifact verification code"
);

const tampered =
  JSON.parse(
    JSON.stringify(created.reference)
  );

const original = fs.readFileSync(source, "utf8");
const tamperedSource = original.replace("return 1;", "return 2;");
fs.writeFileSync(source, tamperedSource);

const tamperedResult =
  verifyTrustedArtifactReference(
    jobId,
    tampered
  );

assert(
  tamperedResult.allowed === false,
  "tampered artifact is blocked"
);

assert(
  tamperedResult.code ===
    "TRUSTED_ARTIFACT_HASH_MISMATCH",
  "tampered artifact gets hash mismatch"
);

const traversal =
  verifyTrustedArtifactReference(
    jobId,
    {
      ...created.reference,
      artifact: {
        ...created.reference.artifact,
        path: "../Contract.sol"
      }
    }
  );

assert(
  traversal.allowed === false,
  "traversal reference is blocked"
);

assert(
  traversal.code ===
    "TRUSTED_ARTIFACT_PATH_INVALID",
  "traversal gets path rejection"
);

const url =
  verifyTrustedArtifactReference(
    jobId,
    {
      ...created.reference,
      artifact: {
        ...created.reference.artifact,
        path: "https://example.com/Contract.sol"
      }
    }
  );

assert(
  url.allowed === false,
  "URL reference is blocked"
);

const wrongJob =
  verifyTrustedArtifactReference(
    "different-job",
    created.reference
  );

assert(
  wrongJob.allowed === false,
  "cross-job artifact reference is blocked"
);

assert(
  verified.safety?.networkFetch === false,
  "network fetch is disabled"
);

assert(
  verified.safety?.walletUsed === false &&
  verified.safety?.signing === false &&
  verified.safety?.broadcast === false,
  "wallet signing and broadcast remain disabled"
);

fs.rmSync(staging, {
  recursive: true,
  force: true
});

console.log("");
console.log("========================================");
console.log("TRUSTED ARTIFACT REGRESSION");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed > 0) {
  process.exit(1);
}

console.log("");
console.log("TRUSTED ARTIFACT REGRESSION PASSED");
console.log("Network : NONE");
console.log("URL Fetch : BLOCKED");
console.log("Traversal : BLOCKED");
console.log("Wallet : NOT USED");
console.log("Signing : NOT USED");
console.log("Broadcast : NOT USED");
