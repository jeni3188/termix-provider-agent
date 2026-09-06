import fs from "node:fs";
import path from "node:path";
import {
  ensureStagingPath,
  resolveSource
} from "./source-router.mjs";
import {
  createManifest,
  verifyManifest
} from "./artifact-manifest.mjs";

const MAX_SOURCE_BYTES = 5 * 1024 * 1024;

function validJobId(jobId) {
  return (
    typeof jobId === "string" &&
    /^[A-Za-z0-9._-]{1,128}$/.test(jobId)
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

function intake(jobId, sourcePath, requestedName = null) {
  if (!validJobId(jobId)) {
    return reject(
      "INVALID_JOB_ID",
      "Job ID is invalid."
    );
  }

  if (
    typeof sourcePath !== "string" ||
    sourcePath.trim() === ""
  ) {
    return reject(
      "SOURCE_ARTIFACT_REQUIRED",
      "A local source/artifact path is required."
    );
  }

  const absoluteSource =
    path.resolve(sourcePath);

  if (!fs.existsSync(absoluteSource)) {
    return reject(
      "SOURCE_ARTIFACT_REQUIRED",
      "Local source/artifact does not exist.",
      { path: absoluteSource }
    );
  }

  const stat =
    fs.statSync(absoluteSource);

  if (!stat.isFile()) {
    return reject(
      "SOURCE_REJECTED",
      "Source/artifact is not a regular file."
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

  const originalExtension =
    path.extname(absoluteSource).toLowerCase();

  if (
    ![".sol", ".json", ".txt"].includes(
      originalExtension
    )
  ) {
    return reject(
      "SOURCE_REJECTED",
      "Source/artifact extension is not allowed.",
      {
        extension: originalExtension
      }
    );
  }

  const jobRoot =
    ensureStagingPath(jobId);

  const filename =
    requestedName ||
    path.basename(absoluteSource);

  if (
    typeof filename !== "string" ||
    filename.trim() === ""
  ) {
    return reject(
      "SOURCE_REJECTED",
      "Artifact filename is invalid."
    );
  }

  const destination =
    path.resolve(jobRoot, filename);

  const relative =
    path.relative(jobRoot, destination);

  if (
    relative.startsWith("..") ||
    path.isAbsolute(relative)
  ) {
    return reject(
      "SOURCE_REJECTED",
      "Artifact filename escapes the job staging directory."
    );
  }

  const destinationExtension =
    path.extname(destination).toLowerCase();

  if (
    ![".sol", ".json", ".txt"].includes(
      destinationExtension
    )
  ) {
    return reject(
      "SOURCE_REJECTED",
      "Destination artifact extension is not allowed.",
      {
        extension: destinationExtension
      }
    );
  }

  fs.copyFileSync(
    absoluteSource,
    destination
  );

  const routed =
    resolveSource(
      jobId,
      relative
    );

  if (!routed.allowed) {
    return routed;
  }

  const manifest =
    createManifest(
      jobId,
      relative
    );

  if (!manifest.allowed) {
    return reject(
      "MANIFEST_CREATION_FAILED",
      manifest.message || "Manifest creation failed."
    );
  }

  const verified =
    verifyManifest(jobId);

  if (!verified.allowed) {
    return reject(
      "MANIFEST_VERIFICATION_FAILED",
      verified.message || "Manifest verification failed.",
      {
        verificationCode: verified.code
      }
    );
  }

  return {
    allowed: true,
    code: "INTAKE_READY",
    intake: {
      version: "1.0.0",
      mode: "MANUAL_LOCAL_STAGING",
      jobId,
      source: {
        originalPath: absoluteSource,
        stagedPath: routed.path,
        relativePath: relative,
        extension: routed.extension,
        size: routed.size
      },
      manifest: {
        path: manifest.path,
        code: verified.code,
        sha256: verified.manifest.artifact.sha256
      }
    },
    safety: {
      networkFetch: false,
      networkRequest: false,
      walletUsed: false,
      signing: false,
      broadcast: false,
      automaticSubmission: false
    }
  };
}

export { intake };

if (
  process.argv[1] ===
  new URL(import.meta.url).pathname
) {
  const jobId = process.argv[2];
  const sourcePath = process.argv[3];
  const requestedName = process.argv[4] || null;

  const result =
    intake(
      jobId,
      sourcePath,
      requestedName
    );

  console.log(
    JSON.stringify(
      result,
      null,
      2
    )
  );

  process.exit(
    result.allowed ? 0 : 2
  );
}
