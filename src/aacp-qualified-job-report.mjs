const READ_ONLY_SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false
};

function normalizeJob(job) {
  const q = job?.qualification ?? {};

  return {
    jobId: job?.jobId ?? job?.id ?? null,
    status: job?.status ?? null,
    strategyType: job?.strategyType ?? null,
    title: job?.title ?? null,
    description: job?.description ?? null,
    budget: job?.budget ?? null,

    qualification: q.qualification ?? "MANUAL_REVIEW",
    score: Number.isFinite(Number(q.score))
      ? Number(q.score)
      : 0,

    artifact: q.artifactStatus ?? "NO_ARTIFACT",
    trusted: q.artifactTrusted === true
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
