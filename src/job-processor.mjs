import fs from "fs";
import path from "path";
import { execFileSync } from "child_process";

const jobFile = process.argv[2];
const sourceFile = process.argv[3];

if (!jobFile || !sourceFile) {
  console.error(
    "Usage: pnpm run process <job.json> <SolidityFile>"
  );
  process.exit(1);
}

if (!fs.existsSync(jobFile)) {
  console.error(`Job file not found: ${jobFile}`);
  process.exit(1);
}

if (!fs.existsSync(sourceFile)) {
  console.error(`Source file not found: ${sourceFile}`);
  process.exit(1);
}

const job = JSON.parse(
  fs.readFileSync(jobFile, "utf8")
);

const jobId = job.jobId ?? "unknown-job";

const outputDir = path.resolve(
  "provider-output",
  jobId
);

fs.mkdirSync(outputDir, {
  recursive: true
});

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Job Processor v1.4.0");
console.log(" READ ONLY");
console.log("========================================");
console.log("");

console.log(`Job    : ${jobId}`);
console.log(`Source : ${sourceFile}`);
console.log("");

/* ---------------------------------------
   1. EVALUATION
--------------------------------------- */

console.log("[1/4] Evaluating provider capability...");

const evaluationRaw = execFileSync(
  process.execPath,
  ["src/provider-evaluate.mjs", jobFile],
  { encoding: "utf8" }
);

const evaluation = JSON.parse(
  evaluationRaw
);

console.log(
  `Match    : ${evaluation.matching.score}/100`
);

console.log(
  `Budget   : ${evaluation.pricing.budgetStatus}`
);

console.log(
  `Decision : ${evaluation.decision.status}`
);

/* ---------------------------------------
   2. DECISION GATE
--------------------------------------- */

console.log("");
console.log("[2/4] Applying provider decision gate...");

const decision =
  evaluation.decision.status;

let executionPath;

if (decision === "REJECT") {
  executionPath = "REJECT";
} else if (decision === "MANUAL_REVIEW") {
  executionPath = "MANUAL_REVIEW";
} else if (
  decision === "PROCEED_TO_OFFER_REVIEW"
) {
  executionPath = "OFFER_REVIEW";
} else {
  executionPath = "MANUAL_REVIEW";
}

console.log(
  `Execution path: ${executionPath}`
);

/* ---------------------------------------
   3. SECURITY ANALYSIS
--------------------------------------- */

let analysis = null;
let deliverable = null;

if (executionPath !== "REJECT") {
  console.log("");
  console.log(
    "[3/4] Running security assessment..."
  );

  const analysisRaw = execFileSync(
    process.execPath,
    ["src/analyze.mjs", sourceFile],
    { encoding: "utf8" }
  );

  analysis = JSON.parse(
    analysisRaw
  );

  console.log(
    `Findings : ${analysis.summary.total}`
  );

  console.log(
    `Risk     : ${analysis.summary.riskLevel}`
  );

  console.log(
    `Score    : ${analysis.summary.riskScore}`
  );

  const base = path.basename(
    sourceFile,
    path.extname(sourceFile)
  );

  const sourceDir = path.dirname(
    path.resolve(sourceFile)
  );

  const deliverableJsonPath =
    path.join(
      sourceDir,
      `${base}-TERMiX-DELIVERABLE.json`
    );

  const deliverableMdPath =
    path.join(
      sourceDir,
      `${base}-TERMiX-DELIVERABLE.md`
    );

  execFileSync(
    process.execPath,
    [
      "src/provider-deliverable.mjs",
      jobFile,
      sourceFile
    ],
    { stdio: "ignore" }
  );

  deliverable = {
    json: deliverableJsonPath,
    markdown: deliverableMdPath
  };
} else {
  console.log("");
  console.log(
    "[3/4] Security assessment skipped."
  );
}

/* ---------------------------------------
   4. PACKAGE
--------------------------------------- */

console.log("");
console.log("[4/4] Building processor result...");

const result = {
  processor: "TermiX Job Processor",
  version: "1.4.0",

  job: {
    jobId,
    status: job.status ?? null,
    strategyType: job.strategyType ?? null,
    title: job.title ?? null,
    budgetUSDC:
      Number(job.budget ?? 0) / 1_000_000
  },

  evaluation,

  execution: {
    path: executionPath,
    securityAssessment:
      analysis !== null,
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false
  },

  security: analysis
    ? {
        findings: analysis.summary.total,
        critical: analysis.summary.critical,
        high: analysis.summary.high,
        medium: analysis.summary.medium,
        low: analysis.summary.low,
        riskScore: analysis.summary.riskScore,
        riskLevel: analysis.summary.riskLevel
      }
    : null,

  deliverable,

  safety: {
    mode: "READ_ONLY",
    noAutomaticSubmission: true
  }
};

const outputPath = path.join(
  outputDir,
  "processor-result.json"
);

fs.writeFileSync(
  outputPath,
  JSON.stringify(result, null, 2)
);

console.log("");
console.log("========================================");
console.log(" JOB PROCESSOR COMPLETE");
console.log("========================================");
console.log("");

console.log(
  `Decision : ${decision}`
);

console.log(
  `Path     : ${executionPath}`
);

console.log(
  `Output   : ${outputPath}`
);

console.log("");
console.log("Wallet: NOT USED");
console.log("Signing: NOT USED");
console.log("Submission: NOT USED");
