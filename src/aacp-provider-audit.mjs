import fs from "node:fs";
import path from "node:path";

const DEFAULT_OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  "provider-output/aacp-observer";

const FILES = {
  status: path.join(
    DEFAULT_OUTPUT_DIR,
    "latest-provider-status.json"
  ),
  qualification: path.join(
    DEFAULT_OUTPUT_DIR,
    "latest-provider-qualification.json"
  ),
  decision: path.join(
    DEFAULT_OUTPUT_DIR,
    "latest-provider-decision.json"
  ),
  preflight: path.join(
    DEFAULT_OUTPUT_DIR,
    "latest-provider-preflight.json"
  )
};

const SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false
};

function readJson(file) {
  if (!fs.existsSync(file)) {
    return {
      exists: false,
      value: null,
      error: "FILE_MISSING"
    };
  }

  try {
    return {
      exists: true,
      value: JSON.parse(
        fs.readFileSync(file, "utf8")
      ),
      error: null
    };
  } catch (err) {
    return {
      exists: true,
      value: null,
      error: `INVALID_JSON: ${err.message}`
    };
  }
}

function unsafe(value = {}) {
  return (
    value.postPerformed === true ||
    value.walletUsed === true ||
    value.signingPerformed === true ||
    value.broadcastPerformed === true ||
    value.submissionPerformed === true
  );
}

export function buildProviderAudit({
  status,
  qualification,
  decision,
  preflight
}) {
  const sources = {
    status,
    qualification,
    decision,
    preflight
  };

  const sourceErrors = Object.entries(sources)
    .filter(([, item]) => item.error)
    .map(([name, item]) => ({
      source: name,
      error: item.error
    }));

  const values = Object.fromEntries(
    Object.entries(sources).map(
      ([name, item]) => [name, item.value]
    )
  );

  const allSafety = [
    values.status?.safety,
    values.qualification?.safety,
    values.decision?.safety,
    values.preflight?.safety
  ];

  const unsafeDetected =
    allSafety.some(unsafe);

  let auditState = "BLOCKED";
  let reason =
    "Provider audit is fail-closed.";

  if (sourceErrors.length > 0) {
    auditState = "INCOMPLETE";
    reason =
      "One or more provider reports are missing or invalid.";
  } else if (unsafeDetected) {
    auditState = "BLOCKED";
    reason =
      "Unsafe side-effect state detected.";
  } else if (
    values.preflight?.preflight ===
    "BACKEND_UNAVAILABLE"
  ) {
    auditState = "BACKEND_UNAVAILABLE";
    reason =
      "Backend is unavailable.";
  } else if (
    values.preflight?.preflight ===
    "READY_READ_ONLY"
  ) {
    auditState = "READY_READ_ONLY";
    reason =
      "All provider reports passed read-only audit gates.";
  }

  return {
    observer:
      "TermiX AACP Provider Audit",
    version: "1.0.0",

    mode: "READ_ONLY",

    auditState,
    reason,

    executionAuthorized: false,

    sources: {
      status: {
        exists: status.exists,
        error: status.error
      },
      qualification: {
        exists: qualification.exists,
        error: qualification.error
      },
      decision: {
        exists: decision.exists,
        error: decision.error
      },
      preflight: {
        exists: preflight.exists,
        error: preflight.error
      }
    },

    provider: {
      state:
        values.decision?.state ??
        values.status?.state ??
        "UNKNOWN",

      decision:
        values.decision?.decision ??
        "UNKNOWN",

      preflight:
        values.preflight?.preflight ??
        "UNKNOWN",

      job:
        values.preflight?.job ??
        values.decision?.job ??
        null
    },

    safety: SAFETY,

    unsafeDetected,

    sideEffects: {
      post: false,
      wallet: false,
      signing: false,
      broadcast: false,
      submission: false
    }
  };
}

export function runProviderAudit({
  outputDir = DEFAULT_OUTPUT_DIR
} = {}) {
  const files = {
    status: path.join(
      outputDir,
      "latest-provider-status.json"
    ),
    qualification: path.join(
      outputDir,
      "latest-provider-qualification.json"
    ),
    decision: path.join(
      outputDir,
      "latest-provider-decision.json"
    ),
    preflight: path.join(
      outputDir,
      "latest-provider-preflight.json"
    )
  };

  const report = buildProviderAudit({
    status: readJson(files.status),
    qualification:
      readJson(files.qualification),
    decision:
      readJson(files.decision),
    preflight:
      readJson(files.preflight)
  });

  fs.mkdirSync(
    outputDir,
    { recursive: true }
  );

  const file = path.join(
    outputDir,
    "latest-provider-audit.json"
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

async function main() {
  const result =
    runProviderAudit();

  console.log(
    "TERMiX AACP PROVIDER AUDIT v1.0"
  );

  console.log(
    "READ ONLY / FAIL CLOSED"
  );

  console.log(
    `AUDIT=${result.report.auditState}`
  );

  console.log(
    `REASON=${result.report.reason}`
  );

  console.log(
    `STATE=${result.report.provider.state}`
  );

  console.log(
    `DECISION=${result.report.provider.decision}`
  );

  console.log(
    `PREFLIGHT=${result.report.provider.preflight}`
  );

  console.log(
    `JOB=${result.report.provider.job?.jobId ?? "NONE"}`
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
