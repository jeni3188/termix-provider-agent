import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import {
  resolveSource,
  getStagingPath
} from "./source-router.mjs";

function reject(code, message, extra = {}) {
  return {
    allowed: false,
    code,
    message,
    ...extra
  };
}

function sha256File(file) {
  const hash = crypto.createHash("sha256");
  hash.update(fs.readFileSync(file));
  return hash.digest("hex");
}

function validSha256(value) {
  return (
    typeof value === "string" &&
    /^[a-f0-9]{64}$/.test(value)
  );
}

function validSize(value) {
  return (
    Number.isInteger(value) &&
    value >= 0
  );
}

/**
 * Build a trusted artifact reference from an already staged artifact.
 *
 * IMPORTANT:
 * - No network access.
 * - No URL fetching.
 * - Artifact must already exist inside the job staging directory.
 */
export function createTrustedArtifactReference(
  jobId,
  requestedPath
) {
  const routed = resolveSource(jobId, requestedPath);

  if (!routed.allowed) {
    return routed;
  }

  const jobRoot = getStagingPath(jobId);
  const relativePath = path.relative(
    jobRoot,
    routed.path
  );

  if (
    !relativePath ||
    relativePath.startsWith("..") ||
    path.isAbsolute(relativePath)
  ) {
    return reject(
      "TRUSTED_ARTIFACT_PATH_INVALID",
      "Artifact path is outside the job staging directory."
    );
  }

  const digest = sha256File(routed.path);

  return {
    allowed: true,
    code: "TRUSTED_ARTIFACT_REFERENCE_CREATED",
    reference: {
      version: "1.0.0",
      jobId,
      source: {
        mode: "LOCAL_STAGING_ONLY"
      },
      artifact: {
        path: relativePath,
        size: routed.size,
        sha256: digest
      },
      safety: {
        networkFetch: false,
        arbitraryUrlFetch: false,
        walletUsed: false,
        signing: false,
        broadcast: false
      }
    }
  };
}

/**
 * Verify an artifact against a trusted reference.
 *
 * The artifact is resolved only through source-router, therefore:
 * - no absolute paths
 * - no traversal
 * - no URL
 * - no network
 */
export function verifyTrustedArtifactReference(
  jobId,
  reference
) {
  if (
    typeof jobId !== "string" ||
    !/^[A-Za-z0-9._-]{1,128}$/.test(jobId)
  ) {
    return reject(
      "INVALID_JOB_ID",
      "Invalid job ID."
    );
  }

  if (
    !reference ||
    typeof reference !== "object" ||
    Array.isArray(reference)
  ) {
    return reject(
      "TRUSTED_ARTIFACT_REFERENCE_REQUIRED",
      "Trusted artifact reference is required."
    );
  }

  if (reference.jobId !== jobId) {
    return reject(
      "TRUSTED_ARTIFACT_JOB_MISMATCH",
      "Trusted artifact reference belongs to a different job."
    );
  }

  const artifact = reference.artifact;

  if (
    !artifact ||
    typeof artifact !== "object" ||
    Array.isArray(artifact)
  ) {
    return reject(
      "TRUSTED_ARTIFACT_METADATA_INVALID",
      "Trusted artifact metadata is invalid."
    );
  }

  if (
    typeof artifact.path !== "string" ||
    !artifact.path ||
    path.isAbsolute(artifact.path) ||
    artifact.path.includes("..") ||
    artifact.path.includes("\\") ||
    /^https?:\/\//i.test(artifact.path)
  ) {
    return reject(
      "TRUSTED_ARTIFACT_PATH_INVALID",
      "Trusted artifact path must be a relative local staging path."
    );
  }

  if (!validSha256(artifact.sha256)) {
    return reject(
      "TRUSTED_ARTIFACT_HASH_INVALID",
      "Trusted artifact SHA-256 is invalid."
    );
  }

  if (!validSize(artifact.size)) {
    return reject(
      "TRUSTED_ARTIFACT_SIZE_INVALID",
      "Trusted artifact size is invalid."
    );
  }

  const routed = resolveSource(
    jobId,
    artifact.path
  );

  if (!routed.allowed) {
    return reject(
      "TRUSTED_ARTIFACT_ROUTE_BLOCKED",
      routed.message,
      {
        routeCode: routed.code
      }
    );
  }

  if (routed.size !== artifact.size) {
    return reject(
      "TRUSTED_ARTIFACT_SIZE_MISMATCH",
      "Artifact size does not match trusted reference.",
      {
        expected: artifact.size,
        actual: routed.size
      }
    );
  }

  const actualHash = sha256File(routed.path);

  if (actualHash !== artifact.sha256) {
    return reject(
      "TRUSTED_ARTIFACT_HASH_MISMATCH",
      "Artifact SHA-256 does not match trusted reference.",
      {
        expected: artifact.sha256,
        actual: actualHash
      }
    );
  }

  return {
    allowed: true,
    code: "TRUSTED_ARTIFACT_VERIFIED",
    jobId,
    path: routed.path,
    size: routed.size,
    sha256: actualHash,
    safety: {
      networkFetch: false,
      arbitraryUrlFetch: false,
      walletUsed: false,
      signing: false,
      broadcast: false
    }
  };
}
