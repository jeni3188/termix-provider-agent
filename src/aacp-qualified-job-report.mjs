import fs from "node:fs";
import path from "node:path";

const DEFAULT_OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  "provider-output/aacp-observer";

const READ_ONLY_SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false
};

function normalizeJob(job) {
  const nested =
    job?.qualification &&
    typeof job.qualification === "object"
      ? job.qualification
      : null;

  const qualification =
    nested?.qualification ??
    (
      typeof job?.qualification === "string"
        ? job.qualification
        : "MANUAL_REVIEW"
    );

  const score =
    nested?.score ??
    job?.score ??
    0;

  const artifact =
    nested?.artifactStatus ??
    job?.artifactStatus ??
    "NO_ARTIFACT";

  const trusted =
    nested?.artifactTrusted === true ||
    job?.artifactTrusted === true;

  return {
    jobId: job?.jobId ?? job?.id ?? null,
    status: job?.status ?? null,
    strategyType: job?.strategyType ?? null,
    title: job?.title ?? null,
    description: job?.description ?? null,
    budget: job?.budget ?? null,

    qualification,
    score: Number.isFinite(Number(score))
      ? Number(score)
      : 0,

    artifact,
    trusted
  };
}

function isQualified(job) {
  return (
    job.qualification === "STRONG_MATCH" &&
    job.trusted === true &&
    job.artifact === "TRUSTED_ARTIFACT"
  );
}

export function buildQualifiedJobReport({
  state = "UNKNOWN",
  previousState = null,
  recovered = false,
  jobs = [],
  safety = READ_ONLY_SAFETY
} = {}) {
  const normalized = jobs.map(normalizeJob);

  const unique = [];
  const seen = new Set();

  for (const job of normalized) {
    if (!job.jobId) continue;

    if (seen.has(job.jobId)) continue;

    seen.add(job.jobId);
    unique.push(job);
  }

  const qualified = unique
    .filter(isQualified)
    .map(job => ({
      jobId: job.jobId,
      status: job.status,
      strategyType: job.strategyType,
      title: job.title,
      score: job.score,
      qualification: job.qualification,
      artifact: job.artifact,
      trusted: job.trusted,
      analyzer: "ELIGIBLE"
    }));

  const blocked = unique
    .filter(job => !isQualified(job))
    .map(job => ({
      jobId: job.jobId,
      status: job.status,
      strategyType: job.strategyType,
      title: job.title,
      score: job.score,
      reason: job.qualification,
      artifact: job.artifact,
      trusted: job.trusted,
      analyzer: "BLOCKED"
    }));

  return {
    observer: "TermiX AACP Qualified Job Report",
    version: "3.0.0",
    mode: "READ_ONLY",

    state,
    previousState,
    recovered,

    summary: {
      observed: normalized.length,
      unique: unique.length,
      qualified: qualified.length,
      blocked: blocked.length
    },

    qualified,
    blocked,

    safety: {
      postPerformed: safety.postPerformed === true,
      walletUsed: safety.walletUsed === true,
      signingPerformed: safety.signingPerformed === true,
      broadcastPerformed: safety.broadcastPerformed === true,
      submissionPerformed: safety.submissionPerformed === true
    }
  };
}


export function writeQualifiedJobReport(
  input,
  outputDir = DEFAULT_OUTPUT_DIR
) {
  const report = buildQualifiedJobReport(input);

  fs.mkdirSync(outputDir, { recursive: true });

  const file = path.join(
    outputDir,
    "latest-qualified-job-report.json"
  );

  fs.writeFileSync(
    file,
    JSON.stringify(report, null, 2) + "\n"
  );

  return {
    file,
    report
  };
}
