import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT || "provider-output/aacp-observer";

const SOURCE_REPORT_NAMES = [
  "latest-provider-status.json",
  "latest-provider-qualification.json",
  "latest-provider-decision.json",
  "latest-provider-preflight.json",
  "latest-provider-audit.json",
];

const EVIDENCE_REPORT = "latest-provider-evidence.json";
const VERIFICATION_REPORT = "latest-provider-verification.json";

const UNSAFE_KEYS = [
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
];

function reportPath(name) {
  return path.join(OUTPUT_DIR, name);
}

async function readJson(name) {
  try {
    const raw = await fs.readFile(reportPath(name), "utf8");

    return {
      exists: true,
      valid: true,
      raw,
      data: JSON.parse(raw),
    };
  } catch {
    return {
      exists: false,
      valid: false,
      raw: null,
      data: null,
    };
  }
}

function sha256(text) {
  return crypto
    .createHash("sha256")
    .update(text, "utf8")
    .digest("hex");
}

function getSafety(report) {
  const safety = report?.safety || {};
  const sideEffects = report?.sideEffects || {};

  return {
    postPerformed:
      safety.postPerformed === true ||
      sideEffects.postPerformed === true,

    walletUsed:
      safety.walletUsed === true ||
      sideEffects.walletUsed === true,

    signingPerformed:
      safety.signingPerformed === true ||
      sideEffects.signingPerformed === true,

    broadcastPerformed:
      safety.broadcastPerformed === true ||
      sideEffects.broadcastPerformed === true,

    submissionPerformed:
      safety.submissionPerformed === true ||
      sideEffects.submissionPerformed === true,
  };
}

function hasUnsafeSideEffect(report) {
  const safety = getSafety(report);

  return UNSAFE_KEYS.some((key) => safety[key] === true);
}

function normalizeState(report) {
  return (
    report?.state ??
    report?.auditState ??
    report?.preflightState ??
    null
  );
}

function normalizeJobId(report) {
  return (
    report?.job?.jobId ??
    report?.jobId ??
    report?.selectedJob?.jobId ??
    null
  );
}

function verifySourceReports(reports) {
  const missing = SOURCE_REPORT_NAMES.filter(
    (name) => !reports[name]?.exists || !reports[name]?.valid,
  );

  return {
    expected: SOURCE_REPORT_NAMES.length,
    present: SOURCE_REPORT_NAMES.length - missing.length,
    complete: missing.length === 0,
    missing,
  };
}

function verifyEvidence(reports) {
  const evidence = reports[EVIDENCE_REPORT]?.data;

  if (!evidence) {
    return {
      exists: false,
      valid: false,
      reason: "Evidence report is missing or invalid.",
    };
  }

  if (evidence.mode !== "READ_ONLY") {
    return {
      exists: true,
      valid: false,
      reason: "Evidence mode is not READ_ONLY.",
    };
  }

  if (evidence.executionAuthorized !== false) {
    return {
      exists: true,
      valid: false,
      reason: "Evidence execution authorization is not false.",
    };
  }

  return {
    exists: true,
    valid: true,
    reason: "Evidence report is valid.",
  };
}

function verifySafety(reports) {
  const unsafeReports = [];

  for (const name of [
    ...SOURCE_REPORT_NAMES,
    EVIDENCE_REPORT,
  ]) {
    const report = reports[name]?.data;

    if (!report) continue;

    if (hasUnsafeSideEffect(report)) {
      unsafeReports.push(name);
    }

    if (report.executionAuthorized === true) {
      unsafeReports.push(`${name}:executionAuthorized`);
    }
  }

  return {
    valid: unsafeReports.length === 0,
    unsafeReports,
  };
}

function verifyModes(reports) {
  const invalid = [];

  for (const name of [
    ...SOURCE_REPORT_NAMES,
    EVIDENCE_REPORT,
  ]) {
    const report = reports[name]?.data;

    if (!report) continue;

    if (report.mode && report.mode !== "READ_ONLY") {
      invalid.push(name);
    }
  }

  return {
    valid: invalid.length === 0,
    invalid,
  };
}

