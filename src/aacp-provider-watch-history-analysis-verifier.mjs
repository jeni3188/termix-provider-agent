import fs from "node:fs";
import path from "node:path";

const OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  "provider-output/aacp-observer";

const ANALYSIS_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-analysis.json"
);

const VERIFY_FILE = path.join(
  OUTPUT_DIR,
  "latest-provider-watch-history-analysis-verify.json"
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
      };
    }

    return {
      exists: true,
      valid: true,
      data: JSON.parse(
        fs.readFileSync(file, "utf8")
      ),
    };
  } catch {
    return {
      exists: true,
      valid: false,
      data: null,
    };
  }
}

function isSha256(value) {
  return (
    typeof value === "string" &&
    /^[a-f0-9]{64}$/i.test(value)
  );
}

function isBoolean(value) {
  return typeof value === "boolean";
}

function verifyAnalysis(result) {
  if (!result.exists) {
    return {
      state: "INCOMPLETE",
      reason: "Analysis report unavailable.",
      errors: ["ANALYSIS_MISSING"],
      checks: [],
    };
  }

  if (!result.valid) {
    return {
      state: "BLOCKED",
      reason: "Analysis report JSON is invalid.",
      errors: ["ANALYSIS_INVALID_JSON"],
      checks: [],
    };
  }

  const report = result.data;

  if (
    !report ||
    typeof report !== "object"
  ) {
    return {
      state: "BLOCKED",
      reason: "Analysis report root is invalid.",
      errors: ["ANALYSIS_ROOT_INVALID"],
      checks: [],
    };
  }

  const errors = [];
  const checks = [];

  checks.push({
    name: "mode_read_only",
    passed: report.mode === "READ_ONLY",
  });

  if (report.mode !== "READ_ONLY") {
    errors.push("MODE_NOT_READ_ONLY");
  }

  checks.push({
    name: "execution_not_authorized",
    passed: report.executionAuthorized === false,
  });

  if (report.executionAuthorized !== false) {
    errors.push("EXECUTION_AUTHORIZED");
  }

  if (
    typeof report.state !== "string" ||
    !ALLOWED_STATES.has(report.state)
  ) {
    errors.push("INVALID_STATE");
  }

  checks.push({
    name: "state_allowed",
    passed:
      typeof report.state === "string" &&
      ALLOWED_STATES.has(report.state),
  });

  const safety = report.safety;

  if (
    !safety ||
    typeof safety !== "object"
  ) {
    errors.push("SAFETY_MISSING");
  } else {
    for (const field of UNSAFE_FIELDS) {
      const value = safety[field];

      if (value !== false) {
        errors.push(`SAFETY_${field.toUpperCase()}`);
      }

      checks.push({
        name: `safety_${field}`,
        passed: value === false,
      });
    }
  }

  const sideEffects = report.sideEffects;

  if (
    !sideEffects ||
    typeof sideEffects !== "object"
  ) {
    errors.push("SIDE_EFFECTS_MISSING");
  } else {
    for (const field of UNSAFE_FIELDS.filter(
      (field) => field !== "executionAuthorized"
    )) {
      const value = sideEffects[field];

      if (value !== false) {
        errors.push(
          `SIDE_EFFECT_${field.toUpperCase()}`
        );
      }

      checks.push({
        name: `side_effect_${field}`,
        passed: value === false,
      });
    }
  }

  const analysis = report.analysis;

  if (
    !analysis ||
    typeof analysis !== "object"
  ) {
    errors.push("ANALYSIS_SECTION_MISSING");
  } else {
    if (
      !Number.isInteger(analysis.events) ||
      analysis.events < 0
    ) {
      errors.push("INVALID_EVENTS");
    }

    if (
      !Number.isInteger(analysis.transitions) ||
      analysis.transitions < 0
    ) {
      errors.push("INVALID_TRANSITIONS");
    }

    if (
      !Number.isInteger(analysis.changedEvents) ||
      analysis.changedEvents < 0
    ) {
      errors.push("INVALID_CHANGED_EVENTS");
    }

    if (
      !Number.isInteger(analysis.unsafeEvents) ||
      analysis.unsafeEvents < 0
    ) {
      errors.push("INVALID_UNSAFE_EVENTS");
    }

    if (!Array.isArray(analysis.anomalies)) {
      errors.push("ANOMALIES_NOT_ARRAY");
    }

    if (!Array.isArray(analysis.errors)) {
      errors.push("ERRORS_NOT_ARRAY");
    }

    if (
      analysis.events === 0 &&
      report.state === "VERIFIED_READ_ONLY"
    ) {
      errors.push("VERIFIED_WITH_ZERO_EVENTS");
    }

    if (
      analysis.unsafeEvents > 0 &&
      report.state === "VERIFIED_READ_ONLY"
    ) {
      errors.push("UNSAFE_EVENTS_MARKED_VERIFIED");
    }

    if (
      analysis.events > 0 &&
      analysis.firstEventAt !== null &&
      (
        typeof analysis.firstEventAt !== "string" ||
        Number.isNaN(
          Date.parse(analysis.firstEventAt)
        )
      )
    ) {
      errors.push("INVALID_FIRST_EVENT_TIMESTAMP");
    }

    if (
      analysis.events > 0 &&
      analysis.lastEventAt !== null &&
      (
        typeof analysis.lastEventAt !== "string" ||
        Number.isNaN(
          Date.parse(analysis.lastEventAt)
        )
      )
    ) {
      errors.push("INVALID_LAST_EVENT_TIMESTAMP");
    }

    if (
      analysis.firstEventAt &&
      analysis.lastEventAt &&
      Date.parse(analysis.firstEventAt) >
        Date.parse(analysis.lastEventAt)
    ) {
      errors.push("EVENT_RANGE_INVALID");
    }
  }

  const historySha256 =
    report.source?.historySha256;

  if (
    historySha256 !== null &&
    historySha256 !== undefined &&
    !isSha256(historySha256)
  ) {
    errors.push("INVALID_HISTORY_SHA256");
  }

  if (
    report.version !== undefined &&
    typeof report.version !== "string"
  ) {
    errors.push("INVALID_VERSION");
  }

  if (
    report.generatedAt !== undefined &&
    (
      typeof report.generatedAt !== "string" ||
      Number.isNaN(
        Date.parse(report.generatedAt)
      )
    )
  ) {
    errors.push("INVALID_GENERATED_AT");
  }

  return {
    state:
      errors.length > 0
        ? "BLOCKED"
        : "VERIFIED_READ_ONLY",
    reason:
      errors.length > 0
        ? "Analysis report failed integrity verification."
        : "Analysis report passed read-only integrity verification.",
    errors,
    checks,
  };
}

