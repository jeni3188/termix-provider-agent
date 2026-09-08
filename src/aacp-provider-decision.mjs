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

  return {
    jobId: job?.jobId ?? job?.id ?? null,
    status: String(job?.status ?? "").toUpperCase(),
    title: job?.title ?? null,
    strategyType: job?.strategyType ?? null,
    qualification:
      nested?.qualification ??
      (
        typeof job?.qualification === "string"
          ? job.qualification
          : "MANUAL_REVIEW"
      ),
    score: Number.isFinite(Number(
      nested?.score ?? job?.score ?? 0
    ))
      ? Number(nested?.score ?? job?.score ?? 0)
      : 0,
    artifact:
      nested?.artifactStatus ??
      job?.artifactStatus ??
      "NO_ARTIFACT",
    trusted:
      nested?.artifactTrusted === true ||
      job?.artifactTrusted === true
  };
}

function hasUnsafeSideEffect(safety = {}) {
  return (
    safety.postPerformed === true ||
    safety.walletUsed === true ||
    safety.signingPerformed === true ||
    safety.broadcastPerformed === true ||
    safety.submissionPerformed === true
  );
}

function isQualified(job) {
  return (
    job.qualification === "STRONG_MATCH" &&
    job.trusted === true &&
    job.artifact === "TRUSTED_ARTIFACT"
  );
}

export function decideProvider({
  state = "UNKNOWN",
  jobs = [],
  safety = READ_ONLY_SAFETY
} = {}) {
  if (state === "BACKEND_UNAVAILABLE") {
    return {
      decision: "BACKEND_UNAVAILABLE",
      reason: "Backend is unavailable.",
      job: null
    };
  }

  if (hasUnsafeSideEffect(safety)) {
    return {
      decision: "BLOCKED",
      reason: "Unsafe side-effect state detected.",
      job: null
    };
  }

  if (state !== "HEALTHY") {
    return {
      decision: "BLOCKED",
      reason: "Provider state is not HEALTHY.",
      job: null
    };
  }

  if (!Array.isArray(jobs) || jobs.length === 0) {
    return {
      decision: "NO_MATCH",
      reason: "No observable jobs are available.",
      job: null
    };
  }

  const normalized = jobs
    .map(normalizeJob)
    .filter(job => job.jobId);

  const qualified = normalized.find(isQualified);

  if (qualified) {
    return {
      decision: "QUALIFIED",
      reason:
        "Job satisfies STRONG_MATCH and trusted artifact requirements.",
      job: qualified
    };
  }

  return {
    decision: "BLOCKED",
    reason:
      "No job satisfies all provider qualification requirements.",
    job: null
  };
}

export function buildProviderDecision(input = {}) {
  const decision = decideProvider(input);

  return {
    observer: "TermiX AACP Provider Decision",
    version: "1.0.0",
    mode: "READ_ONLY",

    state: input.state ?? "UNKNOWN",

    decision: decision.decision,
    reason: decision.reason,
    job: decision.job,

    safety: {
      postPerformed:
        input.safety?.postPerformed === true,
      walletUsed:
        input.safety?.walletUsed === true,
      signingPerformed:
        input.safety?.signingPerformed === true,
      broadcastPerformed:
        input.safety?.broadcastPerformed === true,
      submissionPerformed:
        input.safety?.submissionPerformed === true
    }
  };
}

export function writeProviderDecision(
  input,
  outputDir = DEFAULT_OUTPUT_DIR
) {
  const decision = buildProviderDecision(input);

  fs.mkdirSync(outputDir, { recursive: true });

  const file = path.join(
    outputDir,
    "latest-provider-decision.json"
  );

  fs.writeFileSync(
    file,
    JSON.stringify(decision, null, 2) + "\n"
  );

  return {
    file,
    decision
  };
}

async function main() {
  console.log(
    "TERMiX AACP PROVIDER DECISION v1.0"
  );
  console.log(
    "READ ONLY / FAIL CLOSED"
  );
  console.log(
    "No remote action is performed by this module."
  );
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) ===
    path.resolve(
      new URL(import.meta.url).pathname
    )
) {
  await main();
}
