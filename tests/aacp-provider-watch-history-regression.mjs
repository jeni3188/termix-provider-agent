import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = process.cwd();

const ENGINE = path.join(
  ROOT,
  "src/aacp-provider-watch-history.mjs"
);

const tmp = fs.mkdtempSync(
  path.join(
    os.tmpdir(),
    "termix-provider-watch-history-"
  )
);

const outputDir = path.join(
  tmp,
  "aacp-observer"
);

const watchFile = path.join(
  outputDir,
  "latest-provider-watch.json"
);

const historyFile = path.join(
  outputDir,
  "latest-provider-watch-history.json"
);

function writeWatch(data) {
  fs.mkdirSync(outputDir, {
    recursive: true,
  });

  fs.writeFileSync(
    watchFile,
    `${JSON.stringify(data, null, 2)}\n`,
    "utf8"
  );
}

function runEngine() {
  const result = spawnSync(
    process.execPath,
    [ENGINE],
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
    `engine failed:\n${result.stdout}\n${result.stderr}`
  );

  assert.ok(
    fs.existsSync(historyFile)
  );

  return JSON.parse(
    fs.readFileSync(
      historyFile,
      "utf8"
    )
  );
}

function baseWatch(state) {
  return {
    version: "1.0.0",
    generatedAt: new Date().toISOString(),
    mode: "READ_ONLY",
    state,
    previousState: null,
    changed: true,

    lifecycle: {
      exists: true,
      valid: true,
      sourceState: state,
      reason: `test ${state}`,
    },

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

    executionAuthorized: false,
  };
}

console.log(
  "AACP PROVIDER WATCH HISTORY REGRESSION"
);

fs.rmSync(tmp, {
  recursive: true,
  force: true,
});

writeWatch(
  baseWatch("INCOMPLETE")
);

{
  const history = runEngine();

  assert.equal(
    history.events.length,
    1
  );

  assert.equal(
    history.events[0].state,
    "INCOMPLETE"
  );

  assert.equal(
    history.events[0].changed,
    true
  );

  console.log(
    "PASS: initial snapshot recorded"
  );
}

{
  const history = runEngine();

  assert.equal(
    history.events.length,
    2
  );

  assert.equal(
    history.events[1].changed,
    false
  );

  assert.deepEqual(
    history.events[1].changedFields,
    []
  );

  console.log(
    "PASS: unchanged snapshot → changed=false"
  );
}

writeWatch(
  baseWatch("VERIFIED_READ_ONLY")
);

{
  const history = runEngine();

  assert.equal(
    history.events.length,
    3
  );

  assert.equal(
    history.events[2].state,
    "VERIFIED_READ_ONLY"
  );

  assert.equal(
    history.events[2].changed,
    true
  );

  assert.ok(
    history.events[2]
      .changedFields
      .includes("state")
  );

  console.log(
    "PASS: state transition detected"
  );
}

{
  const unsafe = baseWatch(
    "VERIFIED_READ_ONLY"
  );

  unsafe.safety.signingPerformed = true;

  writeWatch(unsafe);

  const history = runEngine();
  const event =
    history.events[
      history.events.length - 1
    ];

  assert.equal(
    event.state,
    "BLOCKED"
  );

  assert.equal(
    event.executionAuthorized,
    false
  );

  console.log(
    "PASS: unsafe signing → BLOCKED"
  );
}

{
  const history = JSON.parse(
    fs.readFileSync(
      historyFile,
      "utf8"
    )
  );

  for (const event of history.events) {
    assert.equal(
      event.executionAuthorized,
      false
    );

    assert.equal(
      event.safety.walletUsed,
      false
    );

    assert.equal(
      event.safety.signingPerformed,
      false
    );

    assert.equal(
      event.safety.broadcastPerformed,
      false
    );

    assert.equal(
      event.safety.submissionPerformed,
      false
    );
  }

  console.log(
    "PASS: history safety invariants"
  );

  assert.ok(
    history.events.every(
      (event) =>
        typeof event.watch.sha256 === "string" ||
        event.watch.sha256 === null
    )
  );

  console.log(
    "PASS: SHA-256 fingerprints recorded"
  );
}

fs.rmSync(tmp, {
  recursive: true,
  force: true,
});

console.log(
  "ALL PROVIDER WATCH HISTORY TESTS PASSED"
);
