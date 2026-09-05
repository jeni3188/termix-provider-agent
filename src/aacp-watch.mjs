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

async function check() {
  cycle++;

  try {
    const response = await fetch(`${api}/config`, {
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
      reason: err?.name === "TimeoutError"
        ? "TIMEOUT"
        : `ERROR:${err?.message || "unknown"}`
    };
  }
}

function handleState(result) {
  const state = result.state;

  if (previousState === "UNKNOWN") {
    log(`INITIAL_STATE=${state}`);
  } else if (previousState !== state) {
    log(`STATE_CHANGE ${previousState} -> ${state}`);

    if (previousState !== "HEALTHY" && state === "HEALTHY") {
      log("AACP_RECOVERED");
      log("ACTION=READ_ONLY_DISCOVERY_ALLOWED");
      log("POST=DISABLED");
      log("WALLET=NOT_USED");
      log("SIGNING=NOT_USED");
      log("SUBMISSION=NOT_PERFORMED");
    }
  }

  if (state === "HEALTHY") {
    log(
      `AACP HEALTHY HTTP ${result.httpStatus} (${result.reason})`
    );
  } else {
    log(
      `AACP ${state} ${result.httpStatus ?? "-"} (${result.reason})`
    );
  }

  previousState = state;
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
console.log(" AACP RECOVERY MONITOR v2.0.0");
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

while (!stopping) {
  const result = await check();

  log(`Cycle ${cycle}`);
  handleState(result);

  if (!stopping) {
    log(
      `Next check in ${Math.round(intervalMs / 1000)} seconds...`
    );
    await sleep(intervalMs);
  }
}
