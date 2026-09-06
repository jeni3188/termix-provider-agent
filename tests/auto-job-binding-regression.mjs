import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const root = process.cwd();

const jobId = "auto-binding-regression-001";
const stagingRoot =
  path.join(
    root,
    "provider-output",
    "source-staging",
    jobId
  );

const source =
  path.join(
    stagingRoot,
    "source.sol"
  );

const intakeFile =
  path.join(
    "/tmp",
    "auto-job-binding-intake.json"
  );

const jobFile =
  path.join(
    "/tmp",
    "auto-job-binding-job.json"
  );

const sourceFixture =
  path.join(
    "/tmp",
    "auto-job-binding-source.sol"
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

const tamperedJob = {
  ...job,
  budget: "900000000"
};

fs.mkdirSync(path.dirname(sourceFixture), {
  recursive: true
});

fs.writeFileSync(
  sourceFixture,
  `pragma solidity ^0.8.20;

contract Test {
    function ping() external pure returns (uint256) {
        return 1;
    }
}
`
);

fs.writeFileSync(
  jobFile,
  JSON.stringify(job, null, 2)
);

function run(args) {
  try {
    return execFileSync(
      process.execPath,
      args,
      {
        cwd: root,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"]
      }
    );
  } catch (error) {
    return [
      error.stdout || "",
      error.stderr || ""
    ].join("\n");
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(`FAIL: ${message}`);
  }

  console.log(`PASS: ${message}`);
}

/*
 * Stage artifact and create immutable Job binding.
 */
const intakeOutput = run([
  "src/artifact-intake.mjs",
  jobId,
  sourceFixture,
  "source.sol",
  jobFile
]);

const intake = JSON.parse(intakeOutput);

assert(
  intake.allowed === true,
  "valid Job + artifact intake succeeds"
);

assert(
  intake.code === "INTAKE_READY",
  "intake returns INTAKE_READY"
);

const intakeJson = {
  intake: "TermiX AACP Job Intake",
  version: "test",
  backend: "test",
  mode: "READ_ONLY",
  jobs: [job],
  summary: {
    uniqueJobs: 1,
    endpointErrors: 0,
    backendAvailable: true
  },
  safety: {
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false
  }
};

fs.writeFileSync(
  intakeFile,
  JSON.stringify(intakeJson, null, 2)
);

/*
 * Valid Job A must pass the binding gate.
 */
const validOutput = run([
  "src/auto-processor.mjs",
  intakeFile,
  "source.sol"
]);

assert(
  validOutput.includes("Status : PROCESSED"),
  "matching Job metadata passes processing gate"
);

/*
 * Replace the intake job with tampered Job B.
 */
const tamperedIntake = {
  ...intakeJson,
  jobs: [tamperedJob]
};

fs.writeFileSync(
  intakeFile,
  JSON.stringify(tamperedIntake, null, 2)
);

/*
 * The auto-processor reports per-job BLOCKED results.
 * It does not necessarily exit non-zero for a blocked job,
 * so the regression must inspect the processor result itself.
 */
run([
  "src/auto-processor.mjs",
  intakeFile,
  "source.sol"
]);

const processorResultPath =
  path.join(root, "provider-output", "auto-processor-result.json");

assert(
  fs.existsSync(processorResultPath),
  "tampered Job produces processor result"
);

const processorResult = JSON.parse(
  fs.readFileSync(processorResultPath, "utf8")
);

const tamperedResult =
  processorResult.results?.find(
    (result) =>
      result.jobId === "auto-binding-regression-001"
  );

assert(
  tamperedResult?.status === "BLOCKED",
  "tampered Job is rejected by binding gate"
);

assert(
  tamperedResult?.code === "JOB_BINDING_MISMATCH",
  "tampered Job rejection code is JOB_BINDING_MISMATCH"
);

assert(
  processorResult.execution?.walletRequired === false,
  "tampered Job does not require wallet"
);

assert(
  processorResult.execution?.offerSubmitted === false,
  "tampered Job does not submit offer"
);

/*
 * Cleanup.
 */
fs.rmSync(
  stagingRoot,
  {
    recursive: true,
    force: true
  }
);

fs.rmSync(
  intakeFile,
  { force: true }
);

fs.rmSync(
  jobFile,
  { force: true }
);

fs.rmSync(
  sourceFixture,
  { force: true }
);

console.log("");
console.log("========================================");
console.log("AUTO JOB BINDING REGRESSION PASSED");
console.log("========================================");
console.log("Job identity : VERIFIED");
console.log("Artifact     : VERIFIED");
console.log("Binding      : ENFORCED");
console.log("Tampering    : BLOCKED");
console.log("Wallet       : NOT USED");
console.log("Signing      : NOT USED");
console.log("Broadcast    : NOT USED");
