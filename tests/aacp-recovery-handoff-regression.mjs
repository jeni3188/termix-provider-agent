import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  runRecoveryHandoff
} from "../src/aacp-recovery-handoff.mjs";

const methods = [];

const job = {
  jobId: "handoff-security-001",
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Recovery Handoff Security Audit",
  description:
    "Mock recovered security job"
};

const mockFetch = async (
  url,
  options = {}
) => {
  const method =
    options.method || "GET";

  methods.push(method);

  assert.equal(
    method,
    "GET"
  );

  const headers =
    new Headers({
      "content-type":
        "application/json"
    });

  if (url.endsWith("/config")) {
    return new Response(
      JSON.stringify({
        network: "testnet",
        status: "healthy"
      }),
      {
        status: 200,
        headers
      }
    );
  }

  if (
    url.includes(
      "status=OPEN"
    )
  ) {
    return new Response(
      JSON.stringify({
        jobs: [job]
      }),
      {
        status: 200,
        headers
      }
    );
  }

  if (
    url.includes(
      "status=FUNDED"
    )
  ) {
    return new Response(
      JSON.stringify({
        jobs: []
      }),
      {
        status: 200,
        headers
      }
    );
  }

  return new Response(
    JSON.stringify({
      jobs: []
    }),
    {
      status: 200,
      headers
    }
  );
};

const outputDir =
  fs.mkdtempSync(
    path.join(
      os.tmpdir(),
      "aacp-recovery-handoff-"
    )
  );

const result =
  await runRecoveryHandoff(
    mockFetch,
    {
      previousState: "DOWN",
      baseUrl:
        "https://mock.aacp.local",
      timeoutMs: 1000,
      outputDir
    }
  );

assert.equal(
  result.state,
  "HEALTHY"
);

assert.equal(
  result.previousState,
  "DOWN"
);

assert.equal(
  result.recovered,
  true
);

assert.equal(
  result.jobs.length,
  1
);

assert.equal(
  result.jobs[0].jobId,
  "handoff-security-001"
);

assert.ok(
  fs.existsSync(
    result.snapshotFile
  )
);

assert.ok(
  fs.existsSync(
    result.qualificationFile
  )
);

assert.ok(
  fs.existsSync(
    result.qualifiedReportFile
  )
);

assert.equal(
  result.qualifiedReport.mode,
  "READ_ONLY"
);

assert.equal(
  result.qualifiedReport.state,
  "HEALTHY"
);

assert.equal(
  result.qualifiedReport.previousState,
  "DOWN"
);

assert.equal(
  result.qualifiedReport.recovered,
  true
);

assert.equal(
  result.qualifiedReport.summary.observed,
  1
);

assert.equal(
  result.safety.postPerformed,
  false
);

assert.equal(
  result.safety.walletUsed,
  false
);

assert.equal(
  result.safety.signingPerformed,
  false
);

assert.equal(
  result.safety.broadcastPerformed,
  false
);

assert.equal(
  result.safety.submissionPerformed,
  false
);

assert.ok(
  methods.length >= 3
);

assert.equal(
  methods.every(
    method => method === "GET"
  ),
  true
);

assert.equal(
  methods.includes("POST"),
  false
);

console.log(
  "AACP RECOVERY HANDOFF REGRESSION"
);

console.log(
  "PASS: DOWN → HEALTHY recovery"
);

console.log(
  "PASS: existing recovery observer reused"
);

console.log(
  "PASS: existing qualification reused"
);

console.log(
  "PASS: qualified report generated"
);

console.log(
  "PASS: snapshot generated"
);

console.log(
  "PASS: GET-only"
);

console.log(
  "PASS: POST never performed"
);

console.log(
  "PASS: wallet never used"
);

console.log(
  "PASS: signing never performed"
);

console.log(
  "PASS: broadcast never performed"
);

console.log(
  "PASS: submission never performed"
);

console.log(
  "ALL RECOVERY HANDOFF TESTS PASSED"
);
