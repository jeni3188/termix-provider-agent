import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";

const repoRoot = process.cwd();
const watcherPath = path.resolve(repoRoot, "src/aacp-watch.mjs");
const tempDir = fs.mkdtempSync(
  path.join(os.tmpdir(), "termix-watch-production-")
);

const preloadFile = path.join(tempDir, "mock-fetch.mjs");

const preloadSource = `
let configCalls = 0;

const recoveryJob = {
  jobId: "integration-production-recovery-001",
  status: "OPEN",
  strategyType: "PROGRAM",
  budget: "500000000",
  title: "Production Recovery Path Security Audit",
  description: "Mock production recovery path job",
  deadline: 1799000000,
  providerId: null
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json"
    }
  });
}

globalThis.fetch = async (url, options = {}) => {
  const method = options.method || "GET";

  if (method !== "GET") {
    throw new Error(
      "FORBIDDEN_NON_GET_METHOD:" + method
    );
  }

  const value = String(url);

  if (value.endsWith("/config")) {
    configCalls++;

    if (configCalls === 1) {
      return new Response(
        "<html>Service Unavailable</html>",
        {
          status: 503,
          headers: {
            "content-type": "text/html"
          }
        }
      );
    }

    return json({
      chainId: 97,
      network: "bsc-testnet"
    });
  }

  if (value.includes("status=OPEN")) {
    return json({
      jobs: [recoveryJob]
    });
  }

  if (value.includes("status=FUNDED")) {
    return json({
      jobs: []
    });
  }

  throw new Error(
    "UNEXPECTED_MOCK_URL:" + value
  );
};
`;

fs.writeFileSync(
  preloadFile,
  preloadSource,
  "utf8"
);

function cleanup() {
  fs.rmSync(tempDir, {
    recursive: true,
    force: true
  });
}

function runWatcher() {
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [watcherPath],
      {
        cwd: tempDir,
        env: {
          ...process.env,
          AACP_WATCH_TEST: "",
          TERMIX_AACP_URL: "https://mock.aacp.local",
          AACP_WATCH_INTERVAL_MS: "50",
          AACP_WATCH_TIMEOUT_MS: "1000",
          NODE_OPTIONS: [
            process.env.NODE_OPTIONS || "",
            "--import=" + preloadFile
          ]
            .filter(Boolean)
            .join(" ")
        },
        stdio: [
          "ignore",
          "pipe",
          "pipe"
        ]
      }
    );

    let stdout = "";
    let stderr = "";
    let finished = false;

    const timeout = setTimeout(() => {
      if (!finished) {
        finished = true;
        child.kill("SIGTERM");
        reject(
          new Error(
            [
              "production watcher timeout",
              "",
              "--- stdout ---",
              stdout,
              "",
              "--- stderr ---",
              stderr
            ].join("\\n")
          )
        );
      }
    }, 5000);

    function finish(error = null) {
      if (finished) return;

      finished = true;
      clearTimeout(timeout);

      if (error) {
        reject(error);
      } else {
        resolve({
          stdout,
          stderr
        });
      }
    }

    child.stdout.on("data", data => {
      stdout += data.toString();

      if (
        stdout.includes(
          "QUALIFIED_JOB_REPORT="
        )
      ) {
        child.kill("SIGTERM");
      }
    });

    child.stderr.on("data", data => {
      stderr += data.toString();
    });

    child.on("error", finish);

    child.on("close", () => {
      if (
        stdout.includes(
          "QUALIFIED_JOB_REPORT="
        )
      ) {
        finish();
        return;
      }

      finish(
        new Error(
          [
            "watcher exited without qualified report",
            "",
            "--- stdout ---",
            stdout,
            "",
            "--- stderr ---",
            stderr
          ].join("\\n")
        )
      );
    });
  });
}

try {
  const result = await runWatcher();

  assert.match(
    result.stdout,
    /AACP_RECOVERED/
  );

  assert.match(
    result.stdout,
    /ACTION=READ_ONLY_DISCOVERY_ALLOWED/
  );

  assert.match(
    result.stdout,
    /QUALIFIED_JOB_REPORT=/
  );

  assert.doesNotMatch(
    result.stdout,
    /FORBIDDEN_NON_GET_METHOD/
  );

  const reportMatch = result.stdout.match(
    /QUALIFIED_JOB_REPORT=(\S+)/
  );

  assert.ok(
    reportMatch,
    "qualified report marker must exist"
  );

  const reportPath = path.resolve(
    tempDir,
    reportMatch[1]
  );

  assert.ok(
    fs.existsSync(reportPath),
    "qualified report must exist"
  );

  const report = JSON.parse(
    fs.readFileSync(
      reportPath,
      "utf8"
    )
  );

  assert.equal(
    report.mode,
    "READ_ONLY"
  );

  assert.equal(
    report.state,
    "HEALTHY"
  );

  assert.equal(
    report.previousState,
    "DOWN"
  );

  assert.equal(
    report.recovered,
    true
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
    report.summary.blocked,
    1
  );

  assert.equal(
    report.blocked[0].jobId,
    "integration-production-recovery-001"
  );

  assert.equal(
    report.blocked[0].reason,
    "ARTIFACT_MISSING"
  );

  assert.equal(
    report.safety.postPerformed,
    false
  );

  assert.equal(
    report.safety.walletUsed,
    false
  );

  assert.equal(
    report.safety.signingPerformed,
    false
  );

  assert.equal(
    report.safety.broadcastPerformed,
    false
  );

  assert.equal(
    report.safety.submissionPerformed,
    false
  );

  console.log(
    "PASS: production recovery path executes"
  );
  console.log(
    "PASS: AACP_RECOVERED → observer → snapshot → qualification → report"
  );
  console.log(
    "PASS: production recovery path is GET-only"
  );
  console.log(
    "PASS: wallet/signing/broadcast/submission remain disabled"
  );
  console.log("");
  console.log(
    "AACP WATCH PRODUCTION RECOVERY PATH: 4/4 PASS"
  );
} finally {
  cleanup();
}
