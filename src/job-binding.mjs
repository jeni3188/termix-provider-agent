import crypto from "node:crypto";

const JOB_FIELDS = [
  "jobId",
  "status",
  "strategyType",
  "budget",
  "title",
  "description",
  "deadline",
  "providerId"
];

function reject(code, message, extra = {}) {
  return {
    allowed: false,
    code,
    message,
    ...extra
  };
}

function normalize(value) {
  if (Array.isArray(value)) {
    return value.map(normalize);
  }

  if (
    value &&
    typeof value === "object"
  ) {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map(key => [
          key,
          normalize(value[key])
        ])
    );
  }

  return value;
}

export function canonicalizeJob(job) {
  if (
    !job ||
    typeof job !== "object" ||
    Array.isArray(job)
  ) {
    throw new Error("INVALID_JOB");
  }

  const selected = {};

  for (const field of JOB_FIELDS) {
    if (
      Object.prototype.hasOwnProperty.call(
        job,
        field
      )
    ) {
      selected[field] = job[field];
    }
  }

  return JSON.stringify(
    normalize(selected)
  );
}

export function fingerprintJob(job) {
  const canonical =
    canonicalizeJob(job);

  return crypto
    .createHash("sha256")
    .update(canonical, "utf8")
    .digest("hex");
}

export function validateJobBinding(
  manifest,
  job
) {
  if (
    !manifest ||
    typeof manifest !== "object"
  ) {
    return reject(
      "MANIFEST_INVALID",
      "Manifest is invalid."
    );
  }

  if (
    !job ||
    typeof job !== "object" ||
    Array.isArray(job)
  ) {
    return reject(
      "INVALID_JOB",
      "Job metadata is invalid."
    );
  }

  const manifestJobId =
    manifest.jobId;

  const jobId =
    job.jobId ??
    job.id;

  if (
    typeof jobId !== "string" ||
    manifestJobId !== jobId
  ) {
    return reject(
      "JOB_BINDING_ID_MISMATCH",
      "Manifest Job ID does not match supplied job metadata.",
      {
        manifestJobId,
        jobId
      }
    );
  }

  const expected =
    manifest.jobBinding?.fingerprint;

  if (
    typeof expected !== "string" ||
    !/^[a-f0-9]{64}$/.test(expected)
  ) {
    return reject(
      "JOB_BINDING_REQUIRED",
      "Manifest does not contain a valid job fingerprint."
    );
  }

  const actual =
    fingerprintJob(job);

  if (actual !== expected) {
    return reject(
      "JOB_BINDING_MISMATCH",
      "Job metadata fingerprint does not match the manifest.",
      {
        expected,
        actual
      }
    );
  }

  return {
    allowed: true,
    code: "JOB_BINDING_VALID",
    jobId,
    fingerprint: actual
  };
}
