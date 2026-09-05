import fs from "fs";
import crypto from "crypto";

const input = process.argv[2];

if (!input) {
  console.error("Usage: pnpm run aacp-validate <OFFER-APPROVAL.json>");
  process.exit(2);
}

if (!fs.existsSync(input)) {
  console.error(`File not found: ${input}`);
  process.exit(2);
}

let approval;

try {
  approval = JSON.parse(fs.readFileSync(input, "utf8"));
} catch {
  console.error("Invalid JSON.");
  process.exit(2);
}

const errors = [];

const jobId = approval?.job?.jobId;
const status = approval?.decision?.status;
const price = approval?.pricing?.proposedPriceUSDC;
const budget = approval?.pricing?.budgetUSDC;
const submitted = approval?.execution?.offerSubmitted;
const signed = approval?.execution?.transactionSigned;
const broadcast = approval?.execution?.transactionBroadcast;

if (!approval.approvalId) {
  errors.push("Missing approvalId");
}

if (status !== "READY_TO_SUBMIT") {
  errors.push(`Invalid approval status: ${status}`);
}

if (!jobId || typeof jobId !== "string") {
  errors.push("Invalid jobId");
}

if (!Number.isFinite(price) || price <= 0) {
  errors.push("Invalid proposed price");
}

if (!Number.isFinite(budget) || budget <= 0) {
  errors.push("Invalid budget");
}

if (Number.isFinite(price) && Number.isFinite(budget) && price > budget) {
  errors.push("Proposed price exceeds job budget");
}

if (submitted === true) {
  errors.push("Offer is already marked as submitted");
}

if (signed === true) {
  errors.push("Transaction is already marked as signed");
}

if (broadcast === true) {
  errors.push("Transaction is already marked as broadcast");
}

if (approval?.safety?.networkRequestSent === true) {
  errors.push("Approval indicates a network request was already sent");
}

/*
 * Recompute the exact approval hash used by v1.9.0.
 */
const canonical = JSON.stringify({
  job: approval.job,
  pricing: approval.pricing,
  decision: approval.decision
});

const calculatedHash = crypto
  .createHash("sha256")
  .update(canonical)
  .digest("hex");

const storedHash = approval?.integrity?.approvalHash;

if (!storedHash) {
  errors.push("Missing approval hash");
} else if (storedHash !== calculatedHash) {
  errors.push("Approval hash mismatch");
}

/*
 * Build the exact dry-run payload.
 * No request is sent.
 */
const payload = {
  jobId,
  proposedPriceUSDC: price,
  message: "Provider draft: EVM smart contract security assessment.",
  deliverables: [
    "Security assessment report",
    "Prioritized vulnerability findings",
    "Severity and confidence classification",
    "Risk score and overall risk level",
    "Methodology and limitations",
    "Machine-readable JSON deliverable",
    "Markdown deliverable"
  ]
};

const result = {
  validator: "TermiX AACP Submission Validator",
  version: "1.9.1",

  source: input,

  validation: {
    passed: errors.length === 0,
    errors,
    checks: {
      approvalStatus: status === "READY_TO_SUBMIT",
      jobId: Boolean(jobId),
      priceValid: Number.isFinite(price) && price > 0,
      priceWithinBudget:
        Number.isFinite(price) &&
        Number.isFinite(budget) &&
        price <= budget,
      notSubmitted: submitted !== true,
      notSigned: signed !== true,
      notBroadcast: broadcast !== true,
      networkNotSent: approval?.safety?.networkRequestSent !== true,
      approvalHashValid: storedHash === calculatedHash
    }
  },

  endpoint: {
    method: "POST",
    path: `/api/v1/jobs/${jobId}/offers`,
    networkRequestSent: false
  },

  payload,

  integrity: {
    algorithm: "SHA-256",
    storedApprovalHash: storedHash ?? null,
    calculatedApprovalHash: calculatedHash
  },

  execution: {
    mode: "VALIDATION_ONLY",
    walletRequired: false,
    walletUsed: false,
    transactionSigned: false,
    transactionBroadcast: false,
    offerSubmitted: false,
    networkRequestSent: false
  },

  safety: {
    readOnly: true,
    automaticSubmission: false,
    automaticSigning: false,
    automaticBroadcast: false,
    manualConfirmationRequired: true
  }
};

const dir = input.substring(0, input.lastIndexOf("/"));
const out = `${dir}/AACP-SUBMISSION-VALIDATION.json`;

fs.writeFileSync(out, JSON.stringify(result, null, 2));

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" AACP Submission Validator v1.9.1");
console.log(" READ ONLY");
console.log("========================================");
console.log("");

if (errors.length === 0) {
  console.log("VALIDATION PASSED");
  console.log("");
  console.log("Approval status : READY_TO_SUBMIT");
  console.log(`Job             : ${jobId}`);
  console.log(`Price           : ${price} USDC`);
  console.log(`Budget          : ${budget} USDC`);
  console.log("Hash            : VALID");
  console.log("Payload         : VALID");
  console.log("");
  console.log("READY_FOR_LIVE_SUBMISSION");
} else {
  console.log("VALIDATION BLOCKED");
  console.log("");
  for (const error of errors) {
    console.log(`- ${error}`);
  }
}

console.log("");
console.log("Network request : NOT SENT");
console.log("Wallet          : NOT USED");
console.log("Signing         : NOT USED");
console.log("Submitted       : NO");
console.log("Broadcast       : NO");
console.log("");
console.log(`JSON            : ${out}`);

if (errors.length > 0) {
  process.exit(2);
}
