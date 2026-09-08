import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  buildProviderAudit,
  runProviderAudit
} from "../src/aacp-provider-audit.mjs";

function source(value, error = null) {
  return {
    exists: error === null,
    value,
    error
  };
}

function healthyValue() {
  return {
    state: "HEALTHY",
    safety: {
      postPerformed: false,
      walletUsed: false,
      signingPerformed: false,
      broadcastPerformed: false,
      submissionPerformed: false
    }
  };
}

console.log("AACP PROVIDER AUDIT REGRESSION");

const incomplete = buildProviderAudit({
  status: source(null, "FILE_MISSING"),
  qualification: source(null, "FILE_MISSING"),
  decision: source(null, "FILE_MISSING"),
  preflight: source(null, "FILE_MISSING")
});

assert.equal(incomplete.auditState, "INCOMPLETE");
assert.equal(incomplete.executionAuthorized, false);
console.log("PASS: missing reports → INCOMPLETE");

const backendUnavailable = buildProviderAudit({
  status: source(healthyValue()),
  qualification: source(healthyValue()),
  decision: source({
    state: "BACKEND_UNAVAILABLE",
    decision: "BACKEND_UNAVAILABLE",
    safety: healthyValue().safety
  }),
  preflight: source({
    preflight: "BACKEND_UNAVAILABLE",
    safety: healthyValue().safety
  })
});

assert.equal(
  backendUnavailable.auditState,
  "BACKEND_UNAVAILABLE"
);
assert.equal(
  backendUnavailable.executionAuthorized,
  false
);
console.log(
  "PASS: backend unavailable → BACKEND_UNAVAILABLE"
);

const blocked = buildProviderAudit({
  status: source(healthyValue()),
  qualification: source(healthyValue()),
  decision: source({
    state: "HEALTHY",
    decision: "BLOCKED",
    safety: healthyValue().safety
  }),
  preflight: source({
    preflight: "BLOCKED",
    safety: healthyValue().safety
  })
});

assert.equal(blocked.auditState, "BLOCKED");
assert.equal(blocked.executionAuthorized, false);
console.log("PASS: blocked provider → BLOCKED");

const unsafe = buildProviderAudit({
  status: source({
    ...healthyValue(),
    safety: {
      ...healthyValue().safety,
      signingPerformed: true
    }
  }),
  qualification: source(healthyValue()),
  decision: source({
    state: "HEALTHY",
    decision: "QUALIFIED",
    safety: {
      ...healthyValue().safety,
      signingPerformed: true
    }
  }),
  preflight: source({
    preflight: "READY_READ_ONLY",
    safety: {
      ...healthyValue().safety,
      signingPerformed: true
    }
  })
});

assert.equal(unsafe.auditState, "BLOCKED");
assert.equal(unsafe.unsafeDetected, true);
assert.equal(unsafe.executionAuthorized, false);
console.log("PASS: unsafe signing state → BLOCKED");

const readyJob = {
  jobId: "audit-test-job",
  qualification: "STRONG_MATCH",
  trusted: true,
  artifact: "TRUSTED_ARTIFACT"
};

const ready = buildProviderAudit({
  status: source({
    ...healthyValue(),
    state: "HEALTHY"
  }),
  qualification: source({
    ...healthyValue(),
    qualification: "STRONG_MATCH",
    trusted: true,
    artifact: "TRUSTED_ARTIFACT"
  }),
  decision: source({
    state: "HEALTHY",
    decision: "QUALIFIED",
    job: readyJob,
    safety: healthyValue().safety
  }),
  preflight: source({
    preflight: "READY_READ_ONLY",
    job: readyJob,
    safety: healthyValue().safety
  })
});

assert.equal(ready.auditState, "READY_READ_ONLY");
assert.equal(ready.executionAuthorized, false);
assert.equal(ready.provider.job.jobId, "audit-test-job");
console.log(
  "PASS: trusted qualified provider → READY_READ_ONLY"
);

const tempDir = fs.mkdtempSync(
  path.join(os.tmpdir(), "aacp-provider-audit-")
);

const statusFile = path.join(
  tempDir,
  "latest-provider-status.json"
);

const qualificationFile = path.join(
  tempDir,
  "latest-provider-qualification.json"
);

const decisionFile = path.join(
  tempDir,
  "latest-provider-decision.json"
);

const preflightFile = path.join(
  tempDir,
  "latest-provider-preflight.json"
);

fs.writeFileSync(
  statusFile,
  JSON.stringify({
    state: "HEALTHY",
    safety: healthyValue().safety
  })
);

fs.writeFileSync(
  qualificationFile,
  JSON.stringify({
    qualification: "STRONG_MATCH",
    trusted: true,
    artifact: "TRUSTED_ARTIFACT",
    safety: healthyValue().safety
  })
);

fs.writeFileSync(
  decisionFile,
  JSON.stringify({
    state: "HEALTHY",
    decision: "QUALIFIED",
    job: readyJob,
    safety: healthyValue().safety
  })
);

fs.writeFileSync(
  preflightFile,
  JSON.stringify({
    preflight: "READY_READ_ONLY",
    job: readyJob,
    safety: healthyValue().safety
  })
);

const result = runProviderAudit({
  outputDir: tempDir
});

assert.equal(
  result.report.auditState,
  "READY_READ_ONLY"
);

assert.equal(
  result.report.executionAuthorized,
  false
);

assert.equal(
  fs.existsSync(
    path.join(
      tempDir,
      "latest-provider-audit.json"
    )
  ),
  true
);

console.log("PASS: audit report generated");
console.log("PASS: executionAuthorized=false");

fs.rmSync(tempDir, {
  recursive: true,
  force: true
});

console.log("ALL PROVIDER AUDIT TESTS PASSED");
