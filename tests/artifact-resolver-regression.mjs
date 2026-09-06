import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

import {
  ensureStagingPath
} from "../src/source-router.mjs";

import {
  createManifest
} from "../src/artifact-manifest.mjs";

import {
  resolveStagedManifestArtifact,
  resolveExplicitOrStaged
} from "../src/artifact-resolver.mjs";

const jobId = "resolver-regression-001";

const job = {
  jobId,
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Artifact Resolver Regression",
  description: "Test staged manifest discovery.",
  deadline: 1799000000,
  providerId: null
};

const jobRoot = ensureStagingPath(jobId);
const source = path.join(
  jobRoot,
  "Contract.sol"
);

fs.writeFileSync(
  source,
  "pragma solidity ^0.8.20;\ncontract Contract { function test() external pure returns (uint256) { return 1; } }\n"
);

const manifest = createManifest(
  jobId,
  "Contract.sol",
  job
);

assert.equal(
  manifest.allowed,
  true
);

function pass(label) {
  console.log(`PASS: ${label}`);
}

console.log("========================================");
console.log(" TERMIX ARTIFACT RESOLVER REGRESSION");
console.log(" READ ONLY / NO NETWORK");
console.log("========================================");

const discovered =
  resolveStagedManifestArtifact(jobId);

assert.equal(discovered.allowed, true);
pass("staged manifest artifact is discovered");

assert.equal(
  discovered.code,
  "STAGED_MANIFEST_ARTIFACT_RESOLVED"
);
pass("discovery returns correct code");

assert.equal(
  discovered.relativePath,
  "Contract.sol"
);
pass("discovered artifact path is relative");

assert.equal(
  discovered.path,
  source
);
pass("discovered path points inside job staging");

const explicit =
  resolveExplicitOrStaged(
    jobId,
    "Contract.sol"
  );

assert.equal(explicit.allowed, true);
assert.equal(
  explicit.code,
  "EXPLICIT_SOURCE_REQUESTED"
);
pass("explicit source remains supported");

const required =
  resolveExplicitOrStaged(
    jobId,
    null
  );

assert.equal(required.allowed, false);
assert.equal(
  required.code,
  "SOURCE_REQUIRED"
);
pass("discovery remains disabled by default");

const enabled =
  resolveExplicitOrStaged(
    jobId,
    null,
    { allowDiscovery: true }
  );

assert.equal(enabled.allowed, true);
assert.equal(
  enabled.code,
  "STAGED_MANIFEST_ARTIFACT_RESOLVED"
);
pass("manifest discovery works when explicitly enabled");

const missing =
  resolveStagedManifestArtifact(
    "resolver-missing-001"
  );

assert.equal(missing.allowed, false);
assert.equal(
  missing.code,
  "MANIFEST_REQUIRED"
);
pass("missing manifest is blocked");

const traversalJob =
  "resolver-traversal-001";

const traversalRoot =
  ensureStagingPath(traversalJob);

const traversalSource =
  path.join(
    traversalRoot,
    "Contract.sol"
  );

fs.writeFileSync(
  traversalSource,
  "pragma solidity ^0.8.20;\ncontract Contract {}\n"
);

const traversalManifestPath =
  path.join(
    traversalRoot,
    "manifest.json"
  );

fs.writeFileSync(
  traversalManifestPath,
  JSON.stringify({
    jobId: traversalJob,
    artifact: {
      path: "../Contract.sol",
      size: 1,
      sha256: "0".repeat(64)
    }
  }, null, 2)
);

const traversal =
  resolveStagedManifestArtifact(
    traversalJob
  );

assert.equal(
  traversal.allowed,
  false
);

pass("manifest traversal is blocked");

const urlJob =
  "resolver-url-001";

const urlRoot =
  ensureStagingPath(urlJob);

fs.writeFileSync(
  path.join(urlRoot, "manifest.json"),
  JSON.stringify({
    jobId: urlJob,
    artifact: {
      path: "https://example.com/Contract.sol",
      size: 1,
      sha256: "0".repeat(64)
    }
  }, null, 2)
);

const url =
  resolveStagedManifestArtifact(
    urlJob
  );

assert.equal(
  url.allowed,
  false
);

pass("manifest URL artifact is blocked");

console.log("");
console.log("========================================");
console.log(" ARTIFACT RESOLVER SUMMARY");
console.log("========================================");
console.log("Passed: 10");
console.log("Failed: 0");
console.log("");
console.log("Discovery      : ENABLED ONLY BY FLAG");
console.log("Explicit       : ALLOWED");
console.log("Traversal      : BLOCKED");
console.log("URL            : BLOCKED");
console.log("Network        : NONE");
console.log("Wallet         : NOT USED");
console.log("Signing        : NOT USED");
console.log("Broadcast      : NOT USED");
console.log("");
console.log("ARTIFACT RESOLVER REGRESSION PASSED");
