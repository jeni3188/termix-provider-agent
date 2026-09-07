import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  discoverProviderReadOnly,
  writeProviderDiscovery
} from "../src/aacp-provider-discovery.mjs";

const requests = [];

const mockFetch = async (url, options = {}) => {
  requests.push({
    url,
    method: options.method || "GET"
  });

  assert.equal(
    options.method || "GET",
    "GET"
  );

  if (url.endsWith("/api/v1/config")) {
    return new Response(
      JSON.stringify({
        network: "testnet",
        providerMode: "READ_ONLY"
      }),
      {
        status: 200,
        headers: {
          "content-type": "application/json"
        }
      }
    );
  }

  if (
    url.includes(
      "/api/v1/jobs?status=OPEN"
    )
  ) {
    return new Response(
      JSON.stringify({
        jobs: [
          {
            jobId: "job-open-1",
            status: "OPEN",
            strategyType: "SECURITY",
            title: "Security audit",
            budget: 100
          }
        ]
      }),
      {
        status: 200,
        headers: {
          "content-type": "application/json"
        }
      }
    );
  }

  if (
    url.includes(
      "/api/v1/jobs?status=FUNDED"
    )
  ) {
    return new Response(
      JSON.stringify({
        jobs: [
          {
            jobId: "job-funded-1",
            status: "FUNDED",
            strategyType: "SECURITY",
            title: "Funded audit",
            budget: 250
          }
        ]
      }),
      {
        status: 200,
        headers: {
          "content-type": "application/json"
        }
      }
    );
  }

  throw new Error(
    `Unexpected URL: ${url}`
  );
};

const snapshot =
  await discoverProviderReadOnly(
    mockFetch,
    {
      baseUrl:
        "https://mock.aacp.local",
      timeoutMs: 1000
    }
  );

assert.equal(
  snapshot.version,
  "1.0.0"
);

assert.equal(
  snapshot.mode,
  "READ_ONLY"
);

assert.equal(
  snapshot.state,
  "HEALTHY"
);

assert.equal(
  snapshot.jobs.length,
  2
);

assert.equal(
  snapshot.invalidJobs.length,
  0
);

assert.equal(
  snapshot.safety.postPerformed,
  false
);

assert.equal(
  snapshot.safety.walletUsed,
  false
);

assert.equal(
  snapshot.safety.signingPerformed,
  false
);

assert.equal(
  snapshot.safety.broadcastPerformed,
  false
);

assert.equal(
  snapshot.safety.submissionPerformed,
  false
);

assert.equal(
  requests.every(
    x => x.method === "GET"
  ),
  true
);

assert.equal(
  requests.some(
    x => x.method === "POST"
  ),
  false
);

const tempDir =
  fs.mkdtempSync(
    path.join(
      os.tmpdir(),
      "aacp-provider-discovery-"
    )
  );

const output =
  writeProviderDiscovery(
    snapshot,
    tempDir
  );

assert.equal(
  fs.existsSync(output),
  true
);

const saved =
  JSON.parse(
    fs.readFileSync(
      output,
      "utf8"
    )
  );

assert.equal(
  saved.jobs.length,
  2
);

assert.equal(
  saved.safety.submissionPerformed,
  false
);

console.log(
  "AACP PROVIDER DISCOVERY REGRESSION"
);

console.log(
  "PASS: uses existing discoverReadOnly engine"
);

console.log(
  "PASS: GET-only"
);

console.log(
  "PASS: healthy discovery preserved"
);

console.log(
  "PASS: qualification preserved"
);

console.log(
  "PASS: safety gates remain false"
);

console.log(
  "PASS: snapshot written"
);

console.log(
  "ALL PROVIDER DISCOVERY TESTS PASSED"
);
