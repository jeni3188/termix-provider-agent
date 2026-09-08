import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = path.resolve(".");
const SOURCE = path.join(ROOT, "src", "aacp-provider-lifecycle.mjs");

const tmp = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-provider-lifecycle-")
);

const REPORT_NAMES = [
  "latest-provider-status.json",
  "latest-provider-qualification.json",
  "latest-provider-decision.json",
  "latest-provider-preflight.json",
  "latest-provider-audit.json",
  "latest-provider-evidence.json",
  "latest-provider-verification.json",
];

const SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false,
  executionAuthorized: false,
};

function clean() {
  fs.rmSync(tmp, { recursive: true, force: true });
}

function write(name, data) {
  fs.writeFileSync(
    path.join(tmp, name),
    JSON.stringify(data, null, 2) + "\n",
    "utf8"
  );
}

function baseReports() {
  return {
    status: {
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "HEALTHY",
      job: { jobId: "job-001" },
      safety: SAFETY,
    },

    qualification: {
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "HEALTHY",
      job: {
        jobId: "job-001",
        qualification: "STRONG_MATCH",
        trusted: true,
        artifact: "TRUSTED_ARTIFACT",
      },
      safety: SAFETY,
    },

    decision: {
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "HEALTHY",
      decision: "QUALIFIED",
      job: {
        jobId: "job-001",
        qualification: "STRONG_MATCH",
        trusted: true,
        artifact: "TRUSTED_ARTIFACT",
      },
      safety: SAFETY,
    },

    preflight: {
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "READY_READ_ONLY",
      executionAuthorized: false,
      job: { jobId: "job-001" },
      safety: SAFETY,
    },

    audit: {
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "READY_READ_ONLY",
      executionAuthorized: false,
      job: { jobId: "job-001" },
      safety: SAFETY,
      sideEffects: {
        postPerformed: false,
        walletUsed: false,
        signingPerformed: false,
        broadcastPerformed: false,
        submissionPerformed: false,
      },
    },

    evidence: {
      version: "1.1.0",
      mode: "READ_ONLY",
      state: "COMPLETE",
      executionAuthorized: false,
      auditBinding: {
        auditExists: true,
        auditSha256: "fixture",
        auditState: "READY_READ_ONLY",
        executionAuthorized: false,
      },
      safety: SAFETY,
      sideEffects: {
        postPerformed: false,
        walletUsed: false,
        signingPerformed: false,
        broadcastPerformed: false,
        submissionPerformed: false,
      },
    },

    verification: {
      version: "1.1.0",
      mode: "READ_ONLY",
      verification: "VERIFIED",
      executionAuthorized: false,
      safety: SAFETY,
      job: { jobId: "job-001" },
    },
  };
}

function resetReports(overrides = {}) {
  clean();
  fs.mkdirSync(tmp, { recursive: true });

  const reports = baseReports();

  for (const [key, value] of Object.entries(overrides)) {
    reports[key] = {
      ...reports[key],
      ...value,
    };
  }

  for (const name of REPORT_NAMES) {
    const key = Object.keys({
      status: 1,
      qualification: 1,
      decision: 1,
      preflight: 1,
      audit: 1,
      evidence: 1,
      verification: 1,
    }).find(
      (candidate) =>
        `latest-provider-${candidate}.json` === name
    );

    write(name, reports[key]);
  }
}

function run() {
  return spawnSync(
    process.execPath,
    [SOURCE],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OBSERVER_OUTPUT: tmp,
      },
      encoding: "utf8",
    }
  );
}

