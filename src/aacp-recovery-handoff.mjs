import fs from "node:fs";
import path from "node:path";

import {
  observeRecovery
} from "./aacp-recovery-observer.mjs";

import {
  writeSnapshot
} from "./aacp-job-inspector.mjs";

import {
  writeQualification
} from "./aacp-job-qualifier.mjs";

import {
  writeQualifiedJobReport
} from "./aacp-qualified-job-report.mjs";

const DEFAULT_BASE_URL =
  process.env.AACP_BACKEND_URL ||
  "https://aacp-backend.termix.live";

const DEFAULT_OUTPUT_DIR =
  process.env.AACP_OBSERVER_OUTPUT ||
  path.join(
    process.cwd(),
    "provider-output",
    "aacp-observer"
  );

const READ_ONLY_SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false
};

function mergeSafety(...values) {
  const result = {
    ...READ_ONLY_SAFETY
  };

  for (const value of values) {
    if (!value) continue;

    for (const key of Object.keys(result)) {
      if (value[key] === true) {
        result[key] = true;
      }
    }
  }

  return result;
}

export async function runRecoveryHandoff(
  fetchImpl = fetch,
  options = {}
) {
  const baseUrl =
    options.baseUrl ||
    DEFAULT_BASE_URL;

  const outputDir =
    options.outputDir ||
    DEFAULT_OUTPUT_DIR;

  const previousState =
    options.previousState ||
    "NONE";

  const observed =
    await observeRecovery(
      fetchImpl,
      {
        baseUrl,
        previousState,
        timeoutMs:
          options.timeoutMs
      }
    );

  const safety =
    mergeSafety(
      observed.safety
    );

  const normalized = {
    ...observed,
    safety
  };

  const snapshotFile =
    writeSnapshot(
      normalized,
      outputDir
    );

  const qualification =
    writeQualification(
      normalized.jobs,
      outputDir
    );

  const qualifiedReport =
    writeQualifiedJobReport(
      {
        state:
          normalized.state,

        previousState:
          normalized.previousState,

        recovered:
          normalized.recovered,

        jobs:
          qualification.output.jobs,

        safety
      },
      outputDir
    );

  return {
    ...normalized,

    qualification:
      qualification.output.jobs,

    snapshotFile,

    qualificationFile:
      qualification.file,

    qualifiedReportFile:
      qualifiedReport.file,

    qualifiedReport:
      qualifiedReport.report,

    safety
  };
}

function main() {
  return runRecoveryHandoff()
    .then(result => {
      console.log(
        "TERMiX AACP RECOVERY HANDOFF v1.0"
      );

      console.log(
        "READ ONLY / GET ONLY"
      );

      console.log(
        `Previous State : ${result.previousState}`
      );

      console.log(
        `Current State  : ${result.state}`
      );

      console.log(
        `Recovered      : ${
          result.recovered
            ? "YES"
            : "NO"
        }`
      );

      console.log(
        `Jobs           : ${result.jobs.length}`
      );

      console.log(
        `Qualified      : ${
          result.qualifiedReport
            ?.summary
            ?.qualified ?? 0
        }`
      );

      console.log(
        `Blocked        : ${
          result.qualifiedReport
            ?.summary
            ?.blocked ?? 0
        }`
      );

      console.log("");

      console.log(
        `Snapshot       : ${result.snapshotFile}`
      );

      console.log(
        `Qualification  : ${result.qualificationFile}`
      );

      console.log(
        `Qualified Report: ${result.qualifiedReportFile}`
      );

      console.log("");

      console.log(
        "POST           : NOT PERFORMED"
      );

      console.log(
        "WALLET         : NOT USED"
      );

      console.log(
        "SIGNING        : NOT PERFORMED"
      );

      console.log(
        "BROADCAST      : NOT PERFORMED"
      );

      console.log(
        "SUBMISSION     : NOT PERFORMED"
      );
    });
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
