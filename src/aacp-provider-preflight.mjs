import fs from "node:fs";
import path from "node:path";

const DEFAULT_OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  "provider-output/aacp-observer";

const DEFAULT_DECISION_FILE = path.join(
  DEFAULT_OUTPUT_DIR,
  "latest-provider-decision.json"
);

const READ_ONLY_SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false
};

function hasUnsafeSideEffect(safety = {}) {
  return (
    safety.postPerformed === true ||
    safety.walletUsed === true ||
    safety.signingPerformed === true ||
    safety.broadcastPerformed === true ||
    safety.submissionPerformed === true
  );
}

export function preflightProviderDecision(decision) {
  if (!decision || typeof decision !== "object") {
    return {
      preflight: "BLOCKED",
      reason: "Provider decision is missing or invalid.",
      job: null
    };
  }

  if (decision.mode !== "READ_ONLY") {
    return {
      preflight: "BLOCKED",
      reason: "Provider decision mode is not READ_ONLY.",
      job: null
    };
  }

  if (decision.state === "BACKEND_UNAVAILABLE") {
    return {
      preflight: "BACKEND_UNAVAILABLE",
      reason:
        "Backend is unavailable; preflight cannot authorize work.",
      job: null
    };
  }

  if (hasUnsafeSideEffect(decision.safety)) {
    return {
      preflight: "BLOCKED",
      reason: "Unsafe side-effect state detected.",
      job: null
    };
  }

  if (decision.state !== "HEALTHY") {
    return {
      preflight: "BLOCKED",
      reason: "Provider state is not HEALTHY.",
      job: null
    };
  }

  if (decision.decision !== "QUALIFIED") {
    return {
      preflight: "BLOCKED",
      reason: "Provider decision is not QUALIFIED.",
      job: null
    };
  }

  const job = decision.job;

  if (!job || !job.jobId) {
    return {
      preflight: "BLOCKED",
      reason:
        "Qualified provider decision has no job binding.",
      job: null
    };
  }

  if (job.qualification !== "STRONG_MATCH") {
    return {
      preflight: "BLOCKED",
      reason: "Bound job is not STRONG_MATCH.",
      job: null
    };
  }

  if (
    job.trusted !== true ||
    job.artifact !== "TRUSTED_ARTIFACT"
  ) {
    return {
      preflight: "BLOCKED",
      reason:
        "Bound job does not have a trusted artifact.",
      job: null
    };
  }

  return {
    preflight: "READY_READ_ONLY",
    reason:
      "Provider decision passed all read-only preflight gates. No execution is authorized.",
    job
  };
}

export function buildProviderPreflight(decision) {
  const result =
    preflightProviderDecision(decision);

  return {
    observer:
      "TermiX AACP Provider Preflight",
    version: "1.0.0",
    mode: "READ_ONLY",

    state:
      decision?.state ?? "UNKNOWN",

    decision:
      decision?.decision ?? "UNKNOWN",

    preflight:
      result.preflight,

    reason:
      result.reason,

    job:
      result.job,

    executionAuthorized: false,

    safety: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false
    }
  };
}

export function writeProviderPreflight(
  decision,
  outputDir = DEFAULT_OUTPUT_DIR
) {
  const report =
    buildProviderPreflight(decision);

  fs.mkdirSync(
    outputDir,
    { recursive: true }
  );

  const file = path.join(
    outputDir,
    "latest-provider-preflight.json"
  );

  fs.writeFileSync(
    file,
    JSON.stringify(report, null, 2) +
      "\n"
  );

  return {
    file,
    report
  };
}

export function runProviderPreflight({
  decisionFile = DEFAULT_DECISION_FILE,
  outputDir = DEFAULT_OUTPUT_DIR
} = {}) {
  if (!fs.existsSync(decisionFile)) {
    const report = {
      observer:
        "TermiX AACP Provider Preflight",
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "UNKNOWN",
      decision: "UNKNOWN",
      preflight: "BLOCKED",
      reason:
        "Provider decision file is missing.",
      job: null,
      executionAuthorized: false,
      safety: READ_ONLY_SAFETY
    };

    fs.mkdirSync(
      outputDir,
      { recursive: true }
    );

    const file = path.join(
      outputDir,
      "latest-provider-preflight.json"
    );

    fs.writeFileSync(
      file,
      JSON.stringify(report, null, 2) +
        "\n"
    );

    return {
      file,
      report
    };
  }

  let decision;

  try {
    decision = JSON.parse(
      fs.readFileSync(
        decisionFile,
        "utf8"
      )
    );
  } catch (err) {
    const report = {
      observer:
        "TermiX AACP Provider Preflight",
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "UNKNOWN",
      decision: "UNKNOWN",
      preflight: "BLOCKED",
      reason:
        `Invalid provider decision: ${err.message}`,
      job: null,
      executionAuthorized: false,
      safety: READ_ONLY_SAFETY
    };

    fs.mkdirSync(
      outputDir,
      { recursive: true }
    );

    const file = path.join(
      outputDir,
      "latest-provider-preflight.json"
    );

    fs.writeFileSync(
      file,
      JSON.stringify(report, null, 2) +
        "\n"
    );

    return {
      file,
      report
    };
  }

  return writeProviderPreflight(
    decision,
    outputDir
  );
}

async function main() {
  const result =
    runProviderPreflight();

  console.log(
    "TERMiX AACP PROVIDER PREFLIGHT v1.0"
  );

  console.log(
    "READ ONLY / FAIL CLOSED"
  );

  console.log(
    `PREFLIGHT=${result.report.preflight}`
  );

  console.log(
    `REASON=${result.report.reason}`
  );

  console.log(
    `JOB=${result.report.job?.jobId ?? "NONE"}`
  );

  console.log(
    "EXECUTION_AUTHORIZED=false"
  );

  console.log(
    "POST=NOT_PERFORMED"
  );

  console.log(
    "WALLET=NOT_USED"
  );

  console.log(
    "SIGNING=NOT_PERFORMED"
  );

  console.log(
    "BROADCAST=NOT_PERFORMED"
  );

  console.log(
    "SUBMISSION=NOT_PERFORMED"
  );

  console.log(
    `REPORT=${result.file}`
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
