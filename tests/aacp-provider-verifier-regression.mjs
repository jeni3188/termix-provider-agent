import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const VERIFIER = path.join(
  ROOT,
  "src",
  "aacp-provider-verifier.mjs",
);

const SOURCE_REPORTS = [
  "latest-provider-status.json",
  "latest-provider-qualification.json",
  "latest-provider-decision.json",
  "latest-provider-preflight.json",
  "latest-provider-audit.json",
];

const EVIDENCE = "latest-provider-evidence.json";

function sha256(text) {
  return crypto
    .createHash("sha256")
    .update(text, "utf8")
    .digest("hex");
}

async function writeJson(dir, name, data) {
  await fs.writeFile(
    path.join(dir, name),
    `${JSON.stringify(data, null, 2)}\n`,
    "utf8",
  );
}

async function readJson(dir, name) {
  return JSON.parse(
    await fs.readFile(
      path.join(dir, name),
      "utf8",
    ),
  );
}

function runVerifier(dir) {
  const result = spawnSync(
    process.execPath,
    [VERIFIER],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OBSERVER_OUTPUT: dir,
      },
      encoding: "utf8",
    },
  );

  assert.equal(
    result.status,
    0,
    result.stderr || result.stdout,
  );

  return result.stdout;
}

function baseReports() {
  return {
    "latest-provider-status.json": {
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "HEALTHY",
      safety: {},
    },

    "latest-provider-qualification.json": {
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "HEALTHY",
      job: {
        jobId: "job-001",
      },
      qualification: "STRONG_MATCH",
      trusted: true,
      artifact: "TRUSTED_ARTIFACT",
      safety: {},
    },

    "latest-provider-decision.json": {
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "HEALTHY",
      decision: "QUALIFIED",
      job: {
        jobId: "job-001",
      },
      safety: {},
      executionAuthorized: false,
    },

    "latest-provider-preflight.json": {
      version: "1.0.0",
      mode: "READ_ONLY",
      state: "HEALTHY",
      preflightState: "READY_READ_ONLY",
      job: {
        jobId: "job-001",
      },
      safety: {},
      executionAuthorized: false,
    },

    "latest-provider-audit.json": {
      version: "1.0.0",
      mode: "READ_ONLY",
      auditState: "READY_READ_ONLY",
      job: {
        jobId: "job-001",
      },
      safety: {},
      executionAuthorized: false,
    },
  };
}

async function buildCompleteFixture(dir) {
  const reports = baseReports();

  for (const name of SOURCE_REPORTS) {
    await writeJson(dir, name, reports[name]);
  }

  const auditRaw = await fs.readFile(
    path.join(
      dir,
      "latest-provider-audit.json",
    ),
    "utf8",
  );

  await writeJson(
    dir,
    EVIDENCE,
    {
      version: "1.1.0",
      mode: "READ_ONLY",
      evidenceState: "COMPLETE",
      auditBinding: {
        auditExists: true,
        auditSha256: sha256(auditRaw),
        auditState: "READY_READ_ONLY",
        executionAuthorized: false,
      },
      executionAuthorized: false,
      safety: {
        postPerformed: false,
        walletUsed: false,
        signingPerformed: false,
        broadcastPerformed: false,
        submissionPerformed: false,
      },
      sideEffects: {
        postPerformed: false,
        walletUsed: false,
        signingPerformed: false,
        broadcastPerformed: false,
        submissionPerformed: false,
      },
    },
  );
}

async function scenarioIncomplete() {
  const dir = await fs.mkdtemp(
    path.join(
      os.tmpdir(),
      "aacp-verifier-incomplete-",
    ),
  );

  try {
    await writeJson(
      dir,
      "latest-provider-audit.json",
      {
        mode: "READ_ONLY",
        auditState: "INCOMPLETE",
        executionAuthorized: false,
      },
    );

    const out = runVerifier(dir);

    assert.match(
      out,
      /VERIFICATION=INCOMPLETE/,
    );
  } finally {
    await fs.rm(dir, {
      recursive: true,
      force: true,
    });
  }
}

async function scenarioComplete() {
  const dir = await fs.mkdtemp(
    path.join(
      os.tmpdir(),
      "aacp-verifier-complete-",
    ),
  );

  try {
    await buildCompleteFixture(dir);

    const out = runVerifier(dir);

    assert.match(
      out,
      /VERIFICATION=VERIFIED/,
    );

    assert.match(
      out,
      /REPORTS=5\/5/,
    );

    assert.match(
      out,
      /INTEGRITY=VALID/,
    );

    assert.match(
      out,
      /AUDIT_SHA=VALID/,
    );
  } finally {
    await fs.rm(dir, {
      recursive: true,
      force: true,
    });
  }
}

async function scenarioModifiedAudit() {
  const dir = await fs.mkdtemp(
    path.join(
      os.tmpdir(),
      "aacp-verifier-modified-audit-",
    ),
  );

  try {
    await buildCompleteFixture(dir);

    const auditPath = path.join(
      dir,
      "latest-provider-audit.json",
    );

    const audit = await readJson(
      dir,
      "latest-provider-audit.json",
    );

    audit.auditState = "BLOCKED";

    await fs.writeFile(
      auditPath,
      `${JSON.stringify(audit, null, 2)}\n`,
      "utf8",
    );

    const out = runVerifier(dir);

    assert.match(
      out,
      /VERIFICATION=BLOCKED/,
    );

    assert.match(
      out,
      /AUDIT_SHA=INVALID/,
    );
  } finally {
    await fs.rm(dir, {
      recursive: true,
      force: true,
    });
  }
}

