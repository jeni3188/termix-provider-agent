import fs from "node:fs";
import path from "node:path";

const QUEUE_FILE =
  path.resolve(
    "provider-output",
    "state",
    "job-queue.json"
  );

const REPORT_FILE =
  path.resolve(
    "provider-output",
    "aacp-observer",
    "latest-qualified-job-report.json"
  );

function loadJson(file) {
  if (!fs.existsSync(file)) {
    return null;
  }

  return JSON.parse(
    fs.readFileSync(file, "utf8")
  );
}

const queueData =
  loadJson(QUEUE_FILE);

const queue =
  Array.isArray(queueData)
    ? queueData
    : [];

const report =
  loadJson(REPORT_FILE);

const qualified =
  Array.isArray(report?.qualified)
    ? report.qualified
    : [];

const blocked =
  Array.isArray(report?.blocked)
    ? report.blocked
    : [];

const strongMatch =
  qualified.filter(
    job =>
      job.qualification ===
      "STRONG_MATCH"
  ).length;

const trustedArtifact =
  qualified.filter(
    job =>
      job.artifact ===
        "TRUSTED_ARTIFACT" &&
      job.trusted === true
  ).length;

const localQueueState =
  Array.isArray(queueData)
    ? "HEALTHY"
    : "INVALID";

const qualificationState =
  report
    ? "READY"
    : "NOT_RUN";

console.log(
  "========================================"
);

console.log(
  " TERMiX PROVIDER STATUS"
);

console.log(
  "========================================"
);

console.log(
  `QUEUE             : ${queue.length}`
);

console.log(
  `QUALIFIED         : ${qualified.length}`
);

console.log(
  `BLOCKED           : ${blocked.length}`
);

console.log(
  `STRONG_MATCH      : ${strongMatch}`
);

console.log(
  `TRUSTED_ARTIFACT  : ${trustedArtifact}`
);

console.log("");

console.log(
  "AACP BACKEND      : NOT_CHECKED (READ_ONLY)"
);

console.log(
  `LOCAL QUEUE       : ${localQueueState}`
);

console.log(
  `QUALIFICATION     : ${qualificationState}`
);

console.log(
  "LIVE SUBMISSION   : BLOCKED"
);

console.log("");

console.log(
  "WALLET            : NOT_USED"
);

console.log(
  "SIGNING           : NOT_PERFORMED"
);

console.log(
  "BROADCAST         : NOT_PERFORMED"
);

console.log(
  "SUBMISSION        : NOT_PERFORMED"
);

console.log("");

if (report) {
  console.log(
    `REPORT            : ${REPORT_FILE}`
  );

  console.log(
    `REPORT MODE       : ${report.mode}`
  );

  console.log(
    `REPORT STATE      : ${report.state}`
  );
}

console.log(
  "========================================"
);