function verifyChainConsistency(reports) {
  const status =
    reports["latest-provider-status.json"]?.data;

  const qualification =
    reports["latest-provider-qualification.json"]?.data;

  const decision =
    reports["latest-provider-decision.json"]?.data;

  const preflight =
    reports["latest-provider-preflight.json"]?.data;

  const audit =
    reports["latest-provider-audit.json"]?.data;

  const evidence =
    reports[EVIDENCE_REPORT]?.data;

  const problems = [];

  const statusState = normalizeState(status);
  const qualificationState = normalizeState(qualification);
  const decisionState = normalizeState(decision);
  const preflightState = normalizeState(preflight);
  const auditState = normalizeState(audit);
  const evidenceState = normalizeState(evidence);

  if (
    statusState &&
    qualificationState &&
    statusState !== "HEALTHY" &&
    qualificationState !== "BACKEND_UNAVAILABLE"
  ) {
    problems.push("status/qualification state mismatch");
  }

  if (decision && preflight) {
    if (
      decision.decision === "QUALIFIED" &&
      preflight.preflightState !== "READY_READ_ONLY"
    ) {
      problems.push(
        "qualified decision does not produce READY_READ_ONLY preflight",
      );
    }

    if (
      decision.decision !== "QUALIFIED" &&
      preflight.preflightState === "READY_READ_ONLY"
    ) {
      problems.push(
        "blocked decision has READY_READ_ONLY preflight",
      );
    }
  }

  if (preflight && audit) {
    if (
      preflight.preflightState &&
      audit.auditState &&
      preflight.preflightState !== audit.auditState
    ) {
      problems.push("preflight/audit state mismatch");
    }
  }

  if (audit && evidence) {
    if (
      audit.auditState &&
      evidence.auditBinding?.auditState &&
      audit.auditState !== evidence.auditBinding.auditState
    ) {
      problems.push("audit/evidence state mismatch");
    }
  }

  const jobIds = [
    normalizeJobId(qualification),
    normalizeJobId(decision),
    normalizeJobId(preflight),
    normalizeJobId(audit),
  ].filter((value) => value !== null);

  if (new Set(jobIds).size > 1) {
    problems.push("job binding mismatch");
  }

  return {
    valid: problems.length === 0,
    problems,

    states: {
      status: statusState,
      qualification: qualificationState,
      decision: decisionState,
      preflight: preflightState,
      audit: auditState,
      evidence: evidenceState,
    },
  };
}

function verifyAuditSha(reports) {
  const audit = reports["latest-provider-audit.json"];
  const evidence = reports[EVIDENCE_REPORT];

  if (!audit?.exists || !audit?.valid) {
    return {
      valid: false,
      expected: null,
      actual: null,
      reason: "Audit report is missing or invalid.",
    };
  }

  if (!evidence?.exists || !evidence?.valid) {
    return {
      valid: false,
      expected: null,
      actual: sha256(audit.raw),
      reason: "Evidence report is missing or invalid.",
    };
  }

  const expected =
    evidence.data?.auditBinding?.auditSha256 ?? null;

  const actual = sha256(audit.raw);

  if (!expected) {
    return {
      valid: false,
      expected,
      actual,
      reason: "Evidence does not contain audit SHA-256.",
    };
  }

  return {
    valid: expected === actual,
    expected,
    actual,

    reason:
      expected === actual
        ? "Audit SHA-256 matches evidence binding."
        : "Audit SHA-256 does not match evidence binding.",
  };
}

function determineVerification({
  sourceReports,
  evidence,
  safety,
  modes,
  chain,
  auditSha,
  reports,
}) {
  if (!sourceReports.complete || !evidence.valid) {
    return {
      verification: "INCOMPLETE",
      reason: "Provider evidence set is incomplete.",
    };
  }

  if (!modes.valid) {
    return {
      verification: "BLOCKED",
      reason: "One or more reports are not READ_ONLY.",
    };
  }

  if (!safety.valid) {
    return {
      verification: "BLOCKED",
      reason:
        "Unsafe side effects or execution authorization detected.",
    };
  }

  if (!auditSha.valid) {
    return {
      verification: "BLOCKED",
      reason: "Audit SHA-256 binding is invalid.",
    };
  }

  if (!chain.valid) {
    return {
      verification: "BLOCKED",
      reason:
        "Provider report chain is internally inconsistent.",
    };
  }

  const audit =
    reports["latest-provider-audit.json"].data;

  if (audit.auditState === "BACKEND_UNAVAILABLE") {
    return {
      verification: "BACKEND_UNAVAILABLE",
      reason:
        "Provider audit reports backend unavailable.",
    };
  }

  if (audit.auditState === "INCOMPLETE") {
    return {
      verification: "INCOMPLETE",
      reason:
        "Provider audit reports incomplete evidence.",
    };
  }

  if (audit.auditState !== "READY_READ_ONLY") {
    return {
      verification: "BLOCKED",
      reason:
        `Provider audit state is ${audit.auditState || "UNKNOWN"}.`,
    };
  }

  return {
    verification: "VERIFIED",
    reason:
      "Provider evidence chain and SHA-256 bindings are valid.",
  };
}

