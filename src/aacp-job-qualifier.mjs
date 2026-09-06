import fs from "node:fs";
import path from "node:path";

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

const ARTIFACT_TERMS = [
  "artifact",
  "source",
  "contract",
  "solidity",
  "repository",
  "repo",
  "program"
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
  return SECURITY_TERMS.some(term => text.includes(term));
}

function hasArtifactReference(job) {
  const fields =
    job?.observedFields ||
    Object.keys(job || {});

  return fields.some(field =>
    ARTIFACT_TERMS.some(term =>
      field.toLowerCase().includes(term)
    )
  );
}

function hasExplicitArtifact(job) {
  return Boolean(
    job?.artifact ||
    job?.artifactPath ||
    job?.source ||
    job?.sourceFile ||
    job?.contract ||
    job?.repository ||
    job?.repo
  );
}

function budgetUSDC(job) {
  const value = Number(job?.budget);

  if (!Number.isFinite(value) || value <= 0) {
    return 0;
  }

  return value / 1e6;
}

function classify(job) {
  if (!job || typeof job !== "object") {
    return {
      qualification: "INVALID_JOB",
      score: 0,
      reasons: ["Invalid job object"]
    };
  }

  const reasons = [];
  let score = 0;

  const status = String(job.status || "").toUpperCase();

  if (!["OPEN", "FUNDED"].includes(status)) {
    return {
      qualification: "INELIGIBLE_STATUS",
      score: 0,
      reasons: [`Status ${status || "UNKNOWN"} is not OPEN/FUNDED`]
    };
  }

  if (hasSecurityMatch(job)) {
    score += 50;
    reasons.push("Security capability match");
  } else {
    reasons.push("No security capability match");
  }

  const strategy = String(job.strategyType || "").toUpperCase();

  if (strategy === "PROGRAM") {
    score += 15;
    reasons.push("PROGRAM strategy");
  }

  const budget = budgetUSDC(job);

  if (budget >= 100) {
    score += 20;
    reasons.push(`Budget ${budget} USDC is actionable`);
  } else if (budget > 0) {
    score += 5;
    reasons.push(`Budget ${budget} USDC is limited`);
  } else {
    reasons.push("Budget unavailable");
  }

  const artifact =
    hasExplicitArtifact(job) ||
    hasArtifactReference(job);

  if (artifact) {
    score += 15;
    reasons.push("Artifact/source reference detected");
  } else {
    reasons.push("Artifact/source not present in job metadata");
  }

  let qualification;

  if (!hasSecurityMatch(job)) {
    qualification = "POOR_MATCH";
  } else if (!artifact && score >= 50) {
    qualification = "ARTIFACT_MISSING";
  } else if (score >= 80) {
    qualification = "STRONG_MATCH";
  } else if (score >= 60) {
    qualification = "GOOD_MATCH";
  } else {
    qualification = "MANUAL_REVIEW";
  }

  return {
    qualification,
    score,
    reasons,
    budgetUSDC: budget,
    artifactAvailable: artifact
  };
}

export function qualifyJobs(jobs = []) {
  return jobs.map(job => ({
    jobId: job?.jobId ?? job?.id ?? null,
    status: job?.status ?? null,
    strategyType: job?.strategyType ?? null,
    title: job?.title ?? null,
    budget: job?.budget ?? null,
    ...classify(job)
  }));
}

export function writeQualification(
  jobs,
  outputDir = DEFAULT_OUTPUT_DIR
) {
  fs.mkdirSync(outputDir, { recursive: true });

  const results = qualifyJobs(jobs);

  const summary = {
    total: results.length,
    strongMatch: results.filter(
      x => x.qualification === "STRONG_MATCH"
    ).length,
    goodMatch: results.filter(
      x => x.qualification === "GOOD_MATCH"
    ).length,
    manualReview: results.filter(
      x => x.qualification === "MANUAL_REVIEW"
    ).length,
    artifactMissing: results.filter(
      x => x.qualification === "ARTIFACT_MISSING"
    ).length,
    poorMatch: results.filter(
      x => x.qualification === "POOR_MATCH"
    ).length
  };

  const output = {
    qualifier: "TermiX AACP Job Qualifier",
    version: "1.0.0",
    mode: "READ_ONLY",
    timestamp: new Date().toISOString(),
    jobs: results,
    summary,
    safety: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false
    }
  };

  const file = path.join(
    outputDir,
    "latest-job-qualification.json"
  );

  fs.writeFileSync(
    file,
    JSON.stringify(output, null, 2) + "\n"
  );

  return {
    file,
    output
  };
}
