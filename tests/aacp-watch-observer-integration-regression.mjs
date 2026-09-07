import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { check, processState } from "../src/aacp-watch.mjs";
import { observeRecovery } from "../src/aacp-recovery-observer.mjs";
import { writeSnapshot } from "../src/aacp-job-inspector.mjs";
import { writeQualification } from "../src/aacp-job-qualifier.mjs";
import { writeQualifiedJobReport } from "../src/aacp-qualified-job-report.mjs";

console.log("========================================");
console.log(" AACP WATCH → OBSERVER INTEGRATION");
console.log(" MOCK HTTP / READ ONLY");
console.log("========================================");

let passed = 0;
let failed = 0;
let calls = [];

function pass(name) {
  passed++;
  console.log(`PASS: ${name}`);
}

function fail(name, error) {
  failed++;
  console.log(`FAIL: ${name}`);
  console.log(`      ${error.message}`);
}

function response(status, body) {
  return new Response(
    JSON.stringify(body),
    {
      status,
      headers: {
        "content-type": "application/json"
      }
    }
  );
}

const job = {
  jobId: "integration-security-001",
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Integration Security Audit",
  description: "Mock security audit job",
  deadline: 1799000000,
  providerId: null
};

const mockFetch = async (url, options = {}) => {
  calls.push({
    method: options.method || "GET",
    url
  });

  assert.equal(
    options.method || "GET",
    "GET",
    "integration must remain GET-only"
  );

  if (url.endsWith("/config")) {
    return response(200, {
      chainId: 97,
      network: "bsc-testnet"
    });
  }

  if (url.includes("status=OPEN")) {
    return response(200, {
      jobs: [job]
    });
  }

  if (url.includes("status=FUNDED")) {
    return response(200, {
      jobs: []
    });
  }

  return response(404, {});
};

try {
  const downFetch = async (url, options = {}) => {
    calls.push({
      method: options.method || "GET",
      url
    });

    return new Response(
      "<html>Service Unavailable</html>",
      {
        status: 503,
        headers: {
          "content-type": "text/html"
        }
      }
    );
  };

  const down = await check(downFetch);

  assert.equal(down.state, "DOWN");
  pass("watcher detects DOWN");
} catch (error) {
  fail("watcher detects DOWN", error);
}

try {
  const healthy = await check(mockFetch);

  assert.equal(healthy.state, "HEALTHY");

  const downEvents = processState({
    state: "DOWN",
    httpStatus: 503,
    reason: "HTTP_503"
  });

  assert.ok(
    downEvents.includes("INITIAL_STATE=DOWN") ||
    downEvents.includes("AACP DOWN"),
    "initial DOWN state must be processed"
  );

  const events = processState(healthy);

  assert.ok(
    events.includes("AACP_RECOVERED"),
    "DOWN → HEALTHY recovery event required"
  );

  pass("watcher detects DOWN → HEALTHY");
} catch (error) {
  fail("watcher detects DOWN → HEALTHY", error);
}

let observed;
let snapshotFile;
let qualificationFile;
let qualifiedReportFile;

try {
  observed = await observeRecovery(
    mockFetch,
    {
      previousState: "DOWN",
      baseUrl: "https://mock.aacp.local",
      timeoutMs: 1000
    }
  );

  assert.equal(observed.state, "HEALTHY");
  assert.equal(observed.recovered, true);
  assert.equal(observed.jobs.length, 1);
  assert.equal(
    observed.jobs[0].jobId,
    "integration-security-001"
  );

  pass("recovery observer captures recovered job");
} catch (error) {
  fail("recovery observer captures recovered job", error);
}

const tempDir = fs.mkdtempSync(
  path.join(os.tmpdir(), "termix-observer-")
);

try {
  snapshotFile = writeSnapshot(
    observed,
    tempDir
  );

  assert.ok(fs.existsSync(snapshotFile));

  const data = JSON.parse(
    fs.readFileSync(snapshotFile, "utf8")
  );

  assert.equal(data.mode, "READ_ONLY");
  assert.equal(data.state, "HEALTHY");
  assert.equal(data.recovered, true);
  assert.equal(data.jobs.length, 1);
  assert.equal(
    data.jobs[0].jobId,
    "integration-security-001"
  );

  pass("job snapshot written successfully");
} catch (error) {
  fail("job snapshot written successfully", error);
}

try {
  const qualification = writeQualification(
    observed.jobs,
    tempDir
  );

  qualificationFile = qualification.file;

  assert.ok(
    fs.existsSync(qualificationFile)
  );

  assert.equal(
    qualification.output.jobs.length,
    1
  );

  assert.equal(
    qualification.output.jobs[0].qualification,
    "ARTIFACT_MISSING"
  );

  assert.equal(
    qualification.output.jobs[0].artifactTrusted,
    false
  );

  pass("qualification result preserved");
} catch (error) {
  fail("qualification result preserved", error);
}

try {
  const qualification = JSON.parse(
    fs.readFileSync(
      qualificationFile,
      "utf8"
    )
  );

  const qualifiedReport =
    writeQualifiedJobReport(
      {
        state: observed.state,
        previousState: observed.previousState,
        recovered: observed.recovered,
        jobs: qualification.jobs,
        safety: qualification.safety
      },
      tempDir
    );

  qualifiedReportFile =
    qualifiedReport.file;

  assert.ok(
    fs.existsSync(qualifiedReportFile)
  );

  const report = JSON.parse(
    fs.readFileSync(
      qualifiedReportFile,
      "utf8"
    )
  );

  assert.equal(
    report.mode,
    "READ_ONLY"
  );

  assert.equal(
    report.version,
    "3.0.0"
  );

  assert.equal(
    report.summary.observed,
    1
  );

  assert.equal(
    report.summary.unique,
    1
  );

  assert.equal(
    report.summary.qualified,
    0
  );

  assert.equal(
    report.summary.blocked,
    1
  );

  assert.equal(
    report.blocked[0].jobId,
    "integration-security-001"
  );

  assert.equal(
    report.blocked[0].reason,
    "ARTIFACT_MISSING"
  );

  assert.equal(
    report.blocked[0].artifact,
    "NO_ARTIFACT"
  );

  assert.equal(
    report.blocked[0].trusted,
    false
  );

  pass("qualified job report written and qualification preserved");
} catch (error) {
  fail(
    "qualified job report written and qualification preserved",
    error
  );
}

try {
  const forbidden = calls.filter(
    call => call.method !== "GET"
  );

  assert.equal(forbidden.length, 0);

  pass("entire integration is GET-only");
} catch (error) {
  fail("entire integration is GET-only", error);
}

try {
  assert.ok(snapshotFile);
  assert.ok(fs.existsSync(snapshotFile));

  const snapshot = JSON.parse(
    fs.readFileSync(snapshotFile, "utf8")
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

  pass("snapshot safety gates remain closed");
} catch (error) {
  fail("snapshot safety gates remain closed", error);
}

console.log("");
console.log("========================================");
console.log(" INTEGRATION TEST SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
console.log("");
console.log(
  failed === 0
    ? "AACP WATCH → OBSERVER INTEGRATION PASSED"
    : "AACP WATCH → OBSERVER INTEGRATION FAILED"
);
console.log("");
console.log("Real network : NONE");
console.log("POST         : NOT PERFORMED");
console.log("Wallet       : NOT USED");
console.log("Signing      : NOT USED");
console.log("Submission   : NOT PERFORMED");

process.exitCode = failed === 0 ? 0 : 1;
