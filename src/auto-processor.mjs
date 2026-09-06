import fs from "fs";
import path from "path";
import { execFileSync } from "child_process";
import {
  resolveSource,
  getStagingPath
} from "./source-router.mjs";

import {
  verifyManifest
} from "./artifact-manifest.mjs";

import {
  resolveExplicitOrStaged
} from "./artifact-resolver.mjs";

import {
  createTrustedArtifactReference,
  verifyTrustedArtifactReference
} from "./trusted-artifact.mjs";

const intakeFile =
  process.argv[2] || "provider-output/aacp-intake.json";

const sourceFile =
  process.argv[3] || null;

const simulation =
  process.env.PROVIDER_DAEMON_SIMULATION === "1";

const discoverStaged =
  process.env.PROVIDER_AUTO_DISCOVER_STAGED === "1";

if (!sourceFile && !simulation && !discoverStaged) {
  console.error("SOURCE_REQUIRED");
  console.error(
    "Production mode requires an explicit Solidity source/artifact unless staged discovery is enabled."
  );
  console.error(
    "Sample fallback is disabled."
  );
  process.exit(2);
}

if (!sourceFile && simulation) {
  console.error("SIMULATION_SOURCE_REQUIRED");
  console.error(
    "Simulation mode also requires an explicit source file."
  );
  process.exit(2);
}

if (!fs.existsSync(intakeFile)) {
  console.error(`Intake file not found: ${intakeFile}`);
  process.exit(1);
}

const intake = JSON.parse(
  fs.readFileSync(intakeFile, "utf8")
);

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Auto Processor v1.8.0");
console.log(" READ ONLY");
console.log("========================================");
console.log("");

console.log(
  `Backend available : ${intake.summary?.backendAvailable ?? false}`
);

console.log(
  `Jobs available    : ${intake.jobs?.length ?? 0}`
);

if (
  intake.summary?.backendAvailable === false &&
  (!intake.jobs || intake.jobs.length === 0)
) {
  console.log("");
  console.log(
    "AACP backend unavailable."
  );
  console.log(
    "No jobs will be fabricated or assumed."
  );
  console.log("");
  console.log("AUTO PROCESSOR STOPPED SAFELY");
  process.exit(0);
}

const jobs = intake.jobs || [];

const results = [];

