import fs from "fs";
import path from "path";
import { execFileSync } from "child_process";

const intakeFile =
  process.argv[2] || "provider-output/aacp-intake.json";

const sourceFile =
  process.argv[3] || null;

const simulation =
  process.env.PROVIDER_DAEMON_SIMULATION === "1";

if (!sourceFile && !simulation) {
  console.error("SOURCE_REQUIRED");
  console.error(
    "Production mode requires an explicit Solidity source/artifact."
  );
  console.error(
    "Sample fallback is disabled."
  );
  process.exit(2);
}

if (!sourceFile && simulation) {
  console.error("SIMULATION_SOURCE_REQUIRED");
  console.error(
    "Simulation mode also requires an explicit source file."
  );
  process.exit(2);
}

if (!fs.existsSync(intakeFile)) {
  console.error(`Intake file not found: ${intakeFile}`);
  process.exit(1);
}

if (!fs.existsSync(sourceFile)) {
  console.error(`Source file not found: ${sourceFile}`);
  process.exit(1);
}

const intake = JSON.parse(
  fs.readFileSync(intakeFile, "utf8")
);

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Auto Processor v1.6.0");
console.log(" READ ONLY");
console.log("========================================");
console.log("");

console.log(
  `Backend available : ${intake.summary?.backendAvailable ?? false}`
);

console.log(
  `Jobs available    : ${intake.jobs?.length ?? 0}`
);

if (
  intake.summary?.backendAvailable === false &&
  (!intake.jobs || intake.jobs.length === 0)
) {
  console.log("");
  console.log(
    "AACP backend unavailable."
  );
  console.log(
    "No jobs will be fabricated or assumed."
  );
  console.log("");
  console.log("AUTO PROCESSOR STOPPED SAFELY");
  process.exit(0);
}

const jobs = intake.jobs || [];

const results = [];

for (const [index, job] of jobs.entries()) {
  const jobId =
    job.jobId ??
    job.id ??
    `job-${index + 1}`;

  console.log("");
  console.log(
    `[${index + 1}/${jobs.length}] Processing ${jobId}`
  );

  const tempFile = path.join(
    "/tmp",
    `termix-job-${jobId}.json`
  );

  fs.writeFileSync(
    tempFile,
    JSON.stringify(job, null, 2)
  );

  try {
    const raw = execFileSync(
      process.execPath,
      [
        "src/job-processor.mjs",
        tempFile,
        sourceFile
      ],
      {
        encoding: "utf8"
      }
    );

    const outputLine =
      raw
        .split("\n")
        .find(line =>
          line.includes("Output   :")
        );

    const output =
      outputLine
        ? outputLine.split("Output   :")[1].trim()
        : null;

    results.push({
      jobId,
      status: "PROCESSED",
      output
    });

    console.log("  Status : PROCESSED");

  } catch (error) {
    results.push({
      jobId,
      status: "FAILED",
      error: error.message
    });

    console.log("  Status : FAILED");
  }

  fs.rmSync(
    tempFile,
    { force: true }
  );
}

const result = {
  processor: "TermiX Auto Processor",
  version: "1.5.0",

  intake: {
    backendAvailable:
      intake.summary?.backendAvailable ?? false,
    jobsReceived: jobs.length
  },

  results,

  execution: {
    mode: "READ_ONLY",
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false
  }
};

const outputPath =
  "provider-output/auto-processor-result.json";

fs.writeFileSync(
  outputPath,
  JSON.stringify(result, null, 2)
);

console.log("");
console.log("========================================");
console.log(" AUTO PROCESSOR COMPLETE");
console.log("========================================");
console.log("");
console.log(
  `Processed : ${results.filter(x => x.status === "PROCESSED").length}`
);
console.log(
  `Failed    : ${results.filter(x => x.status === "FAILED").length}`
);
console.log(
  `Output    : ${outputPath}`
);
console.log("");
console.log("Wallet       : NOT USED");
console.log("Signing      : NOT USED");
console.log("Submission   : NOT USED");
