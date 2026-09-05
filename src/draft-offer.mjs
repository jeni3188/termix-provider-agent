import fs from "fs";

const input = process.argv[2];

if (!input) {
  console.error("Usage: pnpm run offer <job.json>");
  process.exit(1);
}

if (!fs.existsSync(input)) {
  console.error(`File not found: ${input}`);
  process.exit(1);
}

const job = JSON.parse(fs.readFileSync(input, "utf8"));

const text = [
  job.title,
  job.description,
  job.strategyType
]
  .filter(Boolean)
  .join(" ")
  .toLowerCase();

const checks = [
  ["Solidity", ["solidity", "smart contract"], 20],
  ["Security audit", ["security", "audit"], 20],
  ["Reentrancy", ["reentrancy"], 10],
  ["Access control", ["access control", "authorization"], 10],
  ["EVM/on-chain", ["evm", "on-chain", "bytecode"], 10],
  ["Static analysis", ["tx.origin", "delegatecall", "timestamp", "low-level call"], 10]
];

let matchScore = 0;
const capabilities = [];

for (const [name, keywords, weight] of checks) {
  const hits = keywords.filter(k => text.includes(k));

  if (hits.length) {
    matchScore += weight;
    capabilities.push({
      name,
      matchedKeywords: hits
    });
  }
}

const budgetRaw = Number(job.budget);
const budgetUSDC = Number.isFinite(budgetRaw)
  ? budgetRaw / 1e6
  : null;

let complexity = "LOW";

if (text.includes("audit") || text.includes("security")) {
  complexity = "MEDIUM";
}

if (
  text.includes("reentrancy") &&
  text.includes("access control") &&
  text.includes("delegatecall")
) {
  complexity = "HIGH";
}

const estimatedHours = {
  LOW: 2,
  MEDIUM: 5,
  HIGH: 10
}[complexity];

const confidence =
  matchScore >= 80 ? "HIGH" :
  matchScore >= 50 ? "MEDIUM" :
  "LOW";

const deliverables = [
  "Automated Solidity security scan",
  "Finding list with severity and confidence",
  "On-chain inspection when contract address/RPC are available",
  "Unified security assessment",
  "Markdown and JSON audit reports"
];

const result = {
  agent: "TermiX Provider Agent",
  version: "0.8.0",

  job: {
    jobId: job.jobId ?? null,
    strategyType: job.strategyType ?? null,
    title: job.title ?? null,
    budgetUSDC,
    status: job.status ?? null
  },

  assessment: {
    matchScore,
    confidence,
    complexity,
    estimatedHours,
    matchedCapabilities: capabilities
  },

  draftOffer: {
    priceUSDC: budgetUSDC,
    proposal:
      "I can perform an automated EVM/Solidity security assessment " +
      "covering static vulnerability detection, access control, " +
      "reentrancy indicators, dangerous calls, and on-chain inspection " +
      "where contract/RPC information is available.",
    deliverables
  },

  execution: {
    mode: "DRAFT_ONLY",
    offerSubmitted: false,
    transactionSigned: false,
    walletRequired: false
  }
};

console.log(JSON.stringify(result, null, 2));
