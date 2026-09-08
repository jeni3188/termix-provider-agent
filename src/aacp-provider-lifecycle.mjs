import fs from "node:fs";
import path from "node:path";

const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT || "provider-output/aacp-observer";

const REPORTS = {
  status: "latest-provider-status.json",
  qualification: "latest-provider-qualification.json",
  decision: "latest-provider-decision.json",
  preflight: "latest-provider-preflight.json",
  audit: "latest-provider-audit.json",
  evidence: "latest-provider-evidence.json",
  verification: "latest-provider-verification.json",
};

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-lifecycle.json"
);

const READ_ONLY_SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false,
  executionAuthorized: false,
};

function readJson(filename) {
  const file = path.join(OUTPUT_DIR, filename);

  if (!fs.existsSync(file)) {
    return {
      exists: false,
      valid: false,
      data: null,
    };
  }

  try {
    const raw = fs.readFileSync(file, "utf8");
    return {
      exists: true,
      valid: true,
      data: JSON.parse(raw),
    };
  } catch {
    return {
      exists: true,
      valid: false,
      data: null,
    };
  }
}

function unsafe(report) {
  const data = report?.data;

  if (!data) return false;

  const safety = data.safety || {};
  const sideEffects = data.sideEffects || {};

  return (
    data.executionAuthorized === true ||
    safety.postPerformed === true ||
    safety.walletUsed === true ||
    safety.signingPerformed === true ||
    safety.broadcastPerformed === true ||
    safety.submissionPerformed === true ||
    sideEffects.postPerformed === true ||
    sideEffects.walletUsed === true ||
    sideEffects.signingPerformed === true ||
    sideEffects.broadcastPerformed === true ||
    sideEffects.submissionPerformed === true
  );
}

function getState(report) {
  return report?.data?.state || null;
}

function getJobId(report) {
  return report?.data?.job?.jobId ?? null;
}

function allRequiredPresent(reports) {
  const required = [
    "status",
    "qualification",
    "decision",
    "preflight",
    "audit",
    "evidence",
    "verification",
  ];

  return required.every(
    (key) => reports[key]?.exists && reports[key]?.valid
  );
}

function determineLifecycle(reports) {
  const verification = reports.verification.data;
  const audit = reports.audit.data;
  const evidence = reports.evidence.data;

  if (!allRequiredPresent(reports)) {
    return {
      state: "INCOMPLETE",
      reason: "One or more provider lifecycle reports are missing or invalid.",
    };
  }

  if (Object.values(reports).some(unsafe)) {
    return {
      state: "BLOCKED",
      reason: "Unsafe side-effect or execution authorization detected.",
    };
  }

  for (const [name, report] of Object.entries(reports)) {
    const mode = report.data?.mode;

    if (mode && mode !== "READ_ONLY") {
      return {
        state: "BLOCKED",
        reason: `${name} report is not READ_ONLY.`,
      };
    }
  }

  if (verification.executionAuthorized !== false) {
    return {
      state: "BLOCKED",
      reason: "Verification does not explicitly fail closed.",
    };
  }

  if (evidence.executionAuthorized !== false) {
    return {
      state: "BLOCKED",
      reason: "Evidence does not explicitly fail closed.",
    };
  }

  if (verification.verification === "BACKEND_UNAVAILABLE") {
    return {
      state: "BACKEND_UNAVAILABLE",
      reason: "Provider backend is unavailable.",
    };
  }

  if (
    verification.verification === "INCOMPLETE" ||
    audit.state === "INCOMPLETE" ||
    evidence.state === "INCOMPLETE"
  ) {
    return {
      state: "INCOMPLETE",
      reason: "Provider evidence or verification is incomplete.",
    };
  }

  if (verification.verification !== "VERIFIED") {
    return {
      state: "BLOCKED",
      reason: "Provider verification is not VERIFIED.",
    };
  }

  if (audit.state !== "READY_READ_ONLY") {
    return {
      state: "BLOCKED",
      reason: "Provider audit is not READY_READ_ONLY.",
    };
  }

  if (evidence.state !== "COMPLETE") {
    return {
      state: "BLOCKED",
      reason: "Provider evidence is not COMPLETE.",
    };
  }

  return {
    state: "VERIFIED_READ_ONLY",
    reason: "Provider lifecycle is fully verified in read-only mode.",
  };
}

function buildLifecycle() {
  const reports = Object.fromEntries(
    Object.entries(REPORTS).map(([key, filename]) => [
      key,
      readJson(filename),
    ])
  );

  const result = determineLifecycle(reports);

  const jobIds = Object.fromEntries(
    Object.entries(reports).map(([key, report]) => [
      key,
      getJobId(report),
    ])
  );

  const uniqueJobIds = [
    ...new Set(Object.values(jobIds).filter(Boolean)),
  ];

  const jobBinding =
    uniqueJobIds.length <= 1
      ? "VALID"
      : "INVALID";

  const finalState =
    jobBinding === "INVALID"
      ? "BLOCKED"
      : result.state;

  const finalReason =
    jobBinding === "INVALID"
      ? "Provider reports reference inconsistent job IDs."
      : result.reason;

  return {
    version: "1.0.0",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    lifecycle: finalState,
    reason: finalReason,

    verification: {
      verification:
        reports.verification.data?.verification ?? null,
      auditState:
        reports.audit.data?.state ?? null,
      evidenceState:
        reports.evidence.data?.state ?? null,
    },

    jobBinding: {
      status: jobIds.status,
      qualification: jobIds.qualification,
      decision: jobIds.decision,
      preflight: jobIds.preflight,
      audit: jobIds.audit,
      evidence: jobIds.evidence,
      verification: jobIds.verification,
      result: jobBinding,
    },

    reports: Object.fromEntries(
      Object.entries(reports).map(([key, report]) => [
        key,
        {
          exists: report.exists,
          valid: report.valid,
        },
      ])
    ),

    executionAuthorized: false,

    safety: READ_ONLY_SAFETY,

    sideEffects: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false,
    },
  };
}

function writeLifecycle(report) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.writeFileSync(
    OUTPUT_FILE,
    JSON.stringify(report, null, 2) + "\n",
    "utf8"
  );
}

const report = buildLifecycle();

writeLifecycle(report);

console.log("TERMiX AACP PROVIDER LIFECYCLE v1.0");
console.log("READ ONLY / FAIL CLOSED");
console.log(`LIFECYCLE=${report.lifecycle}`);
console.log(`REASON=${report.reason}`);
console.log(
  `VERIFICATION=${report.verification.verification ?? "UNKNOWN"}`
);
console.log(
  `AUDIT=${report.verification.auditState ?? "UNKNOWN"}`
);
console.log(
  `EVIDENCE=${report.verification.evidenceState ?? "UNKNOWN"}`
);
console.log(`JOB_BINDING=${report.jobBinding.result}`);
console.log("EXECUTION_AUTHORIZED=false");
console.log("POST=NOT_PERFORMED");
console.log("WALLET=NOT_USED");
console.log("SIGNING=NOT_PERFORMED");
console.log("BROADCAST=NOT_PERFORMED");
console.log("SUBMISSION=NOT_PERFORMED");
console.log(`REPORT=${OUTPUT_FILE}`);
