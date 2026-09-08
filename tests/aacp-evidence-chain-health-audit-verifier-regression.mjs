import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const ROOT = path.resolve(
  path.dirname(new URL(import.meta.url).pathname),
  ".."
);

const SRC = path.join(
  ROOT,
  "src",
  "aacp-evidence-chain-health-audit-verifier.mjs"
);

const POLICY = {
  readOnly: true,
  failClosed: true,
  post: "NOT_PERFORMED",
  wallet: "NOT_USED",
  signing: "NOT_PERFORMED",
  broadcast: "NOT_PERFORMED",
  submission: "NOT_PERFORMED",
};

const SAFETY = {
  postPerformed: false,
  walletUsed: false,
  signingPerformed: false,
  broadcastPerformed: false,
  submissionPerformed: false,
};

function tmp() {
  return fs.mkdtempSync(
    path.join(
      os.tmpdir(),
      "aacp-health-audit-verify-"
    )
  );
}

function writeJson(file, data) {
  fs.writeFileSync(
    file,
    JSON.stringify(data, null, 2) + "\n",
    "utf8"
  );
}

function sha256File(file) {
  return crypto
    .createHash("sha256")
    .update(fs.readFileSync(file))
    .digest("hex");
}

function run(dir) {
  const result = spawnSync(
    process.execPath,
    [SRC],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OUTPUT_DIR: dir,
      },
      encoding: "utf8",
    }
  );

  const output = path.join(
    dir,
    "latest-aacp-evidence-chain-health-audit-verify.json"
  );

  if (!fs.existsSync(output)) {
    throw new Error(
      `missing verifier output\nSTDOUT:\n${result.stdout}\nSTDERR:\n${result.stderr}`
    );
  }

  return {
    result,
    report: JSON.parse(
      fs.readFileSync(output, "utf8")
    ),
  };
}

function expectState(label, report, expected) {
  if (report.state !== expected) {
    throw new Error(
      `${label}: expected ${expected}, got ${report.state}\n` +
      JSON.stringify(report.verification, null, 2)
    );
  }
}

function baseAudit({
  state = "VERIFIED_READ_ONLY",
  sourceState = state,
  valid = true,
  errors = [],
} = {}) {
  return {
    version: "1.0.0",
    type: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state,
    sourceState,
    executionAuthorized: false,
    safety: { ...SAFETY },
    sideEffects: { ...SAFETY },
    audit: {
      valid,
      findings:
        state === "INCOMPLETE"
          ? ["CHAIN_INCOMPLETE", "ARTIFACTS_MISSING"]
          : ["CHAIN_VERIFIED"],
      errors,
      errorCount: errors.length,
    },
    policy: { ...POLICY },
  };
}

function createChain(dir, options = {}) {
  const healthFile = path.join(
    dir,
    "latest-aacp-evidence-chain-health.json"
  );

  const verifyFile = path.join(
    dir,
    "latest-aacp-evidence-chain-health-verify.json"
  );

  writeJson(healthFile, {
    fixture: "health",
    state: "INCOMPLETE",
  });

  writeJson(verifyFile, {
    fixture: "verify",
    state: "INCOMPLETE",
  });

  const audit = baseAudit(options);

  audit.sources = {
    health: {
      file: "latest-aacp-evidence-chain-health.json",
      exists: true,
      sha256: sha256File(healthFile),
    },
    verify: {
      file: "latest-aacp-evidence-chain-health-verify.json",
      exists: true,
      sha256: sha256File(verifyFile),
    },
  };

  if (options.sourceHealthSha256) {
    audit.sources.health.sha256 =
      options.sourceHealthSha256;
  }

  if (options.sourceVerifySha256) {
    audit.sources.verify.sha256 =
      options.sourceVerifySha256;
  }

  writeJson(
    path.join(
      dir,
      "latest-aacp-evidence-chain-health-audit.json"
    ),
    audit
  );
}

function mutateAudit(dir, mutate) {
  const file = path.join(
    dir,
    "latest-aacp-evidence-chain-health-audit.json"
  );

  const audit = JSON.parse(
    fs.readFileSync(file, "utf8")
  );

  mutate(audit);

  writeJson(file, audit);
}

function execute(label, expected, setup) {
  const dir = tmp();

  setup(dir);

  const { report } = run(dir);

  expectState(label, report, expected);

  return { dir, report };
}

/* 1. Complete verified audit */
execute(
  "safe verified audit",
  "VERIFIED_READ_ONLY",
  (dir) => {
    createChain(dir, {
      state: "VERIFIED_READ_ONLY",
      sourceState: "VERIFIED_READ_ONLY",
      valid: true,
    });
  }
);

/* 2. Legitimate incomplete audit */
execute(
  "safe incomplete audit",
  "INCOMPLETE",
  (dir) => {
    createChain(dir, {
      state: "INCOMPLETE",
      sourceState: "INCOMPLETE",
      valid: true,
    });
  }
);

