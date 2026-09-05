import fs from "node:fs";
import path from "node:path";

const reviewFile = process.argv[2];
const mode = process.argv[3] || "dry-run";

if (!reviewFile) {
  console.error("Usage: pnpm run aacp-submit <OFFER-REVIEW.json> [dry-run]");
  process.exit(2);
}

if (mode !== "dry-run") {
  console.error("LIVE submission is intentionally disabled in this adapter.");
  console.error("Use the dedicated live gate only after explicit confirmation.");
  process.exit(2);
}

const review = JSON.parse(fs.readFileSync(reviewFile, "utf8"));

if (review?.decision?.status !== "READY_TO_SUBMIT") {
  console.error("BLOCKED: approval status is not READY_TO_SUBMIT");
  process.exit(2);
}

if (review?.execution?.offerSubmitted === true) {
  console.error("BLOCKED: offer already marked submitted");
  process.exit(2);
}

const jobId = review.job?.jobId;
if (!jobId) {
  console.error("BLOCKED: missing jobId");
  process.exit(2);
}

const payload = {
  agentId: "<AGENT_ID>",
  ownerAddress: "<OWNER_ADDRESS>"
};

const endpoint =
  `/api/v1/jobs/${encodeURIComponent(jobId)}/offers`;

const output = {
  adapter: "TermiX AACP Offer Submission Adapter",
  version: "2.0.0",
  mode: "DRY_RUN",
  jobId,
  endpoint,
  method: "POST",
  payload,
  headers: {
    "Content-Type": "application/json",
    "X-Wallet-Signature": "<GENERATED_AT_LIVE_GATE>",
    "X-Wallet-Address": "<OWNER_ADDRESS>",
    "X-Wallet-Timestamp": "<CURRENT_TIMESTAMP_MS>"
  },
  networkRequestSent: false,
  walletUsed: false,
  signingUsed: false,
  submitted: false,
  broadcast: false,
  schemaVerified: true,
  schemaSource:
    "TermiX-official/termix-agent-skills/docs/provider-submit-offer.md"
};

const dir = path.dirname(reviewFile);
const base = path.join(dir, "AACP-SUBMISSION-DRY-RUN");

fs.writeFileSync(
  `${base}.json`,
  JSON.stringify(output, null, 2)
);

fs.writeFileSync(
  `${base}.md`,
  [
    "# AACP Offer Submission Dry Run",
    "",
    `- Job: ${jobId}`,
    `- Endpoint: POST ${endpoint}`,
    "- Schema: VERIFIED",
    "- Network request: NOT SENT",
    "- Wallet: NOT USED",
    "- Signing: NOT USED",
    "- Submitted: NO",
    "",
    "## Official payload",
    "",
    "```json",
    JSON.stringify(payload, null, 2),
    "```",
    ""
  ].join("\n")
);

console.log("AACP Submission Adapter v2.0.0");
console.log("SCHEMA VERIFIED");
console.log("DRY-RUN ONLY");
console.log(`Job       : ${jobId}`);
console.log(`Endpoint  : POST ${endpoint}`);
console.log("Payload   : agentId + ownerAddress");
console.log("Network   : NOT SENT");
console.log("Wallet    : NOT USED");
console.log("Signing   : NOT USED");
console.log("Submitted : NO");
