import fs from "fs";
import path from "path";

const processorFile = process.argv[2];

if (!processorFile) {
  console.error(
    "Usage: pnpm run offer-draft <processor-result.json>"
  );
  process.exit(1);
}

if (!fs.existsSync(processorFile)) {
  console.error(`File not found: ${processorFile}`);
  process.exit(1);
}

const result = JSON.parse(
  fs.readFileSync(processorFile, "utf8")
);

const evaluation = result.evaluation;
const execution = result.execution;

if (
  execution.path !== "OFFER_REVIEW" ||
  evaluation.decision.status !==
    "PROCEED_TO_OFFER_REVIEW"
) {
  console.error(
    "Offer draft blocked: job is not eligible for OFFER_REVIEW."
  );
  console.error(
    `Decision: ${evaluation.decision.status}`
  );
  console.error(
    `Path: ${execution.path}`
  );
  process.exit(2);
}

const job = result.job;
const pricing = evaluation.pricing;
const matching = evaluation.matching;

const price = pricing.recommendedPriceUSDC;

const proposal = [
  `I can perform a structured EVM smart contract security assessment for this job.`,
  ``,
  `The assessment will cover:`,
  `- Reentrancy and external-call risks`,
  `- Access-control weaknesses`,
  `- tx.origin usage`,
  `- delegatecall and proxy/upgrade risks`,
  `- dangerous low-level calls`,
  `- timestamp/block-dependent logic`,
  `- unchecked operations and other static security indicators.`,
  ``,
  `The final deliverable will contain prioritized findings,`,
  `severity/confidence indicators, risk scoring, methodology,`,
  `and limitations requiring manual validation.`
].join("\n");

const deliverables = [
  "Security assessment report",
  "Prioritized vulnerability findings",
  "Severity and confidence classification",
  "Risk score and overall risk level",
  "Methodology and limitations",
  "Machine-readable JSON deliverable",
  "Markdown deliverable"
];

const draft = {
  offer: "TermiX Provider Offer Draft",
  version: "1.6.0",

  job: {
    jobId: job.jobId,
    title: job.title,
    strategyType: job.strategyType,
    status: job.status
  },

  provider: {
    capabilityMatch: matching.score,
    recommendation: matching.recommendation,
    matchedCapabilities:
      matching.matchedCapabilities
  },

  pricing: {
    proposedPriceUSDC: price,
    budgetUSDC: pricing.budgetUSDC,
    estimatedValueUSDC:
      pricing.estimatedValueUSDC,
    budgetStatus:
      pricing.budgetStatus,
    estimatedHours:
      evaluation.workload.estimatedHours,
    referenceHourlyRateUSDC:
      pricing.referenceHourlyRateUSDC
  },

  proposal,

  deliverables,

  execution: {
    mode: "DRAFT_ONLY",
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false
  },

  review: {
    status: "PENDING_MANUAL_REVIEW",
    automaticSubmission: false
  }
};

const outputDir =
  path.dirname(
    path.resolve(processorFile)
  );

const jsonPath =
  path.join(
    outputDir,
    "OFFER-DRAFT.json"
  );

const mdPath =
  path.join(
    outputDir,
    "OFFER-DRAFT.md"
  );

fs.writeFileSync(
  jsonPath,
  JSON.stringify(draft, null, 2)
);

const markdown = `# TermiX Provider Offer Draft

## Job

- Job ID: ${job.jobId}
- Title: ${job.title}
- Strategy: ${job.strategyType}
- Match: ${matching.score}/100
- Recommendation: ${matching.recommendation}

## Pricing

- Proposed price: ${price} USDC
- Job budget: ${pricing.budgetUSDC} USDC
- Estimated value: ${pricing.estimatedValueUSDC} USDC
- Budget status: ${pricing.budgetStatus}
- Estimated effort: ${evaluation.workload.estimatedHours} hours

## Proposal

${proposal}

## Deliverables

${deliverables.map(x => `- ${x}`).join("\n")}

## Execution Safety

- Mode: DRAFT_ONLY
- Wallet required: NO
- Offer submitted: NO
- Transaction signed: NO
- Transaction broadcast: NO

## Review

Status: PENDING_MANUAL_REVIEW

This document is a draft only. No offer has been submitted to AACP.
`;

fs.writeFileSync(
  mdPath,
  markdown
);

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Offer Draft Engine v1.6.0");
console.log(" DRAFT ONLY");
console.log("========================================");
console.log("");
console.log(`Job       : ${job.jobId}`);
console.log(`Match     : ${matching.score}/100`);
console.log(`Budget    : ${pricing.budgetUSDC} USDC`);
console.log(`Proposed  : ${price} USDC`);
console.log(`Status    : PENDING_MANUAL_REVIEW`);
console.log("");
console.log(`JSON      : ${jsonPath}`);
console.log(`Markdown  : ${mdPath}`);
console.log("");
console.log("Wallet    : NOT USED");
console.log("Signing   : NOT USED");
console.log("Submitted : NO");
console.log("");
