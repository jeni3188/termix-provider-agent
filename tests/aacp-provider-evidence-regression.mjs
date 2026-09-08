import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  buildProviderEvidence,
  writeProviderEvidence
} from "../src/aacp-provider-evidence.mjs";

function makeDir(label) {
  return fs.mkdtempSync(
    path.join(
      os.tmpdir(),
      `aacp-provider-evidence-${label}-`
    )
  );
}

function writeReport(dir, name, value) {
  fs.writeFileSync(
    path.join(dir, name),
    JSON.stringify(value, null, 2) + "\n"
  );
}

function writeAllReports(dir) {
  const names = [
    "latest-provider-status.json",
    "latest-provider-qualification.json",
    "latest-provider-decision.json",
    "latest-provider-preflight.json"
  ];

  for (const name of names) {
    writeReport(dir, name, {
      mode: "READ_ONLY"
    });
  }
}

console.log(
  "AACP PROVIDER EVIDENCE REGRESSION"
);

// 1. Missing reports
{
  const dir = makeDir("incomplete");

  writeReport(
    dir,
    "latest-provider-audit.json",
    {
      mode: "READ_ONLY",
      auditState: "INCOMPLETE",
      executionAuthorized: false,
      unsafeDetected: false
    }
  );

  const report =
    buildProviderEvidence(dir);

  assert.equal(
    report.evidenceState,
    "INCOMPLETE"
  );

  assert.equal(
    report.summary.existingReports,
    1
  );

  assert.equal(
    report.summary.missingReports,
    4
  );

  console.log(
    "PASS: incomplete reports → INCOMPLETE"
  );
}

// 2. Unsafe audit
{
  const dir = makeDir("unsafe");

  writeAllReports(dir);

  writeReport(
    dir,
    "latest-provider-audit.json",
    {
      mode: "READ_ONLY",
      auditState: "BLOCKED",
      executionAuthorized: false,
      unsafeDetected: true
    }
  );

  const report =
    buildProviderEvidence(dir);

  assert.equal(
    report.evidenceState,
    "BLOCKED"
  );

  assert.equal(
    report.executionAuthorized,
    false
  );

  console.log(
    "PASS: unsafe audit → BLOCKED"
  );
}

// 3. Backend unavailable
{
  const dir = makeDir("backend");

  writeAllReports(dir);

  writeReport(
    dir,
    "latest-provider-audit.json",
    {
      mode: "READ_ONLY",
      auditState: "BACKEND_UNAVAILABLE",
      executionAuthorized: false,
      unsafeDetected: false
    }
  );

  const report =
    buildProviderEvidence(dir);

  assert.equal(
    report.evidenceState,
    "BACKEND_UNAVAILABLE"
  );

  console.log(
    "PASS: backend unavailable audit → BACKEND_UNAVAILABLE"
  );
}

// 4. Blocked audit
{
  const dir = makeDir("blocked");

  writeAllReports(dir);

  writeReport(
    dir,
    "latest-provider-audit.json",
    {
      mode: "READ_ONLY",
      auditState: "BLOCKED",
      executionAuthorized: false,
      unsafeDetected: false
    }
  );

  const report =
    buildProviderEvidence(dir);

  assert.equal(
    report.evidenceState,
    "BLOCKED"
  );

  console.log(
    "PASS: blocked audit → BLOCKED"
  );
}

// 5. READY_READ_ONLY + all reports
{
  const dir = makeDir("ready");

  writeAllReports(dir);

  writeReport(
    dir,
    "latest-provider-audit.json",
    {
      mode: "READ_ONLY",
      auditState: "READY_READ_ONLY",
      executionAuthorized: false,
      unsafeDetected: false
    }
  );

  const report =
    buildProviderEvidence(dir);

  assert.equal(
    report.evidenceState,
    "COMPLETE"
  );

  assert.equal(
    report.summary.existingReports,
    5
  );

  assert.equal(
    report.summary.missingReports,
    0
  );

  assert.equal(
    report.executionAuthorized,
    false
  );

  console.log(
    "PASS: READY_READ_ONLY + 5 reports → COMPLETE"
  );
}

// 6. Never authorize execution
{
  const dir = makeDir("authorization");

  writeAllReports(dir);

  writeReport(
    dir,
    "latest-provider-audit.json",
    {
      mode: "READ_ONLY",
      auditState: "READY_READ_ONLY",
      executionAuthorized: false,
      unsafeDetected: false
    }
  );

  const report =
    buildProviderEvidence(dir);

  assert.equal(
    report.auditBinding.executionAuthorized,
    false
  );

  assert.equal(
    report.executionAuthorized,
    false
  );

  console.log(
    "PASS: executionAuthorized=false"
  );
}

// 7. Evidence file generation
{
  const dir = makeDir("generated");

  writeAllReports(dir);

  writeReport(
    dir,
    "latest-provider-audit.json",
    {
      mode: "READ_ONLY",
      auditState: "READY_READ_ONLY",
      executionAuthorized: false,
      unsafeDetected: false
    }
  );

  const result =
    writeProviderEvidence(dir);

  assert.equal(
    fs.existsSync(result.file),
    true
  );

  const saved =
    JSON.parse(
      fs.readFileSync(
        result.file,
        "utf8"
      )
    );

  assert.equal(
    saved.executionAuthorized,
    false
  );

  console.log(
    "PASS: evidence report generated"
  );
}

console.log(
  "ALL PROVIDER EVIDENCE TESTS PASSED"
);
