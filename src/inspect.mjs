import fs from "fs";
import { execFileSync } from "child_process";
import { ethers } from "ethers";

const solidityFile = process.argv[2];
const address = process.argv[3];
const rpcUrl = process.argv[4];

if (!solidityFile || !address || !rpcUrl) {
  console.error(
    "Usage: pnpm run inspect <SolidityFile> <ContractAddress> <RPC_URL>"
  );
  process.exit(1);
}

if (!fs.existsSync(solidityFile)) {
  console.error(`File not found: ${solidityFile}`);
  process.exit(1);
}

if (!ethers.isAddress(address)) {
  console.error(`Invalid EVM address: ${address}`);
  process.exit(1);
}

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Unified Security Inspector");
console.log("========================================\n");

console.log(`Source   : ${solidityFile}`);
console.log(`Contract : ${address}`);
console.log(`RPC      : ${rpcUrl}\n`);

/* =========================================================
   STATIC ANALYSIS
   ========================================================= */

console.log("[1/3] Running static security analysis...");

let staticAnalysis;

try {
  const output = execFileSync(
    process.execPath,
    ["src/analyze.mjs", solidityFile],
    { encoding: "utf8" }
  );

  staticAnalysis = JSON.parse(output);
} catch (error) {
  console.error("Static analyzer failed.");
  console.error(error.message);
  process.exit(1);
}

console.log(
  `Findings: ${staticAnalysis.summary.total} ` +
  `(${staticAnalysis.summary.critical} critical, ` +
  `${staticAnalysis.summary.high} high, ` +
  `${staticAnalysis.summary.medium} medium, ` +
  `${staticAnalysis.summary.low} low)`
);

/* =========================================================
   ON-CHAIN ANALYSIS
   ========================================================= */

console.log("\n[2/3] Running on-chain analysis...");

let provider;
let network;
let blockNumber;
let code;
let balance;

try {
  provider = new ethers.JsonRpcProvider(rpcUrl);

  network = await provider.getNetwork();
  blockNumber = await provider.getBlockNumber();
  code = await provider.getCode(address);
  balance = await provider.getBalance(address);
} catch (error) {
  console.error("RPC analysis failed.");
  console.error(error.shortMessage || error.message);
  process.exit(1);
}

const isContract = code !== "0x";
const runtimeBytecodeBytes = Math.max(0, (code.length - 2) / 2);

const onChainRisks = [];

if (!isContract) {
  onChainRisks.push("ADDRESS_HAS_NO_RUNTIME_CODE");
}

if (isContract && runtimeBytecodeBytes > 24000) {
  onChainRisks.push("LARGE_RUNTIME_BYTECODE");
}

console.log(`Chain ID: ${network.chainId}`);
console.log(`Block: ${blockNumber}`);
console.log(`Contract: ${isContract ? "YES" : "NO"}`);
console.log(`Runtime bytecode: ${runtimeBytecodeBytes} bytes`);
console.log(`Native balance: ${ethers.formatEther(balance)}`);

if (onChainRisks.length) {
  console.log("On-chain indicators:");

  for (const risk of onChainRisks) {
    console.log(`- ${risk}`);
  }
}

/* =========================================================
   UNIFIED RISK
   ========================================================= */

console.log("\n[3/3] Calculating unified risk assessment...");

const staticScore = staticAnalysis.summary.riskScore;

let onChainScore = 0;

if (onChainRisks.includes("ADDRESS_HAS_NO_RUNTIME_CODE")) {
  onChainScore += 5;
}

if (onChainRisks.includes("LARGE_RUNTIME_BYTECODE")) {
  onChainScore += 3;
}

const unifiedScore = staticScore + onChainScore;

let unifiedRisk = "LOW";

if (unifiedScore >= 30) {
  unifiedRisk = "CRITICAL";
} else if (unifiedScore >= 15) {
  unifiedRisk = "HIGH";
} else if (unifiedScore >= 5) {
  unifiedRisk = "MEDIUM";
}

const confidenceCounts = {
  HIGH: 0,
  MEDIUM: 0,
  LOW: 0
};

