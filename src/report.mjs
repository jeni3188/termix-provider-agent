import fs from "fs";
import { execFileSync } from "child_process";

const input = process.argv[2];

if (!input) {
  console.error("Usage: pnpm report <SolidityFile>");
  process.exit(1);
}

if (!fs.existsSync(input)) {
  console.error(`File not found: ${input}`);
  process.exit(1);
}

let analysis;

try {
  const output = execFileSync(
    process.execPath,
    ["src/analyze.mjs", input],
    { encoding: "utf8" }
  );

  analysis = JSON.parse(output);
} catch (err) {
  console.error("Analyzer failed.");
  console.error(err.message);
  process.exit(1);
}

const { findings, summary } = analysis;

let md = "";

md += "# Smart Contract Security Review\n\n";

md += `**Contract:** \`${input}\`  \n`;
md += `**Analyzer:** TermiX Provider Agent v${analysis.version}  \n`;
md += `**Lines:** ${analysis.lines}  \n`;
md += `**Bytes:** ${analysis.bytes}  \n`;
md += `**Findings:** ${summary.total}\n\n`;

md += "## Executive Summary\n\n";

if (summary.critical > 0) {
  md += "🚨 **Critical findings detected. Immediate security review is recommended.**\n\n";
} else if (summary.high > 0) {
  md += "⚠️ **High-severity findings detected. Manual security review is recommended before deployment.**\n\n";
} else if (summary.medium > 0) {
  md += "🟠 **Medium-severity findings detected. Further review is recommended.**\n\n";
} else {
  md += "✅ **No findings detected by the automated heuristic scanner. Manual review is still required.**\n\n";
}

md += "### Severity Summary\n\n";
md += "| Severity | Count |\n";
md += "|---|---:|\n";
md += `| Critical | ${summary.critical} |\n`;
md += `| High | ${summary.high} |\n`;
md += `| Medium | ${summary.medium} |\n`;
md += `| Low | ${summary.low} |\n\n`;

md += "## Findings\n\n";

if (!findings.length) {
  md += "No findings detected by the automated scanner.\n\n";
}

for (const finding of findings) {
  md += `### [${finding.severity}] ${finding.title}\n\n`;
  md += `**ID:** \`${finding.id}\`  \\n`;
  md += `**Confidence:** ${finding.confidence || "UNKNOWN"}\\n\\n`;
  md += `${finding.message}\\n\\n`;

  if (finding.evidence?.length) {
    md += "**Evidence:**\n\n";

    for (const item of finding.evidence) {
      md += `- **Line ${item.line}:** \`${item.text.replace(/`/g, "\\`")}\`\n`;
    }

    md += "\n";
  }

  md += "---\n\n";
}

md += "## Methodology\n\n";
md += "This report was generated using static heuristic pattern analysis. ";
md += "Automated findings should be manually validated. ";
md += "This scanner does not replace manual audit, fuzzing, symbolic execution, formal verification, or economic/security analysis.\n";

const base = input.replace(/\.[^.]+$/, "");

const markdownOutput = `${base}-AUDIT-REPORT.md`;
const jsonOutput = `${base}-AUDIT-REPORT.json`;

fs.writeFileSync(markdownOutput, md);
fs.writeFileSync(
  jsonOutput,
  JSON.stringify(analysis, null, 2)
);

console.log(`Markdown report: ${markdownOutput}`);
console.log(`JSON report:     ${jsonOutput}`);
console.log(`Findings:        ${summary.total}`);
console.log(
  `Severity:        ${summary.critical} critical, ${summary.high} high, ${summary.medium} medium, ${summary.low} low`
);
