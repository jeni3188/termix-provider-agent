import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  preflightProviderDecision,
  buildProviderPreflight,
  writeProviderPreflight
} from "../src/aacp-provider-preflight.mjs";

const strongDecision = {
  mode: "READ_ONLY",
  state: "HEALTHY",
  decision: "QUALIFIED",
  job: {
    jobId: "job-phase6",
    qualification: "STRONG_MATCH",
    artifact: "TRUSTED_ARTIFACT",
    trusted: true
  },
  safety: {
    postPerformed: false,
    walletUsed: false,
    signingPerformed: false,
    broadcastPerformed: false,
    submissionPerformed: false
  }
};

let result;

result =
  preflightProviderDecision({
    ...strongDecision,
    state: "BACKEND_UNAVAILABLE"
  });

assert.equal(
  result.preflight,
  "BACKEND_UNAVAILABLE"
);

result =
  preflightProviderDecision({
    ...strongDecision,
    state: "UNKNOWN"
  });

assert.equal(
  result.preflight,
  "BLOCKED"
);

result =
  preflightProviderDecision({
    ...strongDecision,
    decision: "BLOCKED"
  });

assert.equal(
  result.preflight,
  "BLOCKED"
);

result =
  preflightProviderDecision({
    ...strongDecision,
    safety: {
      ...strongDecision.safety,
      walletUsed: true
    }
  });

assert.equal(
  result.preflight,
  "BLOCKED"
);

result =
  preflightProviderDecision({
    ...strongDecision,
    safety: {
      ...strongDecision.safety,
      signingPerformed: true
    }
  });

assert.equal(
  result.preflight,
  "BLOCKED"
);

result =
  preflightProviderDecision({
    ...strongDecision,
    job: {
      ...strongDecision.job,
      trusted: false
    }
  });

assert.equal(
  result.preflight,
  "BLOCKED"
);

result =
  preflightProviderDecision(
    strongDecision
  );

assert.equal(
  result.preflight,
  "READY_READ_ONLY"
);

assert.equal(
  result.job.jobId,
  "job-phase6"
);

const report =
  buildProviderPreflight(
    strongDecision
  );

assert.equal(
  report.preflight,
  "READY_READ_ONLY"
);

assert.equal(
  report.executionAuthorized,
  false
);

assert.equal(
  report.mode,
  "READ_ONLY"
);

for (
  const value of Object.values(
    report.safety
  )
) {
  assert.equal(value, false);
}

const temp =
  fs.mkdtempSync(
    path.join(
      os.tmpdir(),
      "termix-provider-preflight-"
    )
  );

const written =
  writeProviderPreflight(
    strongDecision,
    temp
  );

assert.equal(
  fs.existsSync(written.file),
  true
);

const saved =
  JSON.parse(
    fs.readFileSync(
      written.file,
      "utf8"
    )
  );

assert.equal(
  saved.preflight,
  "READY_READ_ONLY"
);

assert.equal(
  saved.executionAuthorized,
  false
);

console.log(
  "AACP PROVIDER PREFLIGHT REGRESSION"
);

console.log(
  "PASS: backend unavailable → BACKEND_UNAVAILABLE"
);

console.log(
  "PASS: unhealthy state → BLOCKED"
);

console.log(
  "PASS: non-qualified decision → BLOCKED"
);

console.log(
  "PASS: unsafe wallet/signing state → BLOCKED"
);

console.log(
  "PASS: untrusted artifact → BLOCKED"
);

console.log(
  "PASS: strong trusted decision → READY_READ_ONLY"
);

console.log(
  "PASS: executionAuthorized=false"
);

console.log(
  "PASS: preflight report generated"
);

console.log(
  "ALL PROVIDER PREFLIGHT TESTS PASSED"
);
