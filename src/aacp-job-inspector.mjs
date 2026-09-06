import fs from "node:fs";
import path from "node:path";

const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  "provider-output/aacp-observer";

function ensureOutputDir() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  return OUTPUT_DIR;
}

function stableKeys(value) {
  if (!value || typeof value !== "object") return [];

  return Object.keys(value).sort();
}

export function inspectJobs(jobs = []) {
  return jobs.map((job) => ({
    jobId: job?.jobId ?? job?.id ?? null,
    status: job?.status ?? null,
    strategyType: job?.strategyType ?? null,
    budget: job?.budget ?? null,
    title: job?.title ?? null,
    description: job?.description ?? null,
    deadline: job?.deadline ?? null,
    providerId: job?.providerId ?? null,

    observedFields: stableKeys(job),

    artifactCandidates:
      stableKeys(job).filter((key) =>
        /artifact|source|contract|repository|repo|program|deliverable/i
          .test(key)
      )
  }));
}

export function writeSnapshot(result, outputDir = OUTPUT_DIR) {
  fs.mkdirSync(outputDir, { recursive: true });
  const dir = outputDir;

  const snapshot = {
    observer: "TermiX AACP Recovery Observer",
    version: "1.0.0",
    mode: "READ_ONLY",
    timestamp: new Date().toISOString(),

    state: result.state,
    previousState: result.previousState,
    recovered: result.recovered,

    jobs: inspectJobs(result.jobs),

    safety: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false
    }
  };

  const file = path.join(
    dir,
    "latest-job-snapshot.json"
  );

  fs.writeFileSync(
    file,
    JSON.stringify(snapshot, null, 2) + "\n"
  );

  return file;
}
