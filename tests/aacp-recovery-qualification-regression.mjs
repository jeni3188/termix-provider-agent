import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  createManifest
} from "../src/artifact-manifest.mjs";

import {
  createTrustedArtifactReference
} from "../src/trusted-artifact.mjs";

import { observeRecovery } from "../src/aacp-recovery-observer.mjs";
import {
  writeSnapshot
} from "../src/aacp-job-inspector.mjs";
import {
  writeQualification
} from "../src/aacp-job-qualifier.mjs";

let passed = 0;
let failed = 0;
const methods = [];

function test(name, condition) {
  if (condition) {
    console.log(`PASS: ${name}`);
    passed++;
  } else {
    console.log(`FAIL: ${name}`);
    failed++;
  }
}

console.log("========================================");
console.log(" AACP RECOVERY → QUALIFICATION");
console.log(" MOCK HTTP / FULL READ ONLY");
console.log("========================================");

const job = {
  jobId: "recovered-security-001",
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Smart Contract Security Audit",
  description:
    "Audit Solidity smart contract for reentrancy and access control.",
  source: "Vulnerable.sol"
};

const mockFetch = async (url, options = {}) => {
  methods.push(options.method || "GET");

  if (options.method && options.method !== "GET") {
    throw new Error("NON_GET_REQUEST_BLOCKED");
  }

  const headers = new Headers({
    "content-type": "application/json"
  });

  if (url.endsWith("/config")) {
    return new Response(
      JSON.stringify({
        network: "bsc-testnet",
        status: "healthy"
      }),
      {
        status: 200,
        headers
      }
    );
  }

  if (url.includes("status=OPEN")) {
    return new Response(
      JSON.stringify({ jobs: [job] }),
      {
        status: 200,
        headers
      }
    );
  }

  if (url.includes("status=FUNDED")) {
    return new Response(
      JSON.stringify({ jobs: [] }),
      {
        status: 200,
        headers
      }
    );
  }

  return new Response(
    JSON.stringify({ jobs: [] }),
    {
      status: 200,
      headers
    }
  );
};

const tempDir = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-recovery-qualification-")
);


const stagingRoot = path.resolve(
  "provider-output",
  "source-staging",
  job.jobId
);

fs.mkdirSync(stagingRoot, {
  recursive: true
});

const stagedSource = path.join(
  stagingRoot,
  "Vulnerable.sol"
);

const sourceFixture = path.resolve(
  "samples",
  "Vulnerable.sol"
);

fs.copyFileSync(
  sourceFixture,
  stagedSource
);

const manifestResult = createManifest(
  job.jobId,
  "Vulnerable.sol",
  job
);

if (!manifestResult.allowed) {
  throw new Error(
    `MANIFEST_CREATION_FAILED: ${manifestResult.code}`
  );
}

const trustedReference =
  createTrustedArtifactReference(
    job.jobId,
    "Vulnerable.sol"
  );

if (!trustedReference.allowed) {
  throw new Error(
    `TRUSTED_ARTIFACT_FAILED: ${trustedReference.code}`
  );
}

const observed = await observeRecovery(mockFetch, {
  previousState: "DOWN",
  baseUrl: "https://mock.aacp.local",
  timeoutMs: 1000
});

test(
  "recovery detected",
  observed.recovered === true
);

test(
  "healthy state detected",
  observed.state === "HEALTHY"
);

test(
  "recovered job captured",
  observed.jobs.length === 1
);

test(
  "job identity preserved",
  observed.jobs[0]?.jobId === "recovered-security-001"
);

const snapshotFile = writeSnapshot(
  observed,
  tempDir
);

test(
  "observer snapshot written",
  fs.existsSync(snapshotFile)
);

const qualification = writeQualification(
  observed.jobs,
  tempDir
);

test(
  "qualification snapshot written",
  fs.existsSync(qualification.file)
);

test(
  "security job qualifies",
  qualification.output.jobs[0]?.qualification === "STRONG_MATCH"
);

test(
  "qualification is READ_ONLY",
  qualification.output.mode === "READ_ONLY"
);

test(
  "all requests were GET",
  methods.every(method => method === "GET")
);

test(
  "POST never performed",
  qualification.output.safety.postPerformed === false
);

test(
  "wallet never used",
  qualification.output.safety.walletUsed === false
);

test(
  "signing never performed",
  qualification.output.safety.signingPerformed === false
);

test(
  "broadcast never performed",
  qualification.output.safety.broadcastPerformed === false
);

test(
  "submission never performed",
  qualification.output.safety.submissionPerformed === false
);

console.log("");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
console.log("========================================");

if (failed > 0) {
  process.exit(1);
}

console.log("");
console.log("AACP RECOVERY → QUALIFICATION PASSED");
console.log("");
console.log("Real network : NONE");
console.log("POST         : NOT PERFORMED");
console.log("Wallet       : NOT USED");
console.log("Signing      : NOT PERFORMED");
console.log("Broadcast    : NOT PERFORMED");
console.log("Submission   : NOT PERFORMED");
