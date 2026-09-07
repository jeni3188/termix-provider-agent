import fs from "node:fs";
import path from "node:path";

const STAGING_ROOT =
  path.resolve(
    process.env.PROVIDER_SOURCE_STAGING ||
    "provider-output/source-staging"
  );

const ALLOWED_EXTENSIONS = new Set([
  ".sol",
  ".json",
  ".txt"
]);

const MAX_SOURCE_BYTES =
  5 * 1024 * 1024;

function validJobId(jobId) {
  return (
    typeof jobId === "string" &&
    /^[A-Za-z0-9._-]{1,128}$/.test(jobId)
  );
}

function isInside(parent, target) {
  const relative = path.relative(parent, target);

  return (
    relative === "" ||
    (!relative.startsWith("..") &&
      !path.isAbsolute(relative))
  );
}

function reject(code, message, extra = {}) {
  return {
    allowed: false,
    code,
    message,
    ...extra
  };
}

export function resolveSource(jobId, requestedPath) {
  if (!validJobId(jobId)) {
    return reject(
      "INVALID_JOB_ID",
      "Job ID is invalid."
    );
  }

  if (
    typeof requestedPath !== "string" ||
    requestedPath.trim() === ""
  ) {
    return reject(
      "SOURCE_ARTIFACT_REQUIRED",
      "An explicit source/artifact path is required."
    );
  }

  const jobRoot =
    path.resolve(STAGING_ROOT, jobId);

  const candidate =
    path.resolve(jobRoot, requestedPath);

  if (!isInside(jobRoot, candidate)) {
    return reject(
      "SOURCE_REJECTED",
      "Source path escapes the job staging directory.",
      { reason: "PATH_TRAVERSAL_OR_OUTSIDE_STAGING" }
    );
  }

  const extension =
    path.extname(candidate).toLowerCase();

  if (!ALLOWED_EXTENSIONS.has(extension)) {
    return reject(
      "SOURCE_REJECTED",
      "Source/artifact extension is not allowed.",
      { extension }
    );
  }

  if (!fs.existsSync(candidate)) {
    return reject(
      "SOURCE_ARTIFACT_REQUIRED",
      "Requested source/artifact does not exist.",
      { path: candidate }
    );
  }

  let canonicalRoot;
  let canonicalCandidate;

  try {
    canonicalRoot = fs.realpathSync(jobRoot);
    canonicalCandidate = fs.realpathSync(candidate);
  } catch {
    return reject(
      "SOURCE_REJECTED",
      "Source/artifact could not be canonically resolved.",
      { reason: "REALPATH_RESOLUTION_FAILED" }
    );
  }

  if (!isInside(canonicalRoot, canonicalCandidate)) {
    return reject(
      "SOURCE_REJECTED",
      "Source/artifact resolves outside the job staging directory.",
      { reason: "SYMLINK_ESCAPE_OR_OUTSIDE_STAGING" }
    );
  }

  const stat = fs.statSync(candidate);

  if (!stat.isFile()) {
    return reject(
      "SOURCE_REJECTED",
      "Requested source/artifact is not a regular file."
    );
  }

  if (stat.size > MAX_SOURCE_BYTES) {
    return reject(
      "SOURCE_REJECTED",
      "Source/artifact exceeds the maximum allowed size.",
      {
        size: stat.size,
        maxBytes: MAX_SOURCE_BYTES
      }
    );
  }

  return {
    allowed: true,
    code: "SOURCE_ALLOWED",
    jobId,
    path: candidate,
    extension,
    size: stat.size,
    stagingRoot: jobRoot
  };
}

export function getStagingPath(jobId) {
  if (!validJobId(jobId)) {
    throw new Error("INVALID_JOB_ID");
  }

  return path.resolve(
    STAGING_ROOT,
    jobId
  );
}

export function ensureStagingPath(jobId) {
  const jobRoot = getStagingPath(jobId);

  fs.mkdirSync(jobRoot, {
    recursive: true
  });

  return jobRoot;
}

if (process.argv[1] === new URL(import.meta.url).pathname) {
  const jobId = process.argv[2];
  const requestedPath = process.argv[3];

  const result =
    resolveSource(jobId, requestedPath);

  console.log(
    JSON.stringify(result, null, 2)
  );

  process.exit(result.allowed ? 0 : 2);
}
