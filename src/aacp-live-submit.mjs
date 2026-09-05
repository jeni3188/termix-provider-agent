import fs from "node:fs";

const approvalFile = process.argv[2];
const confirm = process.argv[3];

const REQUIRED_CONFIRM = "SUBMIT_AACP_LIVE";

if (!approvalFile || confirm !== REQUIRED_CONFIRM) {
  console.error("");
  console.error("LIVE SUBMISSION BLOCKED");
  console.error("");
  console.error(
    "Usage: node src/aacp-live-submit.mjs <APPROVAL.json> SUBMIT_AACP_LIVE"
  );
  console.error("");
  process.exit(2);
}

const approval = JSON.parse(
  fs.readFileSync(approvalFile, "utf8")
);

if (approval?.status !== "READY_TO_SUBMIT") {
  console.error("BLOCKED: approval is not READY_TO_SUBMIT");
  process.exit(2);
}

if (approval?.execution?.submitted === true) {
  console.error("BLOCKED: approval already submitted");
  process.exit(2);
}

const jobId = approval.job?.jobId;
const agentId = process.env.AACP_AGENT_ID;
const ownerAddress = process.env.AACP_OWNER_ADDRESS;
const signature = process.env.AACP_SIGNATURE;
const timestamp = process.env.AACP_TIMESTAMP;

if (!jobId || !agentId || !ownerAddress || !signature || !timestamp) {
  console.error("BLOCKED: required live credentials are missing");
  console.error("");
  console.error("Required environment variables:");
  console.error("  AACP_AGENT_ID");
  console.error("  AACP_OWNER_ADDRESS");
  console.error("  AACP_SIGNATURE");
  console.error("  AACP_TIMESTAMP");
  process.exit(2);
}

const ts = Number(timestamp);

if (!Number.isSafeInteger(ts)) {
  console.error("BLOCKED: invalid timestamp");
  process.exit(2);
}

const age = Date.now() - ts;

if (age < 0 || age > 5 * 60 * 1000) {
  console.error("BLOCKED: EIP-191 timestamp is older than 5 minutes");
  process.exit(2);
}

const base =
  process.env.TERMIX_AACP_URL ||
  "https://aacp-backend.termix.live";

const api = `${base}/api/v1`;

async function getJson(url) {
  const response = await fetch(url, {
    signal: AbortSignal.timeout(15000)
  });

  const text = await response.text();

  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(
      `HTTP ${response.status}: non-JSON response`
    );
  }

  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status}: ${JSON.stringify(data)}`
    );
  }

  return data;
}

console.log("========================================");
console.log(" AACP LIVE SUBMISSION GATE");
console.log("========================================");
console.log(`Job       : ${jobId}`);
console.log(`Agent     : ${agentId}`);
console.log(`Owner     : ${ownerAddress}`);
console.log(`Timestamp : ${timestamp}`);
console.log("");

console.log("[1/4] Checking AACP backend...");

await getJson(`${api}/config`);

console.log("      Backend OK");

console.log("[2/4] Checking job eligibility...");

const jobResponse = await getJson(
  `${api}/jobs/${encodeURIComponent(jobId)}`
);

const job = jobResponse.data;

if (!job) {
  throw new Error("Job data missing");
}

if (!["OPEN", "FUNDED"].includes(job.status)) {
  throw new Error(
    `Job status ${job.status} does not accept offers`
  );
}

if (job.providerId) {
  throw new Error(
    `Job already has providerId=${job.providerId}`
  );
}

console.log(`      Status: ${job.status}`);
console.log("      Provider slot available");

console.log("[3/4] Checking provider eligibility...");

const agentResponse = await getJson(
  `${api}/agents/${encodeURIComponent(agentId)}`
);

const agent = agentResponse.data;

if (!agent) {
  throw new Error("Agent data missing");
}

const reputation =
  Number(agent.reputation?.score ?? -1);

const availableStake =
  BigInt(agent.stakingPool?.available ?? "0");

if (reputation < 70) {
  throw new Error(
    `Provider reputation ${reputation} < 70`
  );
}

if (availableStake < 100000000n) {
  throw new Error(
    `Available stake ${availableStake} < 100000000`
  );
}

console.log(`      Reputation: ${reputation}`);
console.log(`      Available stake: ${availableStake}`);

console.log("[4/4] Sending official offer payload...");

const payload = {
  agentId,
  ownerAddress
};

const response = await fetch(
  `${api}/jobs/${encodeURIComponent(jobId)}/offers`,
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Wallet-Signature": signature,
      "X-Wallet-Address": ownerAddress,
      "X-Wallet-Timestamp": String(timestamp)
    },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(15000)
  }
);

const text = await response.text();

let result;
try {
  result = JSON.parse(text);
} catch {
  throw new Error(
    `AACP returned HTTP ${response.status} non-JSON`
  );
}

if (!response.ok || result.success !== true) {
  throw new Error(
    `Offer submission failed: HTTP ${response.status} ${JSON.stringify(result)}`
  );
}

console.log("");
console.log("========================================");
console.log(" OFFER SUBMITTED");
console.log("========================================");
console.log(`Job       : ${jobId}`);
console.log(`Agent     : ${result.data?.agentId ?? agentId}`);
console.log(`Owner     : ${result.data?.ownerAddress ?? ownerAddress}`);
console.log(`Status    : ${result.data?.status ?? "UNKNOWN"}`);
console.log(`Created   : ${result.data?.createdAt ?? "UNKNOWN"}`);
console.log("Network   : REQUEST SENT");
console.log("Signing   : PROVIDED BY OPERATOR");
console.log("");
