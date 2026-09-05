import fs from "fs";

const jobFile = process.argv[2];

if (!jobFile) {
  console.error("Usage: pnpm run evaluate <job.json>");
  process.exit(1);
}

if (!fs.existsSync(jobFile)) {
  console.error(`Job file not found: ${jobFile}`);
  process.exit(1);
}

const job = JSON.parse(fs.readFileSync(jobFile, "utf8"));

const text = [
  job.title ?? "",
  job.description ?? "",
  job.strategyType ?? ""
].join(" ").toLowerCase();

const capabilities = [
  {
    name: "Solidity / Smart Contract",
    keywords: ["solidity", "smart contract"],
    weight: 20
  },
  {
    name: "Security Audit",
    keywords: ["security", "audit"],
    weight: 20
  },
  {
    name: "Reentrancy",
    keywords: ["reentrancy"],
    weight: 15
  },
  {
    name: "Access Control",
    keywords: ["access control"],
    weight: 15
  },
  {
    name: "EVM / On-chain",
    keywords: ["evm", "on-chain"],
    weight: 15
  },
  {
    name: "Static Vulnerability Analysis",
    keywords: [
      "tx.origin",
      "delegatecall",
      "timestamp",
      "dangerous call",
      "static vulnerability"
    ],
    weight: 15
  }
];

const matchedCapabilities = [];
let matchScore = 0;

for (const capability of capabilities) {
  const matched = capability.keywords.some(
    keyword => text.includes(keyword)
  );

  if (matched) {
    matchedCapabilities.push({
      capability: capability.name,
      keywords: capability.keywords.filter(
        keyword => text.includes(keyword)
      ),
      weight: capability.weight
    });

    matchScore += capability.weight;
  }
}

const hasSecurity =
  text.includes("security") ||
  text.includes("audit");

const hasSmartContract =
  text.includes("solidity") ||
  text.includes("smart contract");

const complexity =
  hasSecurity && hasSmartContract
    ? "HIGH"
    : hasSmartContract
      ? "MEDIUM"
      : "LOW";

const estimatedHours = {
  LOW: 2,
  MEDIUM: 5,
  HIGH: 10
}[complexity];

const hourlyRate = {
  LOW: 25,
  MEDIUM: 40,
  HIGH: 50
}[complexity];

const estimatedValueUSDC =
  estimatedHours * hourlyRate;

const budgetUSDC =
  Number(job.budget ?? 0) / 1_000_000;

const budgetCoverage =
  estimatedValueUSDC > 0
    ? (budgetUSDC / estimatedValueUSDC) * 100
    : 0;

let budgetStatus;

if (budgetUSDC < estimatedValueUSDC * 0.75) {
  budgetStatus = "UNDERVALUED";
} else if (budgetUSDC <= estimatedValueUSDC * 1.25) {
  budgetStatus = "FAIR";
} else {
  budgetStatus = "ABOVE_ESTIMATE";
}

const recommendedPriceUSDC =
  Math.min(budgetUSDC, estimatedValueUSDC);

let recommendation;

if (matchScore >= 75) {
  recommendation = "STRONG_MATCH";
} else if (matchScore >= 50) {
  recommendation = "GOOD_MATCH";
} else if (matchScore >= 25) {
  recommendation = "PARTIAL_MATCH";
} else {
  recommendation = "POOR_MATCH";
}

let decisionStatus;
let decisionReason;

if (recommendation === "POOR_MATCH") {
  decisionStatus = "REJECT";
  decisionReason =
    "Provider capabilities do not sufficiently match the job.";
} else if (budgetStatus === "UNDERVALUED") {
  decisionStatus = "MANUAL_REVIEW";
  decisionReason =
    "Job budget is materially below the estimated provider value.";
} else if (matchScore >= 75) {
  decisionStatus = "PROCEED_TO_OFFER_REVIEW";
  decisionReason =
    "Strong capability match and budget is acceptable.";
} else {
  decisionStatus = "MANUAL_REVIEW";
  decisionReason =
    "Capability match is not strong enough for automatic progression.";
}

const result = {
  agent: "TermiX Provider Agent",
  version: "1.0.0",

  job: {
    jobId: job.jobId ?? null,
    status: job.status ?? null,
    strategyType: job.strategyType ?? null,
    title: job.title ?? null,
    budgetUSDC
  },

  matching: {
    score: matchScore,
    recommendation,
    matchedCapabilities
  },

  workload: {
    complexity,
    estimatedHours
  },

  pricing: {
    referenceHourlyRateUSDC: hourlyRate,
    estimatedValueUSDC,
    budgetUSDC,
    budgetCoveragePercent: Number(
      budgetCoverage.toFixed(2)
    ),
    budgetStatus,
    recommendedPriceUSDC
  },

  decision: {
    status: decisionStatus,
    reason: decisionReason
  },

  safety: {
    mode: "READ_ONLY",
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false
  }
};

console.log(
  JSON.stringify(result, null, 2)
);