function lifecycle() {
  const file = path.join(
    tmp,
    "latest-provider-lifecycle.json"
  );

  assert.ok(fs.existsSync(file), "lifecycle report missing");

  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function assertSafe(report) {
  assert.equal(report.executionAuthorized, false);
  assert.equal(report.safety.postPerformed, false);
  assert.equal(report.safety.walletUsed, false);
  assert.equal(report.safety.signingPerformed, false);
  assert.equal(report.safety.broadcastPerformed, false);
  assert.equal(report.safety.submissionPerformed, false);
}

console.log("AACP PROVIDER LIFECYCLE REGRESSION");

try {
  clean();

  // 1. Missing reports
  {
    fs.mkdirSync(tmp, { recursive: true });

    const result = run();
    assert.equal(result.status, 0);

    const report = lifecycle();

    assert.equal(report.lifecycle, "INCOMPLETE");
    assertSafe(report);

    console.log("PASS: missing reports → INCOMPLETE");
  }

  // 2. Complete verified chain
  {
    resetReports();

    const result = run();
    assert.equal(result.status, 0);

    const report = lifecycle();

    assert.equal(report.lifecycle, "VERIFIED_READ_ONLY");
    assert.equal(report.jobBinding.result, "VALID");
    assertSafe(report);

    console.log(
      "PASS: complete verified chain → VERIFIED_READ_ONLY"
    );
  }

  // 3. Backend unavailable
  {
    resetReports({
      verification: {
        verification: "BACKEND_UNAVAILABLE",
      },
      audit: {
        state: "BACKEND_UNAVAILABLE",
      },
      evidence: {
        state: "BACKEND_UNAVAILABLE",
      },
    });

    const result = run();
    assert.equal(result.status, 0);

    const report = lifecycle();

    assert.equal(
      report.lifecycle,
      "BACKEND_UNAVAILABLE"
    );
    assertSafe(report);

    console.log(
      "PASS: backend unavailable → BACKEND_UNAVAILABLE"
    );
  }

  // 4. Blocked verification
  {
    resetReports({
      verification: {
        verification: "BLOCKED",
      },
      audit: {
        state: "BLOCKED",
      },
      evidence: {
        state: "BLOCKED",
      },
    });

    const result = run();
    assert.equal(result.status, 0);

    const report = lifecycle();

    assert.equal(report.lifecycle, "BLOCKED");
    assertSafe(report);

    console.log("PASS: blocked verification → BLOCKED");
  }

  // 5. Unsafe audit
  {
    resetReports({
      audit: {
        safety: {
          ...SAFETY,
          signingPerformed: true,
        },
      },
    });

    const result = run();
    assert.equal(result.status, 0);

    const report = lifecycle();

    assert.equal(report.lifecycle, "BLOCKED");
    assertSafe(report);

    console.log("PASS: unsafe signing state → BLOCKED");
  }

  // 6. Non READ_ONLY
  {
    resetReports({
      audit: {
        mode: "EXECUTION",
      },
    });

    const result = run();
    assert.equal(result.status, 0);

    const report = lifecycle();

    assert.equal(report.lifecycle, "BLOCKED");
    assertSafe(report);

    console.log("PASS: non-READ_ONLY report → BLOCKED");
  }

  // 7. executionAuthorized=true
  {
    resetReports({
      verification: {
        executionAuthorized: true,
      },
    });

    const result = run();
    assert.equal(result.status, 0);

    const report = lifecycle();

    assert.equal(report.lifecycle, "BLOCKED");
    assertSafe(report);

    console.log(
      "PASS: executionAuthorized=true → BLOCKED"
    );
  }

  // 8. Inconsistent job IDs
  {
    resetReports({
      audit: {
        job: { jobId: "job-999" },
      },
    });

    const result = run();
    assert.equal(result.status, 0);

    const report = lifecycle();

    assert.equal(report.lifecycle, "BLOCKED");
    assert.equal(report.jobBinding.result, "INVALID");
    assertSafe(report);

    console.log(
      "PASS: inconsistent job IDs → BLOCKED"
    );
  }

  // 9. Missing one report
  {
    resetReports();

    fs.unlinkSync(
      path.join(
        tmp,
        "latest-provider-evidence.json"
      )
    );

    const result = run();
    assert.equal(result.status, 0);

    const report = lifecycle();

    assert.equal(report.lifecycle, "INCOMPLETE");
    assertSafe(report);

    console.log(
      "PASS: missing evidence → INCOMPLETE"
    );
  }

  // 10. Lifecycle report generated
  {
    resetReports();

    run();

    const file = path.join(
      tmp,
      "latest-provider-lifecycle.json"
    );

    assert.ok(fs.existsSync(file));

    const report = lifecycle();

    assert.equal(report.mode, "READ_ONLY");
    assertSafe(report);

    console.log("PASS: lifecycle report generated");
  }

  console.log(
    "PASS: executionAuthorized=false"
  );

  console.log(
    "ALL PROVIDER LIFECYCLE TESTS PASSED"
  );
} finally {
  clean();
}
