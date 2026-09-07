import fs from "node:fs";
import path from "node:path";

import {
  qualifyJobs
} from "./aacp-job-qualifier.mjs";

import {
  writeQualifiedJobReport
} from "./aacp-qualified-job-report.mjs";

const QUEUE_FILE =
  path.resolve(
    "provider-output",
    "state",
    "job-queue.json"
  );

function loadQueue() {
  if (!fs.existsSync(QUEUE_FILE)) {
    return [];
  }

  const data =
    JSON.parse(
      fs.readFileSync(
        QUEUE_FILE,
        "utf8"
      )
    );

  if (!Array.isArray(data)) {
    throw new Error(
      "Invalid provider job queue."
    );
  }

  return data;
}

function normalizeQueueJob(item) {
  if (
    item?.job &&
    typeof item.job === "object"
  ) {
    return {
      ...item.job,
      jobId:
        item.job.jobId ??
        item.job.id ??
        item.jobId ??
        null,
      status:
        item.job.status ??
        item.status ??
        null
    };
  }

  return {
    ...item,
    jobId:
      item?.jobId ??
      item?.id ??
      null
  };
}

function main() {
  const queue = loadQueue();

  const jobs =
    queue.map(
      normalizeQueueJob
    );

  const qualified =
    qualifyJobs(jobs);

  const result =
    writeQualifiedJobReport({
      state: "LOCAL_QUEUE",
      previousState: null,
      recovered: false,
      jobs: qualified,
      safety: {
        postPerformed: false,
        walletUsed: false,
        signingPerformed: false,
        broadcastPerformed: false,
        submissionPerformed: false
      }
    });

  console.log(
    "========================================"
  );
  console.log(
    " TERMiX PROVIDER QUALIFICATION"
  );
  console.log(
    " READ ONLY / LOCAL QUEUE"
  );
  console.log(
    "========================================"
  );

  console.log(
    `QUEUE_FILE=${QUEUE_FILE}`
  );

  console.log(
    `OBSERVED=${result.report.summary.observed}`
  );

  console.log(
    `UNIQUE=${result.report.summary.unique}`
  );

  console.log(
    `QUALIFIED=${result.report.summary.qualified}`
  );

  console.log(
    `BLOCKED=${result.report.summary.blocked}`
  );

  console.log(
    `REPORT=${result.file}`
  );

  console.log(
    "POST=NOT_PERFORMED"
  );

  console.log(
    "WALLET=NOT_USED"
  );

  console.log(
    "SIGNING=NOT_PERFORMED"
  );

  console.log(
    "BROADCAST=NOT_PERFORMED"
  );

  console.log(
    "SUBMISSION=NOT_PERFORMED"
  );
}

try {
  main();
} catch (err) {
  console.error(
    `QUALIFICATION_FAILED=${err.message}`
  );
  process.exit(1);
}