/* 3. Missing Phase 25 audit */
execute(
  "missing source",
  "INCOMPLETE",
  () => {}
);

/* 4. Invalid JSON */
execute(
  "invalid JSON",
  "BLOCKED",
  (dir) => {
    fs.writeFileSync(
      path.join(
        dir,
        "latest-aacp-evidence-chain-health-audit.json"
      ),
      "{invalid-json",
      "utf8"
    );
  }
);

/* 5-9. Safety violations */
for (const field of [
  "executionAuthorized",
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
]) {
  execute(
    `safety violation ${field}`,
    "BLOCKED",
    (dir) => {
      createChain(dir);

      mutateAudit(dir, (audit) => {
        if (field === "executionAuthorized") {
          audit.executionAuthorized = true;
        } else {
          audit.safety[field] = true;
        }
      });
    }
  );
}

/* 10. Policy violation */
execute(
  "policy violation",
  "BLOCKED",
  (dir) => {
    createChain(dir);

    mutateAudit(dir, (audit) => {
      audit.policy.readOnly = false;
    });
  }
);

/* 11. Side effect violation */
execute(
  "side effect violation",
  "BLOCKED",
  (dir) => {
    createChain(dir);

    mutateAudit(dir, (audit) => {
      audit.sideEffects.postPerformed = true;
    });
  }
);

/* 12. State/sourceState mismatch */
execute(
  "state sourceState mismatch",
  "BLOCKED",
  (dir) => {
    createChain(dir);

    mutateAudit(dir, (audit) => {
      audit.sourceState = "INCOMPLETE";
    });
  }
);

/* 13. Audit error count mismatch */
execute(
  "audit error count mismatch",
  "BLOCKED",
  (dir) => {
    createChain(dir);

    mutateAudit(dir, (audit) => {
      audit.audit.errors = ["BROKEN"];
      audit.audit.errorCount = 0;
    });
  }
);

/* 14. BLOCKED without errors */
execute(
  "blocked without errors",
  "BLOCKED",
  (dir) => {
    createChain(dir, {
      state: "BLOCKED",
      sourceState: "BLOCKED",
      valid: false,
    });
  }
);

/* 15. Errors without BLOCKED */
execute(
  "errors without blocked",
  "BLOCKED",
  (dir) => {
    createChain(dir, {
      state: "INCOMPLETE",
      sourceState: "INCOMPLETE",
      valid: true,
      errors: ["BROKEN"],
    });
  }
);

/* 16. Source health SHA mismatch */
execute(
  "health source SHA mismatch",
  "BLOCKED",
  (dir) => {
    createChain(dir, {
      sourceHealthSha256: "a".repeat(64),
    });
  }
);

/* 17. Source verify SHA mismatch */
execute(
  "verify source SHA mismatch",
  "BLOCKED",
  (dir) => {
    createChain(dir, {
      sourceVerifySha256: "b".repeat(64),
    });
  }
);

/* 18. Invalid sources schema */
execute(
  "invalid sources schema",
  "BLOCKED",
  (dir) => {
    createChain(dir);

    mutateAudit(dir, (audit) => {
      delete audit.sources;
    });
  }
);

/* 19. Invalid source exists/SHA */
execute(
  "source exists without SHA",
  "BLOCKED",
  (dir) => {
    createChain(dir);

    mutateAudit(dir, (audit) => {
      audit.sources.health.sha256 = null;
    });
  }
);

/* 20. Incomplete + valid=true is explicitly allowed */
execute(
  "incomplete valid audit",
  "INCOMPLETE",
  (dir) => {
    createChain(dir, {
      state: "INCOMPLETE",
      sourceState: "INCOMPLETE",
      valid: true,
    });
  }
);

/* 21. Verified audit requires valid=true */
execute(
  "verified without valid audit",
  "BLOCKED",
  (dir) => {
    createChain(dir, {
      state: "VERIFIED_READ_ONLY",
      sourceState: "VERIFIED_READ_ONLY",
      valid: false,
    });
  }
);

/* 22. Policy invariant output */
{
  const dir = tmp();

  createChain(dir, {
    state: "INCOMPLETE",
    sourceState: "INCOMPLETE",
    valid: true,
  });

  const { report } = run(dir);

  if (
    report.mode !== "READ_ONLY" ||
    report.executionAuthorized !== false ||
    JSON.stringify(report.safety) !==
      JSON.stringify(SAFETY) ||
    JSON.stringify(report.sideEffects) !==
      JSON.stringify(SAFETY) ||
    JSON.stringify(report.policy) !==
      JSON.stringify(POLICY)
  ) {
    throw new Error(
      "output policy/safety invariants failed"
    );
  }
}

console.log(
  "ALL PROVIDER EVIDENCE CHAIN HEALTH AUDIT VERIFIER TESTS PASSED"
);
