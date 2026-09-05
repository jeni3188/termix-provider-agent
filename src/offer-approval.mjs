import fs from "fs";
import crypto from "crypto";

const input = process.argv[2];

if (!input) {
  console.error("Usage: pnpm run offer-approval <OFFER-REVIEW.json>");
  process.exit(1);
}

if (!fs.existsSync(input)) {
  console.error(`File not found: ${input}`);
  process.exit(1);
}

const review = JSON.parse(fs.readFileSync(input, "utf8"));

if (review?.decision?.status !== "READY_TO_SUBMIT") {
  console.error("Approval blocked.");
  console.error(`Status: ${review?.decision?.status ?? "UNKNOWN"}`);
  process.exit(2);
}

if (review?.execution?.offerSubmitted === true) {
  console.error("Approval blocked: offer already submitted.");
  process.exit(2);
}

const canonical = JSON.stringify({
  job: review.job,
  pricing: review.pricing,
  decision: review.decision
});

const approvalHash = crypto
  .createHash("sha256")
  .update(canonical)
  .digest("hex");

const timestamp = new Date().toISOString();

const approval = {
  approval: "TermiX Immutable Offer Approval",
  version: "1.9.0",
  approvalId: `approval-${Date.now()}`,
  createdAt: timestamp,

  job: {
    jobId: review.job.jobId,
    title: review.job.title,
    strategyType: review.job.strategyType,
    status: review.job.status
  },

  pricing: review.pricing,

  decision: {
    action: "APPROVE",
    status: "READY_TO_SUBMIT"
  },

  integrity: {
    algorithm: "SHA-256",
    approvalHash,
    sourceReview: input
  },

  execution: {
    mode: "APPROVAL_ONLY",
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false
  },

  safety: {
    immutableRecord: true,
    automaticSubmission: false,
    automaticSigning: false,
    automaticBroadcast: false,
    networkRequestSent: false,
    manualConfirmationRequired: true
  }
};

const dir = input.substring(0, input.lastIndexOf("/"));
const jsonPath = `${dir}/OFFER-APPROVAL-${approval.approvalId}.json`;
const mdPath = `${dir}/OFFER-APPROVAL-${approval.approvalId}.md`;

fs.writeFileSync(jsonPath, JSON.stringify(approval, null, 2));

const md = `# TermiX Offer Approval

- Approval ID: ${approval.approvalId}
- Job: ${approval.job.jobId}
- Status: READY_TO_SUBMIT
- Price: ${approval.pricing.proposedPriceUSDC} USDC
- Created: ${timestamp}
- SHA-256: ${approvalHash}

## Execution

- Network request: NOT SENT
- Wallet: NOT USED
- Signing: NOT USED
- Submission: NOT SENT
- Broadcast: NOT SENT

## Safety

This is an immutable approval record for a later submission step.
It does not submit an offer and does not perform any blockchain transaction.
`;

fs.writeFileSync(mdPath, md);

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Immutable Offer Approval v1.9.0");
console.log("========================================");
console.log("");
console.log(`Job       : ${approval.job.jobId}`);
console.log(`Price     : ${approval.pricing.proposedPriceUSDC} USDC`);
console.log(`Status    : ${approval.decision.status}`);
console.log(`Approval  : ${approval.approvalId}`);
console.log(`SHA-256   : ${approvalHash}`);
console.log("");
console.log("Network request : NOT SENT");
console.log("Wallet          : NOT USED");
console.log("Signing         : NOT USED");
console.log("Submitted       : NO");
console.log("Broadcast       : NO");
console.log("");
console.log(`JSON      : ${jsonPath}`);
console.log(`Markdown  : ${mdPath}`);