function writeReport(report) {
  fs.mkdirSync(OUTPUT_DIR, {
    recursive: true,
  });

  fs.writeFileSync(
    VERIFY_FILE,
    `${JSON.stringify(report, null, 2)}\n`,
    "utf8"
  );
}

function main() {
  const analysis = readJson(ANALYSIS_FILE);
  const result = verifyAnalysis(analysis);

  const report = {
    version: VERSION,
    generatedAt: new Date().toISOString(),

    mode: "READ_ONLY",
    state: result.state,

    source: {
      analysisExists: analysis.exists,
      analysisValid: analysis.valid,
    },

    verification: {
      reason: result.reason,
      errors: result.errors,
      checks: result.checks,
    },

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

  writeReport(report);

  console.log(
    "TERMiX AACP PROVIDER WATCH HISTORY ANALYSIS VERIFIER v1.0"
  );
  console.log("READ ONLY / FAIL CLOSED");
  console.log(`STATE=${report.state}`);
  console.log(
    `ANALYSIS_EXISTS=${analysis.exists}`
  );
  console.log(
    `ANALYSIS_VALID=${analysis.valid}`
  );
  console.log(
    `ERRORS=${result.errors.length}`
  );
  console.log(
    `CHECKS=${result.checks.length}`
  );
  console.log("EXECUTION_AUTHORIZED=false");
  console.log("POST=NOT_PERFORMED");
  console.log("WALLET=NOT_USED");
  console.log("SIGNING=NOT_PERFORMED");
  console.log("BROADCAST=NOT_PERFORMED");
  console.log("SUBMISSION=NOT_PERFORMED");
  console.log(`REPORT=${VERIFY_FILE}`);
}

main();