function buildVerification(reports) {
  const sourceReports = verifySourceReports(reports);
  const evidence = verifyEvidence(reports);
  const safety = verifySafety(reports);
  const modes = verifyModes(reports);
  const chain = verifyChainConsistency(reports);
  const auditSha = verifyAuditSha(reports);

  const result = determineVerification({
    sourceReports,
    evidence,
    safety,
    modes,
    chain,
    auditSha,
    reports,
  });

  const reportHashes = {};

  for (const name of [
    ...SOURCE_REPORT_NAMES,
    EVIDENCE_REPORT,
  ]) {
    if (
      reports[name]?.exists &&
      reports[name]?.valid
    ) {
      reportHashes[name] =
        sha256(reports[name].raw);
    }
  }

  return {
    version: "1.1.0",

    generatedAt:
      new Date().toISOString(),

    mode: "READ_ONLY",

    verification:
      result.verification,

    reason:
      result.reason,

    reports: {
      expected: SOURCE_REPORT_NAMES.length,
      present: sourceReports.present,
      missing: sourceReports.missing,
      sha256: reportHashes,
    },

    evidence: {
      exists: evidence.exists,
      valid: evidence.valid,
    },

    integrity: {
      valid:
        sourceReports.complete &&
        evidence.valid &&
        modes.valid &&
        safety.valid &&
        auditSha.valid &&
        chain.valid,
    },

    auditBinding: {
      valid: auditSha.valid,
      expectedSha256: auditSha.expected,
      actualSha256: auditSha.actual,
      reason: auditSha.reason,
    },

    chain,

    safety: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false,
    },

    executionAuthorized: false,
  };
}

async function writeVerification(report) {
  await fs.mkdir(OUTPUT_DIR, {
    recursive: true,
  });

  const target =
    reportPath(VERIFICATION_REPORT);

  await fs.writeFile(
    target,
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8",
  );

  return target;
}

async function main() {
  const reports = {};

  for (const name of [
    ...SOURCE_REPORT_NAMES,
    EVIDENCE_REPORT,
  ]) {
    reports[name] =
      await readJson(name);
  }

  const verification =
    buildVerification(reports);

  const target =
    await writeVerification(verification);

  console.log(
    "TERMiX AACP PROVIDER VERIFIER v1.1",
  );

  console.log(
    "READ ONLY / FAIL CLOSED",
  );

  console.log(
    `VERIFICATION=${verification.verification}`,
  );

  console.log(
    `REASON=${verification.reason}`,
  );

  console.log(
    `REPORTS=${verification.reports.present}/${verification.reports.expected}`,
  );

  console.log(
    `INTEGRITY=${
      verification.integrity.valid
        ? "VALID"
        : "INVALID"
    }`,
  );

  console.log(
    `CHAIN=${
      verification.chain.valid
        ? "VALID"
        : "INVALID"
    }`,
  );

  console.log(
    `AUDIT_SHA=${
      verification.auditBinding.valid
        ? "VALID"
        : "INVALID"
    }`,
  );

  console.log(
    "EXECUTION_AUTHORIZED=false",
  );

  console.log(
    "POST=NOT_PERFORMED",
  );

  console.log(
    "WALLET=NOT_USED",
  );

  console.log(
    "SIGNING=NOT_PERFORMED",
  );

  console.log(
    "BROADCAST=NOT_PERFORMED",
  );

  console.log(
    "SUBMISSION=NOT_PERFORMED",
  );

  console.log(
    `REPORT=${target}`,
  );
}

main().catch((error) => {
  console.error("VERIFIER_ERROR");
  console.error(error.message);
  process.exitCode = 1;
});