for (const [index, job] of jobs.entries()) {
  const jobId =
    job.jobId ??
    job.id ??
    `job-${index + 1}`;

  if (
    typeof jobId !== "string" ||
    !/^[A-Za-z0-9._-]{1,128}$/.test(jobId)
  ) {
    console.error(
      `INVALID_JOB_ID: ${String(jobId)}`
    );

    results.push({
      jobId: String(jobId),
      status: "BLOCKED",
      code: "INVALID_JOB_ID"
    });

    continue;
  }

  console.log("");
  console.log(
    `[${index + 1}/${jobs.length}] Processing ${jobId}`
  );

  /*
   * Source routing:
   *
   * Production:
   *   explicit CLI source is allowed only when it resolves
   *   inside the job staging directory.
   *
   * Simulation:
   *   explicit source remains supported for deterministic tests.
   *
   * No implicit sample fallback is permitted.
   */

  let routedSource = sourceFile;

  if (simulation) {
    if (!routedSource) {
      console.error(
        `SOURCE_ARTIFACT_REQUIRED: ${jobId}`
      );

      results.push({
        jobId,
        status: "BLOCKED",
        code: "SOURCE_ARTIFACT_REQUIRED"
      });

      continue;
    }

    if (!fs.existsSync(routedSource)) {
      console.error(
        `SOURCE_REJECTED: source does not exist: ${routedSource}`
      );

      results.push({
        jobId,
        status: "BLOCKED",
        code: "SOURCE_REJECTED"
      });

      continue;
    }
  } else {
    /*
     * Production source must be staged per job.
     *
     * The CLI source is treated as a relative filename
     * inside provider-output/source-staging/<jobId>.
     */
    const jobRoot = getStagingPath(jobId);

    let requestedSource = sourceFile;

    if (requestedSource && path.isAbsolute(requestedSource)) {
      const relative = path.relative(
        jobRoot,
        path.resolve(requestedSource)
      );

      requestedSource = relative;
    }

    /*
     * Source resolution:
     *
     * Explicit source:
     *   Existing source-router path remains authoritative.
     *
     * No explicit source:
     *   Staged-manifest discovery is allowed only when
     *   PROVIDER_AUTO_DISCOVER_STAGED=1.
     *
     * Resolver discovery is local-only.
     * No URL/network fetching is permitted.
     */
    const resolution =
      resolveExplicitOrStaged(
        jobId,
        requestedSource,
        {
          allowDiscovery: discoverStaged
        }
      );

    if (!resolution.allowed) {
      console.error(
        `${resolution.code}: ${jobId}`
      );
      console.error(
        resolution.message
      );

      results.push({
        jobId,
        status: "BLOCKED",
        code: resolution.code,
        message: resolution.message
      });

      continue;
    }

    if (
      resolution.code ===
      "STAGED_MANIFEST_ARTIFACT_RESOLVED"
    ) {
      routedSource = resolution.path;

      console.log(
        `Source discovery : ${resolution.code}`
      );
      console.log(
        `Discovered source : ${resolution.relativePath}`
      );
    } else {
      const routed = resolveSource(
        jobId,
        requestedSource
      );

      if (!routed.allowed) {
        console.error(
          `${routed.code}: ${jobId}`
        );
        console.error(
          routed.message
        );

        results.push({
          jobId,
          status: "BLOCKED",
          code: routed.code,
          message: routed.message
        });

        continue;
      }

      routedSource = routed.path;
    }

    /*
     * Artifact integrity gate:
     *
     * Production processing is allowed only when
     * manifest.json exists and its:
     *   - jobId
     *   - artifact path
     *   - size
     *   - SHA-256
     *   - immutable Job metadata fingerprint
     * match the staged source and current job.
     *
     * No analysis is performed before this check.
     */
    const manifestResult =
      verifyManifest(jobId, job);

    if (!manifestResult.allowed) {
      console.error(
        `SOURCE_MANIFEST_BLOCKED: ${jobId}`
      );
      console.error(
        `${manifestResult.code}: ${manifestResult.message}`
      );

      results.push({
        jobId,
        status: "BLOCKED",
        code: manifestResult.code,
        message: manifestResult.message
      });

      continue;
    }

    console.log(
      `Manifest          : ${manifestResult.code}`
    );

    /*
     * Trusted artifact integrity gate:
     *
     * The manifest proves the staged artifact and immutable
     * Job metadata are bound together.
     *
     * Trusted Artifact verification independently confirms:
     *   - local staging path
     *   - artifact size
     *   - artifact SHA-256
     *
     * This gate MUST pass before job-processor/analyzer runs.
     *
     * No network fetch, wallet, signing, or broadcast occurs.
     */
    const trustedReference =
      createTrustedArtifactReference(
        jobId,
        path.relative(
          jobRoot,
          routedSource
        )
      );

    if (!trustedReference.allowed) {
      console.error(
        `TRUSTED_ARTIFACT_BLOCKED: ${jobId}`
      );
      console.error(
        `${trustedReference.code}: ${trustedReference.message}`
      );

      results.push({
        jobId,
        status: "BLOCKED",
        code: trustedReference.code,
        message: trustedReference.message
      });

      continue;
    }

    const trustedVerification =
      verifyTrustedArtifactReference(
        jobId,
        trustedReference.reference
      );

    if (!trustedVerification.allowed) {
      console.error(
        `TRUSTED_ARTIFACT_BLOCKED: ${jobId}`
      );
      console.error(
        `${trustedVerification.code}: ${trustedVerification.message}`
      );

      results.push({
        jobId,
        status: "BLOCKED",
        code: trustedVerification.code,
        message: trustedVerification.message
      });

      continue;
    }

    /*
     * Cross-check trusted artifact against the already
     * verified manifest. This prevents the two integrity
     * layers from silently referring to different artifacts.
     */
    const manifestArtifact =
      manifestResult.manifest?.artifact;

    const trustedArtifact =
      trustedReference.reference?.artifact;

    if (
      !manifestArtifact ||
      !trustedArtifact ||
      manifestArtifact.path !== trustedArtifact.path ||
      manifestArtifact.size !== trustedArtifact.size ||
      manifestArtifact.sha256 !== trustedArtifact.sha256
    ) {
      console.error(
        `TRUSTED_ARTIFACT_MANIFEST_MISMATCH: ${jobId}`
      );

      results.push({
        jobId,
        status: "BLOCKED",
        code: "TRUSTED_ARTIFACT_MANIFEST_MISMATCH",
        message:
          "Trusted artifact reference does not match the verified manifest."
      });

      continue;
    }

    console.log(
      `Trusted Artifact  : ${trustedVerification.code}`
    );
  }

  console.log(
    `Source            : ${routedSource}`
  );

  const tempFile = path.join(
    "/tmp",
    `termix-job-${jobId}.json`
  );

  fs.writeFileSync(
    tempFile,
    JSON.stringify(job, null, 2)
  );

  try {
    const raw = execFileSync(
      process.execPath,
      [
        "src/job-processor.mjs",
        tempFile,
        routedSource
      ],
      {
        encoding: "utf8"
      }
    );

    const outputLine =
      raw
        .split("\n")
        .find(line =>
          line.includes("Output   :")
        );

    const output =
      outputLine
        ? outputLine.split("Output   :")[1].trim()
        : null;

    results.push({
      jobId,
      status: "PROCESSED",
      output
    });

    console.log("  Status : PROCESSED");

  } catch (error) {
    results.push({
      jobId,
      status: "FAILED",
      error: error.message
    });

    console.log("  Status : FAILED");
  }

  fs.rmSync(
    tempFile,
    { force: true }
  );
}

const result = {
  processor: "TermiX Auto Processor",
  version: "1.7.0",

  intake: {
    backendAvailable:
      intake.summary?.backendAvailable ?? false,
    jobsReceived: jobs.length
  },

  results,

  execution: {
    mode: "READ_ONLY",
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false
  }
};

const outputPath =
  "provider-output/auto-processor-result.json";

fs.writeFileSync(
  outputPath,
  JSON.stringify(result, null, 2)
);

console.log("");
console.log("========================================");
console.log(" AUTO PROCESSOR COMPLETE");
console.log("========================================");
console.log("");
console.log(
  `Processed : ${results.filter(x => x.status === "PROCESSED").length}`
);
console.log(
  `Failed    : ${results.filter(x => x.status === "FAILED").length}`
);
console.log(
  `Output    : ${outputPath}`
);
console.log("");
console.log("Wallet       : NOT USED");
console.log("Signing      : NOT USED");
console.log("Submission   : NOT USED");
