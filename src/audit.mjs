import fs from "fs";
import { execFileSync } from "child_process";

const input = process.argv[2];

if (!input) {
  console.error("Usage: pnpm audit <SolidityFile>");
  process.exit(1);
}

if (!fs.existsSync(input)) {
  console.error(`File not found: ${input}`);
  process.exit(1);
}

console.log("========================================");
console.log(" TermiX Provider Agent - Smart Contract");
console.log(" Security Audit");
console.log("========================================");
console.log("");
console.log(`Target: ${input}`);
console.log("");

console.log("[1/2] Running static security analyzer...");

const analysisOutput = execFileSync(
  process.execPath,
  ["src/analyze.mjs", input],
  { encoding: "utf8" }
);

const analysis = JSON.parse(analysisOutput);

console.log(
  `Findings: ${analysis.summary.total} ` +
  `(${analysis.summary.critical} critical, ` +
  `${analysis.summary.high} high, ` +
  `${analysis.summary.medium} medium, ` +
  `${analysis.summary.low} low)`
);

console.log("");
console.log("[2/2] Generating deliverables...");

execFileSync(
  process.execPath,
  ["src/report.mjs", input],
  { stdio: "inherit" }
);

console.log("");
console.log("========================================");
console.log(" AUDIT COMPLETE");
console.log("========================================");
