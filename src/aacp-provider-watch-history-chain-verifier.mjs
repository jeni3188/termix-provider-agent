import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  "provider-output/aacp-observer";

const HISTORY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history.json"
);

const HISTORY_VERIFY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-verify.json"
);

const ANALYSIS_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-analysis.json"
);

const ANALYSIS_VERIFY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-analysis-verify.json"
);

const OUTPUT_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-chain-verify.json"
);

const VERSION = "1.0.0";

const ALLOWED_STATES = new Set([
  "BACKEND_UNAVAILABLE",
  "INCOMPLETE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]);

const UNSAFE_FIELDS = [
  "executionAuthorized",
  "postPerformed",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
];

function readJson(file) {
  try {
    if (!fs.existsSync(file)) {
      return {
        exists: false,
        valid: false,
        data: null,
        sha256: null,
      };
    }

    const raw = fs.readFileSync(file, "utf8");

    return {
      exists: true,
      valid: true,
      data: JSON.parse(raw),
      sha256: crypto
        .createHash("sha256")
        .update(raw, "utf8")
        .digest("hex"),
    };
  } catch {
    return {
      exists: true,
      valid: false,
      data: null,
      sha256: null,
    };
  }
}

function isObject(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value)
  );
}

function isSha256(value) {
  return (
    typeof value === "string" &&
    /^[a-f0-9]{64}$/i.test(value)
  );
}

function isSafeFlags(value) {
  if (!isObject(value)) {
    return false;
  }

  return UNSAFE_FIELDS.every(
    (field) => value[field] === false
  );
}

function verifyLayer(name, result, errors) {
  if (!result.exists) {
    errors.push(`${name.toUpperCase()}_MISSING`);
    return null;
  }

  if (!result.valid) {
    errors.push(`${name.toUpperCase()}_INVALID_JSON`);
    return null;
  }

  if (!isObject(result.data)) {
    errors.push(`${name.toUpperCase()}_ROOT_INVALID`);
    return null;
  }

  return result.data;
}

function verifyCommonSafety(name, report, errors) {
  if (!isObject(report)) {
    return;
  }

  if (report.mode !== "READ_ONLY") {
    errors.push(`${name.toUpperCase()}_MODE_NOT_READ_ONLY`);
  }

  if (report.executionAuthorized !== false) {
    errors.push(`${name.toUpperCase()}_EXECUTION_AUTHORIZED`);
  }

  if (
    report.safety !== undefined &&
    !isSafeFlags(report.safety)
  ) {
    errors.push(`${name.toUpperCase()}_UNSAFE_SAFETY`);
  }

  if (
    report.sideEffects !== undefined &&
    !isSafeFlags({
      executionAuthorized: false,
      ...report.sideEffects,
    })
  ) {
    errors.push(`${name.toUpperCase()}_UNSAFE_SIDE_EFFECTS`);
  }
}

function extractState(report) {
  return (
    typeof report?.state === "string"
      ? report.state
      : null
  );
}

function extractHistoryHash(report) {
  const candidates = [
    report?.historySha256,
    report?.source?.historySha256,
    report?.analysis?.historySha256,
  ];

  return candidates.find(isSha256) || null;
}

function extractAnalysisHash(report) {
  const candidates = [
    report?.analysisSha256,
    report?.source?.analysisSha256,
    report?.source?.sha256,
  ];

  return candidates.find(isSha256) || null;
}

