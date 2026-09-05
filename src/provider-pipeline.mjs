import fs from "fs";
import { execFileSync } from "child_process";
import path from "path";

const jobFile = process.argv[2];
const sourceFile = process.argv[3];

if (!jobFile || !sourceFile) {
  console.error(
    "Usage: pnpm run pipeline <job.json> <SolidityFile>"
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

const job = JSON.parse(fs.readFileSync(jobFile, "utf8"));

const jobId = job.jobId ?? "unknown-job";
const rootDir = path.resolve(".");
const outputDir = path.join(
  rootDir,
  "provider-output",
  jobId
);

fs.mkdirSync(outputDir, { recursive: true });

function run(script, args) {
  return execFileSync(
    process.execPath,
    [script, ...args],
    { encoding: "utf8" }
  );
}

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Provider Pipeline v1.1.0");
console.log("========================================");
console.log("");

console.log(`Job    : ${jobId}`);
console.log(`Source : ${sourceFile}`);
console.log("");

/* ---------------------------------------
   1. PROVIDER EVALUATION
--------------------------------------- */

console.log("[1/4] Unified provider evaluation...");

const evaluationRaw = run(
  "src/provider-evaluate.mjs",
  [jobFile]
);

const evaluation = JSON.parse(evaluationRaw);

console.log(
  `Match   : ${evaluation.matching.score}/100`
);

console.log(
  `Budget  : ${evaluation.pricing.budgetStatus}`
);

console.log(
  `Decision: ${evaluation.decision.status}`
);

/* ---------------------------------------
   2. SECURITY ANALYSIS
--------------------------------------- */

console.log("[2/4] Smart-contract security analysis...");

const analysisRaw = run(
  "src/analyze.mjs",
  [sourceFile]
);

const analysis = JSON.parse(analysisRaw);

console.log(
  `Findings: ${analysis.summary.total}`
);

console.log(
  `Risk    : ${analysis.summary.riskLevel}`
);

console.log(
  `Score   : ${analysis.summary.riskScore}`
);

/* ---------------------------------------
   3. DELIVERABLE
--------------------------------------- */

console.log("");
console.log("[3/4] Building security deliverable...");

run(
  "src/provider-deliverable.mjs",
  [jobFile, sourceFile]
);

const base =
  path.basename(
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

const deliverableJson =
  JSON.parse(
    fs.readFileSync(
      deliverableJsonPath,
      "utf8"
    )
  );

/* ---------------------------------------
   4. PROVIDER PACKAGE
--------------------------------------- */

console.log("[4/4] Building provider package...");

const summary = {
  package: "TermiX Provider Package",
  version: "1.2.0",

  job: {
    jobId,
    status: job.status ?? null,
    strategyType: job.strategyType ?? null,
    title: job.title ?? null,
    budget: job.budget ?? null
  },

  evaluation,

  security: {
    findings: analysis.summary.total,
    critical: analysis.summary.critical,
    high: analysis.summary.high,
    medium: analysis.summary.medium,
    low: analysis.summary.low,
    riskScore: analysis.summary.riskScore,
    riskLevel: analysis.summary.riskLevel
  },

  deliverable: {
    json: deliverableJsonPath,
    markdown: deliverableMdPath
  },

  execution: {
    mode: "READ_ONLY",
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false
  }
};

const summaryPath =
  path.join(
    outputDir,
    "provider-summary.json"
  );

const packagePath =
  path.join(
    outputDir,
    "provider-package.json"
  );

fs.writeFileSync(
  summaryPath,
  JSON.stringify(summary, null, 2)
);

fs.writeFileSync(
  packagePath,
  JSON.stringify(
    {
      job,
      evaluation,
      security: analysis,
      deliverable: deliverableJson,
      execution: summary.execution
    },
    null,
    2
  )
);

const markdown = `# TermiX Provider Package

## Job

- Job ID: \`${jobId}\`
- Status: ${job.status ?? "-"}
- Strategy: ${job.strategyType ?? "-"}
- Title: ${job.title ?? "-"}
- Budget: ${job.budget ?? "-"}

## Provider Evaluation

- Match score: ${evaluation.matching.score}/100
- Recommendation: ${evaluation.matching.recommendation}
- Complexity: ${evaluation.workload.complexity}
- Estimated hours: ${evaluation.workload.estimatedHours}
- Estimated value: ${evaluation.pricing.estimatedValueUSDC} USDC
- Budget: ${evaluation.pricing.budgetUSDC} USDC
- Coverage: ${evaluation.pricing.budgetCoveragePercent}%
- Budget status: **${evaluation.pricing.budgetStatus}**
- Recommended price: ${evaluation.pricing.recommendedPriceUSDC} USDC
- Decision: **${evaluation.decision.status}**

## Security Assessment

| Metric | Result |
|---|---:|
| Findings | ${analysis.summary.total} |
| Critical | ${analysis.summary.critical} |
| High | ${analysis.summary.high} |
| Medium | ${analysis.summary.medium} |
| Low | ${analysis.summary.low} |
| Risk Score | ${analysis.summary.riskScore} |
| Risk Level | **${analysis.summary.riskLevel}** |

## Deliverables

- Security JSON: \`${deliverableJsonPath}\`
- Security Markdown: \`${deliverableMdPath}\`
- Provider Summary: \`provider-summary.json\`
- Provider Package: \`provider-package.json\`

## Execution Safety

- Mode: **READ_ONLY**
- Wallet required: **No**
- Offer submitted: **No**
- Transaction signed: **No**
- Transaction broadcast: **No**
`;

const markdownPath =
  path.join(
    outputDir,
    "provider-summary.md"
  );

fs.writeFileSync(
  markdownPath,
  markdown
);

console.log("");
console.log("========================================");
console.log(" PROVIDER PIPELINE COMPLETE");
console.log("========================================");
console.log("");
console.log(`Output : ${outputDir}`);
console.log("");
console.log("Execution: READ_ONLY");
console.log("Offer submitted: NO");
console.log("Transaction signed: NO");
console.log("Transaction broadcast: NO");
