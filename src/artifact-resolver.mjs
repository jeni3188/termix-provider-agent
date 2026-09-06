import fs from "node:fs";
import path from "node:path";
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

export function resolveStagedManifestArtifact(jobId) {
  if (
    typeof jobId !== "string" ||
    !/^[A-Za-z0-9._-]{1,128}$/.test(jobId)
  ) {
    return reject(
      "INVALID_JOB_ID",
      "Job ID is invalid."
    );
  }

  const jobRoot = getStagingPath(jobId);
  const manifestPath = path.join(
    jobRoot,
    "manifest.json"
  );

  if (!fs.existsSync(manifestPath)) {
    return reject(
      "MANIFEST_REQUIRED",
      "Artifact manifest does not exist."
    );
  }

  let manifest;

  try {
    manifest = JSON.parse(
      fs.readFileSync(manifestPath, "utf8")
    );
  } catch {
    return reject(
      "MANIFEST_INVALID",
      "Artifact manifest is not valid JSON."
    );
  }

  if (
    !manifest ||
    typeof manifest !== "object" ||
    Array.isArray(manifest)
  ) {
    return reject(
      "MANIFEST_INVALID",
      "Artifact manifest must be an object."
    );
  }

  if (manifest.jobId !== jobId) {
    return reject(
      "MANIFEST_JOB_MISMATCH",
      "Manifest Job ID does not match."
    );
  }

  const artifactPath =
    manifest.artifact?.path;

  if (
    typeof artifactPath !== "string" ||
    artifactPath.trim() === ""
  ) {
    return reject(
      "MANIFEST_ARTIFACT_REQUIRED",
      "Manifest does not specify an artifact path."
    );
  }

  const routed =
    resolveSource(
      jobId,
      artifactPath
    );

  if (!routed.allowed) {
    return reject(
      "MANIFEST_ARTIFACT_REJECTED",
      routed.message,
      {
        routerCode: routed.code
      }
    );
  }

  return {
    allowed: true,
    code: "STAGED_MANIFEST_ARTIFACT_RESOLVED",
    jobId,
    path: routed.path,
    relativePath: path.relative(
      jobRoot,
      routed.path
    ),
    manifestPath,
    manifest
  };
}

export function resolveExplicitOrStaged(
  jobId,
  requestedSource,
  {
    allowDiscovery = false
  } = {}
) {
  if (
    typeof requestedSource === "string" &&
    requestedSource.trim() !== ""
  ) {
    return {
      allowed: true,
      code: "EXPLICIT_SOURCE_REQUESTED",
      requestedSource
    };
  }

  if (!allowDiscovery) {
    return reject(
      "SOURCE_REQUIRED",
      "Explicit source/artifact is required unless staged-manifest discovery is enabled."
    );
  }

  return resolveStagedManifestArtifact(jobId);
}