async function scenarioForgedEvidenceSha() {
  const dir = await fs.mkdtemp(
    path.join(
      os.tmpdir(),
      "aacp-verifier-forged-sha-",
    ),
  );

  try {
    await buildCompleteFixture(dir);

    const evidence = await readJson(
      dir,
      EVIDENCE,
    );

    evidence.auditBinding.auditSha256 =
      "0000000000000000000000000000000000000000000000000000000000000000";

    await writeJson(
      dir,
      EVIDENCE,
      evidence,
    );

    const out = runVerifier(dir);

    assert.match(
      out,
      /VERIFICATION=BLOCKED/,
    );

    assert.match(
      out,
      /AUDIT_SHA=INVALID/,
    );
  } finally {
    await fs.rm(dir, {
      recursive: true,
      force: true,
    });
  }
}

async function scenarioUnsafeAudit() {
  const dir = await fs.mkdtemp(
    path.join(
      os.tmpdir(),
      "aacp-verifier-unsafe-",
    ),
  );

  try {
    await buildCompleteFixture(dir);

    const audit = await readJson(
      dir,
      "latest-provider-audit.json",
    );

    audit.safety = {
      signingPerformed: true,
    };

    await writeJson(
      dir,
      "latest-provider-audit.json",
      audit,
    );

    const out = runVerifier(dir);

    assert.match(
      out,
      /VERIFICATION=BLOCKED/,
    );
  } finally {
    await fs.rm(dir, {
      recursive: true,
      force: true,
    });
  }
}

async function scenarioExecutionAuthorized() {
  const dir = await fs.mkdtemp(
    path.join(
      os.tmpdir(),
      "aacp-verifier-exec-auth-",
    ),
  );

  try {
    await buildCompleteFixture(dir);

    const evidence = await readJson(
      dir,
      EVIDENCE,
    );

    evidence.executionAuthorized = true;

    await writeJson(
      dir,
      EVIDENCE,
      evidence,
    );

    const out = runVerifier(dir);

    assert.match(
      out,
      /VERIFICATION=BLOCKED|VERIFICATION=INCOMPLETE/,
    );

    const verification = await readJson(
      dir,
      "latest-provider-verification.json",
    );

    assert.equal(
      verification.executionAuthorized,
      false,
    );
  } finally {
    await fs.rm(dir, {
      recursive: true,
      force: true,
    });
  }
}

async function scenarioNonReadOnly() {
  const dir = await fs.mkdtemp(
    path.join(
      os.tmpdir(),
      "aacp-verifier-mode-",
    ),
  );

  try {
    await buildCompleteFixture(dir);

    const audit = await readJson(
      dir,
      "latest-provider-audit.json",
    );

    audit.mode = "EXECUTE";

    await writeJson(
      dir,
      "latest-provider-audit.json",
      audit,
    );

    const out = runVerifier(dir);

    assert.match(
      out,
      /VERIFICATION=BLOCKED/,
    );
  } finally {
    await fs.rm(dir, {
      recursive: true,
      force: true,
    });
  }
}

async function scenarioGeneratedReport() {
  const dir = await fs.mkdtemp(
    path.join(
      os.tmpdir(),
      "aacp-verifier-generated-",
    ),
  );

  try {
    await buildCompleteFixture(dir);

    runVerifier(dir);

    const verificationPath = path.join(
      dir,
      "latest-provider-verification.json",
    );

    const stat = await fs.stat(
      verificationPath,
    );

    assert.ok(stat.isFile());

    const verification =
      await readJson(
        dir,
        "latest-provider-verification.json",
      );

    assert.equal(
      verification.mode,
      "READ_ONLY",
    );

    assert.equal(
      verification.executionAuthorized,
      false,
    );
  } finally {
    await fs.rm(dir, {
      recursive: true,
      force: true,
    });
  }
}

console.log(
  "AACP PROVIDER VERIFIER REGRESSION",
);

await scenarioIncomplete();
console.log(
  "PASS: missing reports → INCOMPLETE",
);

await scenarioComplete();
console.log(
  "PASS: complete evidence → VERIFIED",
);

await scenarioModifiedAudit();
console.log(
  "PASS: modified audit → BLOCKED",
);

await scenarioForgedEvidenceSha();
console.log(
  "PASS: forged audit SHA → BLOCKED",
);

await scenarioUnsafeAudit();
console.log(
  "PASS: unsafe audit → BLOCKED",
);

await scenarioExecutionAuthorized();
console.log(
  "PASS: executionAuthorized=true → BLOCKED",
);

await scenarioNonReadOnly();
console.log(
  "PASS: non-READ_ONLY report → BLOCKED",
);

await scenarioGeneratedReport();
console.log(
  "PASS: verification report generated",
);

console.log(
  "PASS: executionAuthorized=false",
);

console.log(
  "ALL PROVIDER VERIFIER TESTS PASSED",
);
