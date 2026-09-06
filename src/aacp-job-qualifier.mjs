import fs from "node:fs";
import path from "node:path";

import {
  verifyManifest
} from "./artifact-manifest.mjs";

import {
  verifyTrustedArtifactReference
} from "./trusted-artifact.mjs";

const DEFAULT_OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  "provider-output/aacp-observer";

const SECURITY_TERMS = [
  "security",
  "audit",
  "smart contract",
  "solidity",
  "evm",
  "reentrancy",
  "access control",
  "vulnerability",
  "static analysis",
  "on-chain"
];

function textOf(job) {
  return [
    job?.title,
    job?.description,
    job?.strategyType
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function hasSecurityMatch(job) {
  const text = textOf(job);

  return SECURITY_TERMS.some(term =>
    text.includes(term)
  );
}

function budgetUSDC(job) {
  const value = Number(job?.budget);

  if (!Number.isFinite(value) || value <= 0) {
    return 0;
  }

  return value / 1e6;
}

function resolveTrustedArtifact(job) {
  const jobId =
    job?.jobId ??
    job?.id ??
    null;

  if (
    typeof jobId !== "string" ||
    !jobId
  ) {
    return {
      status: "NO_ARTIFACT",
      trusted: false,
      reason: "Job ID is unavailable."
    };
  }

  const jobRoot =
    path.resolve(
      "provider-output",
      "source-staging",
      jobId
    );

  const manifestPath =
    path.join(
      jobRoot,
      "manifest.json"
    );

  if (!fs.existsSync(manifestPath)) {
    return {
      status: "NO_ARTIFACT",
      trusted: false,
      reason: "No local artifact manifest exists."
    };
  }

  const manifest =
    verifyManifest(
      jobId,
      job
    );

  if (!manifest.allowed) {
    return {
      status: "ARTIFACT_REFERENCE_ONLY",
      trusted: false,
      reason:
        `Manifest verification failed: ${manifest.code}`,
      code: manifest.code
    };
  }

  const reference = {
    version: "1.0.0",
    jobId,
    source: {
      mode: "LOCAL_STAGING_ONLY"
    },
    artifact: {
      path: manifest.manifest?.artifact?.path,
      size: manifest.manifest?.artifact?.size,
      sha256: manifest.manifest?.artifact?.sha256
    }
  };

  const trusted =
    verifyTrustedArtifactReference(
      jobId,
      reference
    );

  if (!trusted.allowed) {
    return {
      status: "ARTIFACT_REFERENCE_ONLY",
      trusted: false,
      reason:
        `Trusted artifact verification failed: ${trusted.code}`,
      code: trusted.code
    };
  }

  return {
    status: "TRUSTED_ARTIFACT",
    trusted: true,
    reason:
      "Manifest, SHA-256 and job binding are verified.",
    code: trusted.code,
    path: trusted.path,
    size: trusted.size,
    sha256: trusted.sha256
  };
}

function classify(job) {
  if (!job || typeof job !== "object") {
    return {
      qualification: "INVALID_JOB",
      score: 0,
      reasons: ["Invalid job object"],
      artifactStatus: "NO_ARTIFACT",
      artifactTrusted: false
    };
  }

  const reasons = [];
  let score = 0;

  const status =
    String(job.status || "").toUpperCase();

  if (!["OPEN", "FUNDED"].includes(status)) {
    return {
      qualification: "INELIGIBLE_STATUS",
      score: 0,
      reasons: [
        `Status ${status || "UNKNOWN"} is not OPEN/FUNDED`
      ],
      artifactStatus: "NO_ARTIFACT",
      artifactTrusted: false
    };
  }

  const securityMatch =
    hasSecurityMatch(job);

  if (securityMatch) {
    score += 50;
    reasons.push("Security capability match");
  } else {
    reasons.push(
      "No security capability match"
    );
  }

  const strategy =
    String(
      job.strategyType || ""
    ).toUpperCase();

  if (strategy === "PROGRAM") {
    score += 15;
    reasons.push("PROGRAM strategy");
  }

  const budget =
    budgetUSDC(job);

  if (budget >= 100) {
    score += 20;
    reasons.push(
      `Budget ${budget} USDC is actionable`
    );
  } else if (budget > 0) {
    score += 5;
    reasons.push(
      `Budget ${budget} USDC is limited`
    );
  } else {
    reasons.push("Budget unavailable");
  }

  /*
   * IMPORTANT:
   * Metadata fields such as source/artifact/repo
   * are NOT trusted artifact evidence.
   *
   * Trust is established only through:
   *   manifest verification
   *   job binding verification
   *   SHA-256 verification
   *   trusted artifact verification
   */
  const artifact =
    resolveTrustedArtifact(job);

  if (artifact.trusted) {
    score += 15;

    reasons.push(
      "Trusted local artifact verified"
    );
  } else if (
    artifact.status ===
    "ARTIFACT_REFERENCE_ONLY"
  ) {
    reasons.push(
      "Artifact reference exists but trusted verification failed"
    );
  } else {
    reasons.push(
      "No trusted local artifact available"
    );
  }

  let qualification;

  if (!securityMatch) {
    qualification = "POOR_MATCH";
  } else if (
    artifact.status === "NO_ARTIFACT"
  ) {
    qualification = "ARTIFACT_MISSING";
  } else if (
    artifact.status ===
    "ARTIFACT_REFERENCE_ONLY"
  ) {
    qualification = "ARTIFACT_UNTRUSTED";
  } else if (
    artifact.trusted &&
    score >= 80
  ) {
    qualification = "STRONG_MATCH";
  } else if (
    artifact.trusted &&
    score >= 60
  ) {
    qualification = "GOOD_MATCH";
  } else {
    qualification = "MANUAL_REVIEW";
  }

  return {
    qualification,
    score,
    reasons,
    budgetUSDC: budget,

    artifactStatus:
      artifact.status,

    artifactTrusted:
      artifact.trusted,

    artifactCode:
      artifact.code ?? null,

    artifactPath:
      artifact.path ?? null,

    artifactSize:
      artifact.size ?? null,

    artifactSha256:
      artifact.sha256 ?? null
  };
}

export function qualifyJobs(jobs = []) {
  return jobs.map(job => ({
    jobId:
      job?.jobId ??
      job?.id ??
      null,

    status:
      job?.status ??
      null,

    strategyType:
      job?.strategyType ??
      null,

    title:
      job?.title ??
      null,

    budget:
      job?.budget ??
      null,

    ...classify(job)
  }));
}

export function writeQualification(
  jobs,
  outputDir = DEFAULT_OUTPUT_DIR
) {
  fs.mkdirSync(
    outputDir,
    { recursive: true }
  );

  const results =
    qualifyJobs(jobs);

  const summary = {
    total: results.length,

    strongMatch:
      results.filter(
        x =>
          x.qualification ===
          "STRONG_MATCH"
      ).length,

    goodMatch:
      results.filter(
        x =>
          x.qualification ===
          "GOOD_MATCH"
      ).length,

    manualReview:
      results.filter(
        x =>
          x.qualification ===
          "MANUAL_REVIEW"
      ).length,

    artifactMissing:
      results.filter(
        x =>
          x.qualification ===
          "ARTIFACT_MISSING"
      ).length,

    artifactUntrusted:
      results.filter(
        x =>
          x.qualification ===
          "ARTIFACT_UNTRUSTED"
      ).length,

    poorMatch:
      results.filter(
        x =>
          x.qualification ===
          "POOR_MATCH"
      ).length
  };

  const output = {
    qualifier:
      "TermiX AACP Job Qualifier",

    version:
      "2.0.0",

    mode:
      "READ_ONLY",

    artifactTrust:
      "MANIFEST_SHA256_JOB_BINDING",

    timestamp:
      new Date().toISOString(),

    jobs:
      results,

    summary,

    safety: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false
    }
  };

  const file =
    path.join(
      outputDir,
      "latest-job-qualification.json"
    );

  fs.writeFileSync(
    file,
    JSON.stringify(
      output,
      null,
      2
    ) + "\n"
  );

  return {
    file,
    output
  };
}
