import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import {
  resolveSource,
  getStagingPath
} from "./source-router.mjs";

const MANIFEST_NAME = "manifest.json";

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

export function createManifest(jobId, requestedPath) {
  const routed = resolveSource(
    jobId,
    requestedPath
  );

  if (!routed.allowed) {
    return routed;
  }

  const jobRoot =
    getStagingPath(jobId);

  const relativePath =
    path.relative(
      jobRoot,
      routed.path
    );

  const digest =
    sha256File(routed.path);

  const manifest = {
    version: "1.0.0",

    jobId,

    artifact: {
      type:
        routed.extension === ".sol"
          ? "solidity-source"
          : "source-artifact",

      path: relativePath,

      size: routed.size,

      sha256: digest
    },

    source: {
      mode: "MANUALLY_STAGED"
    },

    safety: {
      networkFetch: false,
      walletUsed: false,
      signing: false,
      broadcast: false
    }
  };

  const manifestPath =
    path.join(
      jobRoot,
      MANIFEST_NAME
    );

  fs.writeFileSync(
    manifestPath,
    JSON.stringify(
      manifest,
      null,
      2
    )
  );

  return {
    allowed: true,
    code: "MANIFEST_CREATED",
    manifest,
    path: manifestPath
  };
}

export function verifyManifest(jobId) {
  if (
    typeof jobId !== "string" ||
    !/^[A-Za-z0-9._-]{1,128}$/.test(jobId)
  ) {
    return reject(
      "INVALID_JOB_ID",
      "Job ID is invalid."
    );
  }

  const jobRoot =
    getStagingPath(jobId);

  const manifestPath =
    path.join(
      jobRoot,
      MANIFEST_NAME
    );

  if (!fs.existsSync(manifestPath)) {
    return reject(
      "MANIFEST_REQUIRED",
      "Artifact manifest does not exist."
    );
  }

  let manifest;

  try {
    manifest =
      JSON.parse(
        fs.readFileSync(
          manifestPath,
          "utf8"
        )
      );
  } catch {
    return reject(
      "MANIFEST_INVALID",
      "Manifest is not valid JSON."
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
      "MANIFEST_INVALID",
      "Manifest artifact path is missing."
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

  if (
    manifest.artifact.size !==
    routed.size
  ) {
    return reject(
      "MANIFEST_SIZE_MISMATCH",
      "Artifact size does not match manifest."
    );
  }

  const actualHash =
    sha256File(routed.path);

  if (
    manifest.artifact.sha256 !==
    actualHash
  ) {
    return reject(
      "MANIFEST_HASH_MISMATCH",
      "Artifact SHA-256 does not match manifest.",
      {
        expected: manifest.artifact.sha256,
        actual: actualHash
      }
    );
  }

  return {
    allowed: true,
    code: "MANIFEST_VALID",
    manifest,
    artifact: routed.path
  };
}

if (
  process.argv[1] ===
  new URL(import.meta.url).pathname
) {
  const command = process.argv[2];
  const jobId = process.argv[3];
  const source = process.argv[4];

  let result;

  if (command === "create") {
    result =
      createManifest(
        jobId,
        source
      );
  } else if (command === "verify") {
    result =
      verifyManifest(
        jobId
      );
  } else {
    console.error(
      "Usage: node src/artifact-manifest.mjs <create|verify> <jobId> [source]"
    );
    process.exit(2);
  }

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
