import fs from "fs";
import path from "path";

const draftFile = process.argv[2];
const action = process.argv[3];

if (!draftFile || !action) {
  console.error(
    "Usage: pnpm run offer-review <OFFER-DRAFT.json> <approve|reject>"
  );
  process.exit(1);
}

if (!fs.existsSync(draftFile)) {
  console.error(`Draft not found: ${draftFile}`);
  process.exit(1);
}

if (!["approve", "reject"].includes(action)) {
  console.error(
    "Action must be: approve or reject"
  );
  process.exit(1);
}

const draft = JSON.parse(
  fs.readFileSync(draftFile, "utf8")
);

if (
  draft.execution?.offerSubmitted === true
) {
  console.error(
    "Safety violation: draft already marked submitted."
  );
  process.exit(2);
}

const approved =
  action === "approve";

const reviewStatus = approved
  ? "READY_TO_SUBMIT"
  : "BLOCKED";

const output = {
  review: "TermiX Offer Review Gate",
  version: "1.7.0",

  job: draft.job,

  pricing: draft.pricing,

  originalDraft: path.resolve(
    draftFile
  ),

  decision: {
    action: action.toUpperCase(),
    status: reviewStatus
  },

  execution: {
    mode: approved
      ? "READY_TO_SUBMIT"
      : "BLOCKED",

    walletRequired: false,

    offerSubmitted: false,

    transactionSigned: false,

    transactionBroadcast: false
  },

  safety: {
    automaticSubmission: false,
    automaticSigning: false,
    automaticBroadcast: false,
    manualReviewRequired: !approved
  }
};

const dir =
  path.dirname(
    path.resolve(draftFile)
  );

const jsonPath =
  path.join(
    dir,
    "OFFER-REVIEW.json"
  );

const mdPath =
  path.join(
    dir,
    "OFFER-REVIEW.md"
  );

fs.writeFileSync(
  jsonPath,
  JSON.stringify(output, null, 2)
);

const markdown = `# TermiX Offer Review

## Job

- Job ID: ${draft.job.jobId}
- Title: ${draft.job.title}

## Pricing

- Proposed price: ${draft.pricing.proposedPriceUSDC} USDC
- Budget: ${draft.pricing.budgetUSDC} USDC
- Budget status: ${draft.pricing.budgetStatus}

## Review Decision

- Action: ${action.toUpperCase()}
- Status: ${reviewStatus}

## Safety

- Wallet required: NO
- Offer submitted: NO
- Transaction signed: NO
- Transaction broadcast: NO
- Automatic submission: NO

${approved
  ? "The offer is READY_TO_SUBMIT but has NOT been submitted."
  : "The offer is BLOCKED and cannot proceed."}
`;

fs.writeFileSync(
  mdPath,
  markdown
);

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Offer Review Gate v1.7.0");
console.log("========================================");
console.log("");
console.log(`Job       : ${draft.job.jobId}`);
console.log(`Action    : ${action.toUpperCase()}`);
console.log(`Status    : ${reviewStatus}`);
console.log("");
console.log(`JSON      : ${jsonPath}`);
console.log(`Markdown  : ${mdPath}`);
console.log("");
console.log("Submitted : NO");
console.log("Signed    : NO");
console.log("Broadcast : NO");
console.log("");
