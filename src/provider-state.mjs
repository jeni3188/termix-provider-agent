import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const STATE_DIR = "provider-output/state";
const QUEUE_FILE = path.join(STATE_DIR, "job-queue.json");
const AUDIT_FILE = path.join(STATE_DIR, "audit-log.jsonl");

fs.mkdirSync(STATE_DIR, { recursive: true });

function loadQueue() {
  if (!fs.existsSync(QUEUE_FILE)) return [];

  try {
    const data = JSON.parse(fs.readFileSync(QUEUE_FILE, "utf8"));
    return Array.isArray(data) ? data : [];
  } catch {
    throw new Error("Invalid job queue");
  }
}

function saveQueue(queue) {
  fs.writeFileSync(
    QUEUE_FILE,
    JSON.stringify(queue, null, 2) + "\n"
  );
}

function audit(event, data = {}) {
  const record = {
    timestamp: new Date().toISOString(),
    event,
    data
  };

  const canonical = JSON.stringify(record);

  record.sha256 = crypto
    .createHash("sha256")
    .update(canonical)
    .digest("hex");

  fs.appendFileSync(
    AUDIT_FILE,
    JSON.stringify(record) + "\n"
  );

  return record;
}

const command = process.argv[2];

if (command === "add") {
  const file = process.argv[3];

  if (!file) {
    console.error("Usage: provider-state add <job.json>");
    process.exit(2);
  }

  const job = JSON.parse(
    fs.readFileSync(file, "utf8")
  );

  if (!job.jobId) {
    console.error("BLOCKED: missing jobId");
    process.exit(2);
  }

  const queue = loadQueue();

  if (queue.some(x => x.jobId === job.jobId)) {
    console.log(`DUPLICATE: ${job.jobId}`);
    process.exit(0);
  }

  queue.push({
    jobId: job.jobId,
    status: "QUEUED",
    addedAt: new Date().toISOString(),
    job
  });

  saveQueue(queue);

  audit("JOB_QUEUED", {
    jobId: job.jobId
  });

  console.log(`QUEUED: ${job.jobId}`);
  process.exit(0);
}

if (command === "list") {
  const queue = loadQueue();

  console.log("========================================");
  console.log(" PROVIDER JOB QUEUE");
  console.log("========================================");

  if (!queue.length) {
    console.log("Queue empty");
    process.exit(0);
  }

  for (const item of queue) {
    console.log(
      `${item.jobId}  ${item.status}  ${item.addedAt}`
    );
  }

  process.exit(0);
}

if (command === "audit") {
  if (!fs.existsSync(AUDIT_FILE)) {
    console.log("Audit log empty");
    process.exit(0);
  }

  console.log(
    fs.readFileSync(AUDIT_FILE, "utf8")
  );

  process.exit(0);
}

console.error("Usage:");
console.error("  provider-state add <job.json>");
console.error("  provider-state list");
console.error("  provider-state audit");
process.exit(2);
