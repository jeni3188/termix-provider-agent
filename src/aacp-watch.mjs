import { observeRecovery } from "./aacp-recovery-observer.mjs";
import { writeSnapshot } from "./aacp-job-inspector.mjs";
import { writeQualification } from "./aacp-job-qualifier.mjs";
import { writeQualifiedJobReport } from "./aacp-qualified-job-report.mjs";

const intervalMs =
  Number(process.env.AACP_WATCH_INTERVAL_MS || 1800000);

const timeoutMs =
  Number(process.env.AACP_WATCH_TIMEOUT_MS || 15000);

const base =
  process.env.TERMIX_AACP_URL ||
  "https://aacp-backend.termix.live";

const api = `${base}/api/v1`;

let previousState = "UNKNOWN";
let cycle = 0;
let stopping = false;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function timestamp() {
  return new Date().toISOString();
}

function log(message) {
  console.log(`[${timestamp()}] ${message}`);
}

export async function check(fetchImpl = fetch) {
  cycle++;

  try {
    const response = await fetchImpl(`${api}/config`, {
      signal: AbortSignal.timeout(timeoutMs)
    });

    const text = await response.text();

    let json = null;

    try {
      json = JSON.parse(text);
    } catch {}

    if (!response.ok) {
      return {
        state: "DOWN",
        httpStatus: response.status,
        reason: `HTTP_${response.status}`
      };
    }

    if (!json) {
      return {
        state: "BLOCKED",
        httpStatus: response.status,
        reason: "NON_JSON_RESPONSE"
      };
    }

    return {
      state: "HEALTHY",
      httpStatus: response.status,
      reason: "JSON_OK"
    };
  } catch (err) {
    return {
      state: "DOWN",
      httpStatus: null,
      reason:
        err?.name === "TimeoutError"
          ? "TIMEOUT"
          : `ERROR:${err?.message || "unknown"}`
    };
  }
}

export function processState(result) {
  const state = result.state;
  const events = [];

  if (previousState === "UNKNOWN") {
    events.push(`INITIAL_STATE=${state}`);
  } else if (previousState !== state) {
    events.push(`STATE_CHANGE ${previousState} -> ${state}`);

    if (previousState !== "HEALTHY" && state === "HEALTHY") {
      events.push("AACP_RECOVERED");
      events.push("ACTION=READ_ONLY_DISCOVERY_ALLOWED");
      events.push("POST=DISABLED");
      events.push("WALLET=NOT_USED");
      events.push("SIGNING=NOT_USED");
      events.push("SUBMISSION=NOT_PERFORMED");
    }
  }

  if (state === "HEALTHY") {
    events.push(
      `AACP HEALTHY HTTP ${result.httpStatus} (${result.reason})`
    );
  } else {
    events.push(
      `AACP ${state} ${result.httpStatus ?? "-"} (${result.reason})`
    );
  }

  previousState = state;

  return events;
}

function shutdown(signal) {
  if (stopping) return;

  stopping = true;

  log(`SHUTDOWN ${signal}`);
  log("POST=DISABLED");
  log("WALLET=NOT_USED");
  log("SIGNING=NOT_USED");
  log("SUBMISSION=NOT_PERFORMED");

  process.exit(0);
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

console.log("========================================");
console.log(" AACP RECOVERY MONITOR v2.1.0");
console.log("========================================");
console.log(`Backend : ${base}`);
console.log(`Interval: ${Math.round(intervalMs / 1000)} seconds`);
console.log(`Timeout : ${Math.round(timeoutMs / 1000)} seconds`);
console.log("Mode    : READ-ONLY");
console.log("POST    : DISABLED");
console.log("Wallet  : NOT USED");
console.log("Signing : NOT USED");
console.log("Submit  : NOT PERFORMED");
console.log("");

if (process.env.AACP_WATCH_TEST !== "1") {
  while (!stopping) {
    const result = await check();

    log(`Cycle ${cycle}`);

    const events = processState(result);

    for (const event of events) {
      log(event);
    }

    if (events.includes("AACP_RECOVERED")) {
      try {
        const observed = await observeRecovery(fetch, {
          previousState: "DOWN",
          baseUrl: base,
          timeoutMs
        });

        const snapshotFile = writeSnapshot(observed);

        log(`JOB_SNAPSHOT=${snapshotFile}`);
        log(`RECOVERY_JOBS=${observed.jobs.length}`);

        const qualification = writeQualification(
          observed.jobs
        );

        log(
          `JOB_QUALIFICATION=${qualification.file}`
        );

        log(
          `QUALIFIED_JOBS=${qualification.output.summary.total}`
        );

        const qualifiedReport =
          writeQualifiedJobReport({
            state: observed.state,
            previousState: observed.previousState,
            recovered: observed.recovered,
            jobs: qualification.output.jobs,
            safety: qualification.output.safety
          });

        log(
          `QUALIFIED_JOB_REPORT=${qualifiedReport.file}`
        );

        log(
          `QUALIFIED=${qualifiedReport.report.summary.qualified}`
        );

        log(
          `BLOCKED=${qualifiedReport.report.summary.blocked}`
        );
      } catch (error) {
        log(
          `JOB_SNAPSHOT_FAILED=${error?.message || error}`
        );
      }
    }

    if (!stopping) {
      log(
        `Next check in ${Math.round(intervalMs / 1000)} seconds...`
      );

      await sleep(intervalMs);
    }
  }
}
