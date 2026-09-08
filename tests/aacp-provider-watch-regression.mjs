import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();
const WATCHER = path.join(ROOT, "src/aacp-provider-watch.mjs");

const tmp = fs.mkdtempSync(
  path.join(os.tmpdir(), "termix-provider-watch-")
);

const outputDir = path.join(tmp, "aacp-observer");
const lifecycleFile = path.join(
  outputDir,
  "latest-provider-lifecycle.json"
);
const watchFile = path.join(
  outputDir,
  "latest-provider-watch.json"
);

function writeLifecycle(data) {
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(
    lifecycleFile,
    `${JSON.stringify(data, null, 2)}\n`,
    "utf8"
  );
}

function runWatcher() {
  const result = spawnSync(
    process.execPath,
    [WATCHER],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AACP_OBSERVER_OUTPUT: outputDir,
      },
      encoding: "utf8",
    }
  );

  assert.equal(
    result.status,
    0,
    `watcher failed:\n${result.stdout}\n${result.stderr}`
  );

  assert.ok(fs.existsSync(watchFile));

  return JSON.parse(
    fs.readFileSync(watchFile, "utf8")
  );
}

function baseLifecycle(state) {
  return {
    version: "1.0.0",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    lifecycle: state,
    reason: `test ${state}`,
    executionAuthorized: false,
    safety: {
      executionAuthorized: false,
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
  };
}

console.log("AACP PROVIDER WATCH REGRESSION");

for (const state of [
  "INCOMPLETE",
  "BACKEND_UNAVAILABLE",
  "BLOCKED",
  "READY_READ_ONLY",
  "VERIFIED_READ_ONLY",
]) {
  fs.rmSync(watchFile, { force: true });
  writeLifecycle(baseLifecycle(state));

  const report = runWatcher();

  assert.equal(report.state, state);
  assert.equal(report.lifecycle.sourceState, state);
  assert.equal(report.executionAuthorized, false);

  console.log(`PASS: ${state} preserved`);
}

writeLifecycle({
  ...baseLifecycle("VERIFIED_READ_ONLY"),
  mode: "EXECUTE",
});

{
  const report = runWatcher();
  assert.equal(report.state, "BLOCKED");
  console.log("PASS: non-READ_ONLY mode → BLOCKED");
}

writeLifecycle({
  ...baseLifecycle("VERIFIED_READ_ONLY"),
  executionAuthorized: true,
});

{
  const report = runWatcher();
  assert.equal(report.state, "BLOCKED");
  assert.equal(report.executionAuthorized, false);
  console.log("PASS: executionAuthorized=true → BLOCKED");
}

for (const field of [
  "walletUsed",
  "signingPerformed",
  "broadcastPerformed",
  "submissionPerformed",
]) {
  const lifecycle = baseLifecycle("VERIFIED_READ_ONLY");
  lifecycle.safety[field] = true;

  writeLifecycle(lifecycle);

  const report = runWatcher();

  assert.equal(report.state, "BLOCKED");
  assert.equal(report.executionAuthorized, false);

  console.log(`PASS: ${field}=true → BLOCKED`);
}

fs.rmSync(watchFile, { force: true });
writeLifecycle(baseLifecycle("INCOMPLETE"));

{
  const first = runWatcher();

  assert.equal(first.previousState, null);
  assert.equal(first.changed, true);

  const second = runWatcher();

  assert.equal(second.previousState, "INCOMPLETE");
  assert.equal(second.changed, false);

  console.log("PASS: unchanged state → changed=false");
}

writeLifecycle(baseLifecycle("VERIFIED_READ_ONLY"));

{
  const report = runWatcher();

  assert.equal(report.previousState, "INCOMPLETE");
  assert.equal(report.changed, true);
  assert.equal(report.state, "VERIFIED_READ_ONLY");

  console.log("PASS: state transition → changed=true");
}

assert.ok(fs.existsSync(watchFile));

{
  const report = JSON.parse(
    fs.readFileSync(watchFile, "utf8")
  );

  assert.equal(report.mode, "READ_ONLY");
  assert.equal(report.executionAuthorized, false);

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

  console.log("PASS: watcher safety invariants");
  console.log("PASS: watcher report generated");
  console.log("PASS: executionAuthorized=false");
}

fs.rmSync(tmp, {
  recursive: true,
  force: true,
});

console.log("ALL PROVIDER WATCH TESTS PASSED");
