import fs from "fs";
import { execFileSync } from "child_process";
import path from "path";

const jobFile = process.argv[2];
const sourceFile = process.argv[3];

if (!jobFile || !sourceFile) {
  console.error(
    "Usage: pnpm run deliver <job.json> <SolidityFile>"
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

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Deliverable Engine v1.0.0");
console.log("========================================");
console.log("");

console.log(`Job     : ${job.jobId ?? "-"}`);
console.log(`Source  : ${sourceFile}`);
console.log("");

console.log("[1/3] Running security analyzer...");

const raw = execFileSync(
  process.execPath,
  ["src/analyze.mjs", sourceFile],
  { encoding: "utf8" }
);

const analysis = JSON.parse(raw);

console.log(
  `Findings: ${analysis.summary.total}`
);

console.log(
  `Risk    : ${analysis.summary.riskLevel}`
);

console.log(
  `Score   : ${analysis.summary.riskScore}`
);

console.log("");
console.log("[2/3] Building deliverable...");

const base =
  path.basename(sourceFile, path.extname(sourceFile));

const outDir = path.dirname(sourceFile);

const deliverable = {
  deliverable: "TermiX Provider Security Assessment",
  version: "1.0.0",

  job: {
    jobId: job.jobId ?? null,
    strategyType: job.strategyType ?? null,
    title: job.title ?? null
  },

  target: {
    sourceFile,
    bytes: fs.statSync(sourceFile).size,
    lines: fs.readFileSync(sourceFile, "utf8").split("\n").length
  },

  assessment: {
    findings: analysis.findings,
    summary: analysis.summary
  },

  methodology: [
    "Static Solidity source inspection",
    "Pattern-based vulnerability detection",
    "Severity classification",
    "Confidence classification",
    "Risk score calculation"
  ],

  limitations: [
    "Automated heuristic analysis is not a formal security audit.",
    "Findings require manual validation.",
    "No exploit execution was performed.",
    "No transaction was signed or broadcast.",
    "On-chain verification requires a separate RPC inspection."
  ],

  execution: {
    mode: "READ_ONLY",
    walletRequired: false,
    transactionSigned: false,
    transactionBroadcast: false
  }
};

const jsonPath =
  path.join(outDir, `${base}-TERMiX-DELIVERABLE.json`);

const mdPath =
  path.join(outDir, `${base}-TERMiX-DELIVERABLE.md`);

fs.writeFileSync(
  jsonPath,
  JSON.stringify(deliverable, null, 2)
);

const md = `# TermiX Provider Security Deliverable

## Job

- Job ID: \`${job.jobId ?? "-"}\`
- Strategy: \`${job.strategyType ?? "-"}\`
- Title: ${job.title ?? "-"}

## Target

- Source: \`${sourceFile}\`
- Lines: ${deliverable.target.lines}
- Bytes: ${deliverable.target.bytes}

## Assessment

| Metric | Result |
|---|---:|
| Findings | ${analysis.summary.total} |
| Critical | ${analysis.summary.critical} |
| High | ${analysis.summary.high} |
| Medium | ${analysis.summary.medium} |
| Low | ${analysis.summary.low} |
| Risk Score | ${analysis.summary.riskScore} |
| Risk Level | **${analysis.summary.riskLevel}** |

## Findings

${analysis.findings.map((f, i) => `
### ${i + 1}. ${f.title}

- Severity: **${f.severity}**
- Confidence: **${f.confidence}**
- Line: ${f.line ?? "-"}
- Description: ${f.description}
`).join("\n")}

## Methodology

${deliverable.methodology.map(x => `- ${x}`).join("\n")}

## Limitations

${deliverable.limitations.map(x => `- ${x}`).join("\n")}

## Execution Safety

- Mode: **READ_ONLY**
- Wallet required: **No**
- Transaction signed: **No**
- Transaction broadcast: **No**
`;

fs.writeFileSync(mdPath, md);

console.log("[3/3] Deliverables generated.");
console.log("");
console.log(`JSON: ${jsonPath}`);
console.log(`MD  : ${mdPath}`);
console.log("");
console.log("DELIVERABLE COMPLETE");
