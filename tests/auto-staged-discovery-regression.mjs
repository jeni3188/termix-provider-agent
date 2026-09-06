import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const ROOT = process.cwd();
const JOB_FILE = path.join(ROOT, "samples/jobs/security-audit-fair.json");
const SOURCE_FILE = path.join(ROOT, "samples/Vulnerable.sol");
const STAGING_DIR = path.join(
  ROOT,
  "provider-output/source-staging/demo-security-fair-001"
);
const INTAKE_FILE = "/tmp/aacp-intake-staged-regression.json";
const RESULT_FILE = path.join(
  ROOT,
  "provider-output/auto-processor-result.json"
);

let passed = 0;
let failed = 0;

function check(name, condition) {
  if (condition) {
    passed++;
    console.log(`PASS: ${name}`);
  } else {
    failed++;
    console.error(`FAIL: ${name}`);
  }
}

function run(command, args, env = {}) {
  return execFileSync(command, args, {
    cwd: ROOT,
    env: { ...process.env, ...env },
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"]
  });
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

console.log("========================================");
console.log(" AUTO STAGED DISCOVERY REGRESSION");
console.log("========================================");
console.log("");

try {
  const manifestFile = path.join(STAGING_DIR, "manifest.json");
  const stagedSource = path.join(STAGING_DIR, "Vulnerable.sol");

  check("job fixture exists", fs.existsSync(JOB_FILE));
  check("source fixture exists", fs.existsSync(SOURCE_FILE));
  check("staged source exists", fs.existsSync(stagedSource));
  check("manifest exists", fs.existsSync(manifestFile));

  if (
    !fs.existsSync(JOB_FILE) ||
    !fs.existsSync(SOURCE_FILE) ||
    !fs.existsSync(stagedSource) ||
    !fs.existsSync(manifestFile)
  ) {
    throw new Error("Required regression fixtures are missing.");
  }

  const job = readJson(JOB_FILE);

  const intake = {
    intake: "TermiX AACP Job Intake",
    version: "1.3.0",
    backend: "LOCAL_FIXTURE",
    mode: "READ_ONLY",
    endpoints: [],
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
    INTAKE_FILE,
    JSON.stringify(intake, null, 2) + "\n"
  );

  check("local intake fixture created", fs.existsSync(INTAKE_FILE));

  const manifest = readJson(manifestFile);
  const { fingerprintJob } = await import("../src/job-binding.mjs");

  check(
    "job fingerprint matches manifest",
    fingerprintJob(job) === manifest.jobBinding?.fingerprint
  );

  let defaultDenyOutput = "";

  try {
    defaultDenyOutput = run(
      "node",
      ["src/auto-processor.mjs", INTAKE_FILE]
    );
  } catch (error) {
    defaultDenyOutput =
      `${error.stdout ?? ""}${error.stderr ?? ""}`;
  }

  check(
    "staged discovery is disabled by default",
    defaultDenyOutput.includes("SOURCE_REQUIRED")
  );

  let output = "";

  try {
    output = run(
      "node",
      ["src/auto-processor.mjs", INTAKE_FILE],
      { PROVIDER_AUTO_DISCOVER_STAGED: "1" }
    );
  } catch (error) {
    output = `${error.stdout ?? ""}${error.stderr ?? ""}`;
    throw new Error(`Auto processor failed:\n${output}`);
  }

  check(
    "staged manifest discovery succeeded",
    output.includes("STAGED_MANIFEST_ARTIFACT_RESOLVED")
  );

  check(
    "manifest validation succeeded",
    output.includes("MANIFEST          : MANIFEST_VALID") ||
      output.includes("Manifest          : MANIFEST_VALID")
  );

  check(
    "trusted artifact verification succeeded",
    output.includes("TRUSTED_ARTIFACT_VERIFIED")
  );

  check(
    "job was processed",
    output.includes("Status : PROCESSED")
  );

  check(
    "auto processor result exists",
    fs.existsSync(RESULT_FILE)
  );

  if (fs.existsSync(RESULT_FILE)) {
    const result = readJson(RESULT_FILE);
    const item = result.results?.[0];

    check(
      "result contains exactly one job",
      Array.isArray(result.results) &&
        result.results.length === 1
    );

    check(
      "result job ID is correct",
      item?.jobId === "demo-security-fair-001"
    );

    check(
      "result status is PROCESSED",
      item?.status === "PROCESSED"
    );

    check(
      "result execution mode is READ_ONLY",
      result.execution?.mode === "READ_ONLY"
    );

    check(
      "wallet was not used",
      result.execution?.walletRequired === false
    );

    check(
      "offer was not submitted",
      result.execution?.offerSubmitted === false
    );

    check(
      "transaction was not signed",
      result.execution?.transactionSigned === false
    );

    check(
      "transaction was not broadcast",
      result.execution?.transactionBroadcast === false
    );
  }

  check(
    "output does not indicate live submission",
    !output.includes("SUBMIT_AACP_LIVE")
  );

  check(
    "output does not indicate wallet usage",
    !output.includes("Wallet       : USED")
  );

} catch (error) {
  failed++;
  console.error("");
  console.error(`REGRESSION ERROR: ${error.message}`);
}

console.log("");
console.log("========================================");
console.log(" AUTO STAGED DISCOVERY SUMMARY");
console.log("========================================");
console.log(`Passed : ${passed}`);
console.log(`Failed : ${failed}`);
console.log("");

if (failed === 0) {
  console.log("AUTO STAGED DISCOVERY REGRESSION PASSED");
  process.exit(0);
}

console.error("AUTO STAGED DISCOVERY REGRESSION FAILED");
process.exit(1);
