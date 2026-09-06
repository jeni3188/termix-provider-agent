import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = process.cwd();
const stagingRoot = path.join(
  root,
  "provider-output/source-staging"
);

const jobId = "intake-regression-001";
const jobRoot = path.join(stagingRoot, jobId);
const source = path.join(
  root,
  "samples/Vulnerable.sol"
);

const jobFile = path.join(
  "/tmp",
  "termix-intake-regression-job.json"
);

const job = {
  jobId,
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Smart Contract Security Audit",
  description:
    "Audit an EVM Solidity smart contract.",
  deadline: 1799000000,
  providerId: null
};

fs.writeFileSync(
  jobFile,
  JSON.stringify(job, null, 2)
);

function run(args) {
  return spawnSync(
    process.execPath,
    ["src/artifact-intake.mjs", ...args],
    {
      cwd: root,
      encoding: "utf8"
    }
  );
}

function check(label, condition) {
  console.log(
    `${condition ? "PASS" : "FAIL"}: ${label}`
  );

  return condition;
}

let passed = 0;
let failed = 0;

function test(label, condition) {
  if (check(label, condition)) {
    passed++;
  } else {
    failed++;
  }
}

console.log("========================================");
console.log(" TERMIX ARTIFACT INTAKE REGRESSION");
console.log(" READ ONLY / NO NETWORK");
console.log("========================================");

fs.rmSync(jobRoot, {
  recursive: true,
  force: true
});

/*
 * 1. Valid intake
 */
let result =
  run([
    jobId,
    source,
    "",
    jobFile
  ]);

test(
  "valid local source is accepted",
  result.status === 0
);

test(
  "valid intake returns INTAKE_READY",
  result.stdout.includes(
    '"code": "INTAKE_READY"'
  )
);

test(
  "staged artifact exists",
  fs.existsSync(
    path.join(
      jobRoot,
      "Vulnerable.sol"
    )
  )
);

test(
  "manifest exists",
  fs.existsSync(
    path.join(
      jobRoot,
      "manifest.json"
    )
  )
);

/*
 * 2. Manifest verification
 */
const verify =
  spawnSync(
    process.execPath,
    [
      "src/artifact-manifest.mjs",
      "verify",
      jobId
    ],
    {
      cwd: root,
      encoding: "utf8"
    }
  );

test(
  "generated manifest verifies",
  verify.status === 0
);

test(
  "manifest verification returns MANIFEST_VALID",
  verify.stdout.includes(
    '"code": "MANIFEST_VALID"'
  )
);

/*
 * 3. Missing source
 */
const missing =
  run([
    jobId,
    "samples/does-not-exist.sol",
    "",
    jobFile
  ]);

test(
  "missing source is rejected",
  missing.status !== 0 &&
  missing.stdout.includes(
    '"code": "SOURCE_ARTIFACT_REQUIRED"'
  )
);

/*
 * 4. Invalid extension
 */
const invalidPath =
  path.join(
    "/tmp",
    "termix-intake-invalid.exe"
  );

fs.writeFileSync(
  invalidPath,
  "invalid"
);

const invalidExtension =
  run([
    jobId,
    invalidPath,
    "",
    jobFile
  ]);

test(
  "invalid extension is rejected",
  invalidExtension.status !== 0 &&
  invalidExtension.stdout.includes(
    '"code": "SOURCE_REJECTED"'
  )
);

fs.rmSync(
  invalidPath,
  { force: true }
);

/*
 * 5. Traversal through destination filename
 */
const traversal =
  run([
    jobId,
    source,
    "../../escape.sol",
    jobFile
  ]);

test(
  "destination traversal is rejected",
  traversal.status !== 0 &&
  traversal.stdout.includes(
    '"code": "SOURCE_REJECTED"'
  )
);

/*
 * 6. Invalid Job ID
 */
const invalidJob =
  run([
    "../escape",
    source,
    "",
    jobFile
  ]);

test(
  "invalid Job ID is rejected",
  invalidJob.status !== 0 &&
  invalidJob.stdout.includes(
    '"code": "INVALID_JOB_ID"'
  )
);

/*
 * 7. Safety markers
 */
test(
  "network fetch is disabled",
  result.stdout.includes(
    '"networkFetch": false'
  )
);

test(
  "wallet is not used",
  result.stdout.includes(
    '"walletUsed": false'
  )
);

test(
  "signing is disabled",
  result.stdout.includes(
    '"signing": false'
  )
);

test(
  "broadcast is disabled",
  result.stdout.includes(
    '"broadcast": false'
  )
);

test(
  "automatic submission is disabled",
  result.stdout.includes(
    '"automaticSubmission": false'
  )
);

fs.rmSync(
  jobRoot,
  {
    recursive: true,
    force: true
  }
);

fs.rmSync(
  jobFile,
  { force: true }
);

console.log("");
console.log("========================================");
console.log(" ARTIFACT INTAKE SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
console.log("");

if (failed === 0) {
  console.log(
    "ALL ARTIFACT INTAKE TESTS PASSED"
  );
  console.log("");
  console.log(
    "Local source    : ALLOWED"
  );
  console.log(
    "Staging         : VERIFIED"
  );
  console.log(
    "Manifest        : VERIFIED"
  );
  console.log(
    "Path traversal  : BLOCKED"
  );
  console.log(
    "Invalid Job ID  : BLOCKED"
  );
  console.log(
    "Network         : NONE"
  );
  console.log(
    "Wallet          : NOT USED"
  );
  console.log(
    "Signing         : NOT USED"
  );
  console.log(
    "Broadcast       : NOT USED"
  );

  process.exit(0);
}

console.error(
  "ARTIFACT INTAKE TESTS FAILED"
);

process.exit(1);
