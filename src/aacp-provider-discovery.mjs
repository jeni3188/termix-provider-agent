import fs from "node:fs";
import path from "node:path";

import { discoverReadOnly } from "./aacp-readonly-discovery.mjs";

const DEFAULT_OUTPUT_DIR =
  process.env.AACP_PROVIDER_OUTPUT_DIR ||
  path.join(
    process.cwd(),
    "provider-output",
    "aacp-observer"
  );

const DEFAULT_BASE_URL =
  process.env.AACP_BACKEND_URL ||
  "https://aacp-backend.termix.live";

function safetyState() {
  return {
    postPerformed: false,
    walletUsed: false,
    signingPerformed: false,
    broadcastPerformed: false,
    submissionPerformed: false
  };
}

function buildProviderDiscovery(result) {
  return {
    version: "1.0.0",
    mode: "READ_ONLY",

    state:
      result?.state ??
      "BACKEND_REQUEST_FAILED",

    backend:
      DEFAULT_BASE_URL,

    observedAt:
      new Date().toISOString(),

    config:
      result?.config ??
      null,

    endpoints:
      result?.endpoints ??
      {},

    jobs:
      Array.isArray(result?.jobs)
        ? result.jobs
        : [],

    inspectedJobs:
      Array.isArray(result?.inspectedJobs)
        ? result.inspectedJobs
        : [],

    qualification:
      Array.isArray(result?.qualification)
        ? result.qualification
        : [],

    invalidJobs:
      Array.isArray(result?.invalidJobs)
        ? result.invalidJobs
        : [],

    safety:
      result?.safety ??
      safetyState()
  };
}

export async function discoverProviderReadOnly(
  fetchImpl = fetch,
  options = {}
) {
  const result =
    await discoverReadOnly(
      fetchImpl,
      {
        baseUrl:
          options.baseUrl ||
          DEFAULT_BASE_URL,

        timeoutMs:
          options.timeoutMs
      }
    );

  return buildProviderDiscovery(result);
}

export function writeProviderDiscovery(
  snapshot,
  outputDir = DEFAULT_OUTPUT_DIR
) {
  fs.mkdirSync(
    outputDir,
    { recursive: true }
  );

  const outputFile =
    path.join(
      outputDir,
      "latest-provider-discovery.json"
    );

  fs.writeFileSync(
    outputFile,
    JSON.stringify(
      snapshot,
      null,
      2
    ) + "\n",
    "utf8"
  );

  return outputFile;
}

async function main() {
  const snapshot =
    await discoverProviderReadOnly();

  const outputFile =
    writeProviderDiscovery(
      snapshot
    );

  console.log(
    "TERMiX AACP PROVIDER DISCOVERY v1.0"
  );

  console.log(
    "READ ONLY / GET ONLY"
  );

  console.log(
    `State          : ${snapshot.state}`
  );

  console.log(
    `Jobs           : ${snapshot.jobs.length}`
  );

  console.log(
    `Qualification  : ${snapshot.qualification.length}`
  );

  console.log(
    `Invalid Jobs   : ${snapshot.invalidJobs.length}`
  );

  console.log(
    `Output         : ${outputFile}`
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