for (const finding of staticAnalysis.findings) {
  const confidence = finding.confidence || "UNKNOWN";

  if (confidenceCounts[confidence] !== undefined) {
    confidenceCounts[confidence]++;
  }
}

const result = {
  analyzer: "TermiX Provider Agent",
  version: "0.5.0",
  target: {
    sourceFile: solidityFile,
    contractAddress: address,
    rpcUrl
  },
  chain: {
    chainId: network.chainId.toString(),
    blockNumber
  },
  onChain: {
    isContract,
    runtimeBytecodeBytes,
    nativeBalanceWei: balance.toString(),
    nativeBalance: ethers.formatEther(balance),
    risks: onChainRisks
  },
  staticAnalysis: {
    analyzerVersion: staticAnalysis.version,
    findings: staticAnalysis.findings,
    summary: staticAnalysis.summary
  },
  assessment: {
    staticScore,
    onChainScore,
    unifiedScore,
    unifiedRisk,
    confidence: confidenceCounts
  }
};

/* =========================================================
   OUTPUT
   ========================================================= */

const base = solidityFile.replace(/\.[^.]+$/, "");

const jsonOutput = `${base}-UNIFIED-REPORT.json`;
const mdOutput = `${base}-UNIFIED-REPORT.md`;

fs.writeFileSync(jsonOutput, JSON.stringify(result, null, 2));

let md = "";

md += "# Unified Smart Contract Security Inspection\n\n";

md += `**Source:** \`${solidityFile}\`  \n`;
md += `**Contract:** \`${address}\`  \n`;
md += `**Chain ID:** ${network.chainId}  \n`;
md += `**Block:** ${blockNumber}  \n`;
md += `**Analyzer:** TermiX Provider Agent v0.5.0\n\n`;

md += "## Overall Assessment\n\n";

md += `**Risk Score:** ${unifiedScore}  \n`;
md += `**Overall Risk:** ${unifiedRisk}\n\n`;

md += "## On-chain Analysis\n\n";

md += `- Contract detected: **${isContract ? "YES" : "NO"}**\n`;
md += `- Runtime bytecode: **${runtimeBytecodeBytes} bytes**\n`;
md += `- Native balance: **${ethers.formatEther(balance)}**\n\n`;

md += "## Static Analysis\n\n";

md += `- Findings: **${staticAnalysis.summary.total}**\n`;
md += `- Critical: **${staticAnalysis.summary.critical}**\n`;
md += `- High: **${staticAnalysis.summary.high}**\n`;
md += `- Medium: **${staticAnalysis.summary.medium}**\n`;
md += `- Low: **${staticAnalysis.summary.low}**\n`;
md += `- Static risk score: **${staticScore}**\n\n`;

md += "### Confidence\n\n";

md += `- High: ${confidenceCounts.HIGH}\n`;
md += `- Medium: ${confidenceCounts.MEDIUM}\n`;
md += `- Low: ${confidenceCounts.LOW}\n\n`;

md += "## Findings\n\n";

for (const finding of staticAnalysis.findings) {
  md += `### [${finding.severity}] ${finding.title}\n\n`;
  md += `**ID:** \`${finding.id}\`  \n`;
  md += `**Confidence:** ${finding.confidence || "UNKNOWN"}\n\n`;
  md += `${finding.message}\n\n`;

  if (finding.evidence?.length) {
    md += "**Evidence:**\n\n";

    for (const item of finding.evidence) {
      md += `- Line ${item.line}: \`${item.text.replace(/`/g, "\\`")}\`\n`;
    }

    md += "\n";
  }
}

md += "## Methodology\n\n";
md += "This is an automated heuristic inspection. ";
md += "Results require manual validation and do not constitute a formal security audit.\n";

fs.writeFileSync(mdOutput, md);

console.log("\nJSON report:");
console.log(jsonOutput);

console.log("Markdown report:");
console.log(mdOutput);

console.log("\n========================================");
console.log(" UNIFIED INSPECTION COMPLETE");
console.log("========================================");
