import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const DEFAULT_OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  "provider-output/aacp-observer";

const REPORT_NAMES = [
  "latest-provider-status.json",
  "latest-provider-qualification.json",
  "latest-provider-decision.json",
  "latest-provider-preflight.json",
  "latest-provider-audit.json"
];

const SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false
};

function sha256File(file) {
  const hash = crypto.createHash("sha256");

  hash.update(
    fs.readFileSync(file)
  );

  return hash.digest("hex");
}

function inspectFile(file) {
  if (!fs.existsSync(file)) {
    return {
      exists: false,
      size: 0,
      sha256: null
    };
  }

  const stat = fs.statSync(file);

  return {
    exists: true,
    size: stat.size,
    sha256: sha256File(file)
  };
}

function readAudit(outputDir) {
  const file = path.join(
    outputDir,
    "latest-provider-audit.json"
  );

  if (!fs.existsSync(file)) {
    return {
      exists: false,
      value: null,
      error: "AUDIT_FILE_MISSING"
    };
  }

  try {
    return {
      exists: true,
      value: JSON.parse(
        fs.readFileSync(
          file,
          "utf8"
        )
      ),
      error: null
    };
  } catch (err) {
    return {
      exists: true,
      value: null,
      error:
        `AUDIT_INVALID_JSON: ${err.message}`
    };
  }
}

export function buildProviderEvidence(
  outputDir = DEFAULT_OUTPUT_DIR
) {
  const reports = {};

  for (const name of REPORT_NAMES) {
    reports[name] = inspectFile(
      path.join(outputDir, name)
    );
  }

  const existing =
    Object.values(reports)
      .filter(
        (item) => item.exists
      );

  const missing =
    Object.entries(reports)
      .filter(
        ([, item]) => !item.exists
      )
      .map(
        ([name]) => name
      );

  const audit =
    readAudit(outputDir);

  let evidenceState =
    "INCOMPLETE";

  let reason =
    "Evidence snapshot is incomplete.";

  if (audit.error) {
    evidenceState =
      "INCOMPLETE";

    reason =
      "Audit report is missing or invalid.";
  } else if (
    audit.value?.mode !==
    "READ_ONLY"
  ) {
    evidenceState =
      "BLOCKED";

    reason =
      "Audit report is not READ_ONLY.";
  } else if (
    audit.value?.executionAuthorized !==
    false
  ) {
    evidenceState =
      "BLOCKED";

    reason =
      "Audit report does not explicitly deny execution.";
  } else if (
    audit.value?.unsafeDetected ===
    true
  ) {
    evidenceState =
      "BLOCKED";

    reason =
      "Audit report detected unsafe side effects.";
  } else if (
    audit.value?.auditState ===
    "BACKEND_UNAVAILABLE"
  ) {
    evidenceState =
      "BACKEND_UNAVAILABLE";

    reason =
      "Audit report indicates backend is unavailable.";
  } else if (
    audit.value?.auditState ===
    "INCOMPLETE"
  ) {
    evidenceState =
      "INCOMPLETE";

    reason =
      "Audit report is incomplete.";
  } else if (
    audit.value?.auditState !==
    "READY_READ_ONLY"
  ) {
    evidenceState =
      "BLOCKED";

    reason =
      "Audit report is not READY_READ_ONLY.";
  } else if (
    existing.length ===
    REPORT_NAMES.length
  ) {
    evidenceState =
      "COMPLETE";

    reason =
      "All provider reports are present and audit binding is valid.";
  }

  return {
    observer:
      "TermiX AACP Provider Evidence",

    version:
      "1.1.0",

    mode:
      "READ_ONLY",

    evidenceState,

    reason,

    generatedAt:
      new Date().toISOString(),

    auditBinding: {
      auditExists:
        audit.exists,

      auditSha256:
        reports[
          "latest-provider-audit.json"
        ]?.sha256 ??
        null,

      auditState:
        audit.value?.auditState ??
        "UNKNOWN",

      executionAuthorized:
        false
    },

    reports,

    summary: {
      totalReports:
        REPORT_NAMES.length,

      existingReports:
        existing.length,

      missingReports:
        missing.length,

      missing
    },

    executionAuthorized:
      false,

    safety:
      SAFETY,

    sideEffects: {
      post: false,
      wallet: false,
      signing: false,
      broadcast: false,
      submission: false
    }
  };
}

export function writeProviderEvidence(
  outputDir = DEFAULT_OUTPUT_DIR
) {
  const report =
    buildProviderEvidence(
      outputDir
    );

  fs.mkdirSync(
    outputDir,
    {
      recursive: true
    }
  );

  const file =
    path.join(
      outputDir,
      "latest-provider-evidence.json"
    );

  fs.writeFileSync(
    file,
    JSON.stringify(
      report,
      null,
      2
    ) +
      "\n"
  );

  return {
    file,
    report
  };
}

async function main() {
  const result =
    writeProviderEvidence();

  console.log(
    "TERMiX AACP PROVIDER EVIDENCE v1.1"
  );

  console.log(
    "READ ONLY / FAIL CLOSED"
  );

  console.log(
    `EVIDENCE=${result.report.evidenceState}`
  );

  console.log(
    `REASON=${result.report.reason}`
  );

  console.log(
    `REPORTS=${result.report.summary.existingReports}/${result.report.summary.totalReports}`
  );

  console.log(
    `AUDIT_SHA256=${result.report.auditBinding.auditSha256 ?? "NONE"}`
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
  path.resolve(
    process.argv[1]
  ) ===
    path.resolve(
      new URL(
        import.meta.url
      ).pathname
    )
) {
  await main();
}
