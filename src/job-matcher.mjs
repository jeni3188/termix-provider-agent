import fs from "fs";

const input = process.argv[2];

if (!input) {
  console.error("Usage: pnpm run match <job.json>");
  process.exit(1);
}

if (!fs.existsSync(input)) {
  console.error(`File not found: ${input}`);
  process.exit(1);
}

const job = JSON.parse(
  fs.readFileSync(input, "utf8")
);

const text = [
  job.title,
  job.description,
  job.strategyType
]
  .filter(Boolean)
  .join(" ")
  .toLowerCase();

const capabilities = [
  {
    name: "Solidity security analysis",
    keywords: [
      "solidity",
      "smart contract",
      "security",
      "audit"
    ],
    weight: 30
  },
  {
    name: "Reentrancy analysis",
    keywords: [
      "reentrancy"
    ],
    weight: 15
  },
  {
    name: "Access-control analysis",
    keywords: [
      "access control",
      "authorization",
      "owner",
      "permission"
    ],
    weight: 15
  },
  {
    name: "EVM / on-chain analysis",
    keywords: [
      "evm",
      "on-chain",
      "blockchain",
      "bytecode",
      "contract address"
    ],
    weight: 15
  },
  {
    name: "Static vulnerability detection",
    keywords: [
      "tx.origin",
      "delegatecall",
      "timestamp",
      "dangerous call",
      "low-level call"
    ],
    weight: 15
  }
];

let score = 0;
const matched = [];

for (const capability of capabilities) {
  const hits = capability.keywords.filter(
    keyword => text.includes(keyword)
  );

  if (hits.length > 0) {
    score += capability.weight;
    matched.push({
      capability: capability.name,
      keywords: hits
    });
  }
}

const budgetRaw = Number(job.budget);
const budgetUSDC = Number.isFinite(budgetRaw)
  ? budgetRaw / 1e6
  : null;

let recommendation;

if (score >= 70) {
  recommendation = "STRONG_MATCH";
} else if (score >= 45) {
  recommendation = "GOOD_MATCH";
} else if (score >= 25) {
  recommendation = "PARTIAL_MATCH";
} else {
  recommendation = "POOR_MATCH";
}

const result = {
  matcher: "TermiX Provider Agent",
  version: "0.7.0",

  job: {
    jobId: job.jobId ?? null,
    status: job.status ?? null,
    strategyType: job.strategyType ?? null,
    title: job.title ?? null,
    budgetUSDC,
    providerId: job.providerId ?? null
  },

  provider: {
    capabilities: capabilities.map(x => x.name)
  },

  assessment: {
    matchScore: score,
    recommendation,
    matchedCapabilities: matched
  },

  execution: {
    mode: "READ_ONLY",
    offerSubmitted: false,
    transactionSigned: false
  }
};

console.log(
  JSON.stringify(result, null, 2)
);