function verifyChain() {
  const history = readJson(HISTORY_FILE);
  const historyVerify = readJson(HISTORY_VERIFY_FILE);
  const analysis = readJson(ANALYSIS_FILE);
  const analysisVerify = readJson(ANALYSIS_VERIFY_FILE);

  const errors = [];
  const checks = [];

  const historyData = verifyLayer(
    "history",
    history,
    errors
  );

  const historyVerifyData = verifyLayer(
    "history_verify",
    historyVerify,
    errors
  );

  const analysisData = verifyLayer(
    "analysis",
    analysis,
    errors
  );

  const analysisVerifyData = verifyLayer(
    "analysis_verify",
    analysisVerify,
    errors
  );

  checks.push({
    name: "history_exists",
    passed: history.exists,
  });

  checks.push({
    name: "history_json_valid",
    passed: history.valid,
  });

  checks.push({
    name: "history_verify_exists",
    passed: historyVerify.exists,
  });

  checks.push({
    name: "history_verify_json_valid",
    passed: historyVerify.valid,
  });

  checks.push({
    name: "analysis_exists",
    passed: analysis.exists,
  });

  checks.push({
    name: "analysis_json_valid",
    passed: analysis.valid,
  });

  checks.push({
    name: "analysis_verify_exists",
    passed: analysisVerify.exists,
  });

  checks.push({
    name: "analysis_verify_json_valid",
    passed: analysisVerify.valid,
  });

  for (const [name, report] of [
    ["history_verify", historyVerifyData],
    ["analysis", analysisData],
    ["analysis_verify", analysisVerifyData],
  ]) {
    if (report) {
      verifyCommonSafety(
        name,
        report,
        errors
      );
    }
  }

  for (const [name, report] of [
    ["history_verify", historyVerifyData],
    ["analysis", analysisData],
    ["analysis_verify", analysisVerifyData],
  ]) {
    const state = extractState(report);

    checks.push({
      name: `${name}_state_allowed`,
      passed:
        state !== null &&
        ALLOWED_STATES.has(state),
    });

    if (
      state !== null &&
      !ALLOWED_STATES.has(state)
    ) {
      errors.push(
        `${name.toUpperCase()}_INVALID_STATE`
      );
    }
  }

  if (
    historyData &&
    !Array.isArray(historyData.events)
  ) {
    errors.push("HISTORY_EVENTS_NOT_ARRAY");
  }

  if (
    historyData &&
    Array.isArray(historyData.events) &&
    historyData.events.length === 0
  ) {
    errors.push("HISTORY_EMPTY");
  }

  if (
    historyVerifyData &&
    Array.isArray(historyData?.events)
  ) {
    const verifiedEvents =
      historyVerifyData.history?.events ??
      historyVerifyData.events;

    if (
      Array.isArray(verifiedEvents) &&
      verifiedEvents.length !==
        historyData.events.length
    ) {
      errors.push("HISTORY_EVENT_COUNT_MISMATCH");
    }
  }

  const historyHashFromVerify =
    extractHistoryHash(historyVerifyData);

  const historyHashFromAnalysis =
    extractHistoryHash(analysisData);

  const historyHashFromAnalysisVerify =
    extractHistoryHash(analysisVerifyData);

  if (
    historyHashFromVerify &&
    history.sha256 &&
    historyHashFromVerify !== history.sha256
  ) {
    errors.push("HISTORY_SHA256_MISMATCH_VERIFY");
  }

  if (
    historyHashFromAnalysis &&
    history.sha256 &&
    historyHashFromAnalysis !== history.sha256
  ) {
    errors.push("HISTORY_SHA256_MISMATCH_ANALYSIS");
  }

  if (
    historyHashFromAnalysisVerify &&
    history.sha256 &&
    historyHashFromAnalysisVerify !==
      history.sha256
  ) {
    errors.push(
      "HISTORY_SHA256_MISMATCH_ANALYSIS_VERIFY"
    );
  }

  if (
    historyHashFromVerify &&
    historyHashFromAnalysis &&
    historyHashFromVerify !==
      historyHashFromAnalysis
  ) {
    errors.push("HISTORY_SHA256_CHAIN_MISMATCH");
  }

  if (
    historyHashFromAnalysis &&
    historyHashFromAnalysisVerify &&
    historyHashFromAnalysis !==
      historyHashFromAnalysisVerify
  ) {
    errors.push(
      "HISTORY_SHA256_ANALYSIS_VERIFY_MISMATCH"
    );
  }

  const analysisHashFromVerify =
    extractAnalysisHash(analysisVerifyData);

  if (
    analysisHashFromVerify &&
    analysis.sha256 &&
    analysisHashFromVerify !== analysis.sha256
  ) {
    errors.push("ANALYSIS_SHA256_MISMATCH");
  }

  const analysisState =
    extractState(analysisData);

  const analysisVerifyState =
    extractState(analysisVerifyData);

  if (
    analysisState &&
    analysisVerifyState &&
    analysisState !== analysisVerifyState
  ) {
    errors.push("ANALYSIS_STATE_MISMATCH");
  }

  const historyVerifyState =
    extractState(historyVerifyData);

  if (
    historyVerifyState &&
    analysisState &&
    historyVerifyState !== analysisState
  ) {
    errors.push("HISTORY_ANALYSIS_STATE_MISMATCH");
  }

  if (
    historyVerifyData &&
    historyVerifyData.mode !== "READ_ONLY"
  ) {
    errors.push("CHAIN_MODE_NOT_READ_ONLY");
  }

  if (
    analysisData &&
    analysisData.mode !== "READ_ONLY"
  ) {
    errors.push("CHAIN_ANALYSIS_MODE_NOT_READ_ONLY");
  }

  if (
    analysisVerifyData &&
    analysisVerifyData.mode !== "READ_ONLY"
  ) {
    errors.push(
      "CHAIN_ANALYSIS_VERIFY_MODE_NOT_READ_ONLY"
    );
  }

  if (
    historyVerifyData &&
    historyVerifyData.executionAuthorized !== false
  ) {
    errors.push("CHAIN_EXECUTION_AUTHORIZED");
  }

  if (
    analysisData &&
    analysisData.executionAuthorized !== false
  ) {
    errors.push("CHAIN_ANALYSIS_EXECUTION_AUTHORIZED");
  }

  if (
    analysisVerifyData &&
    analysisVerifyData.executionAuthorized !== false
  ) {
    errors.push(
      "CHAIN_ANALYSIS_VERIFY_EXECUTION_AUTHORIZED"
    );
  }

  const state =
    errors.length > 0
      ? "BLOCKED"
      : "VERIFIED_READ_ONLY";

  return {
    state,
    reason:
      errors.length > 0
        ? "Provider watch history chain verification failed."
        : "Provider watch history chain is internally consistent.",
    errors,
    checks,
    source: {
      historySha256: history.sha256,
      historyVerifySha256:
        historyVerify.sha256,
      analysisSha256: analysis.sha256,
      analysisVerifySha256:
        analysisVerify.sha256,
    },
  };
}

function writeReport(result) {
  fs.mkdirSync(
    OUTPUT_DIR,
    { recursive: true }
  );

  const report = {
    version: VERSION,
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state: result.state,
    reason: result.reason,
    source: result.source,
    checks: result.checks,
    errors: result.errors,
    safety: {
      executionAuthorized: false,
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false,
    },
    sideEffects: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false,
    },
    executionAuthorized: false,
  };

  fs.writeFileSync(
    OUTPUT_FILE,
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8"
  );

  return report;
}

function main() {
  console.log(
    "TERMiX AACP PROVIDER WATCH HISTORY CHAIN VERIFIER v1.0"
  );
  console.log(
    "READ ONLY / FAIL CLOSED"
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

  const result = verifyChain();
  const report = writeReport(result);

  console.log(`STATE=${report.state}`);
  console.log(
    `CHECKS=${report.checks.length}`
  );
  console.log(
    `ERRORS=${report.errors.length}`
  );
  console.log(
    `EXECUTION_AUTHORIZED=${report.executionAuthorized}`
  );
  console.log(
    `REPORT=${OUTPUT_FILE}`
  );
}

main();
