import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const stagingRoot = fs.mkdtempSync(
  path.join(os.tmpdir(), "source-router-symlink-")
);

process.env.PROVIDER_SOURCE_STAGING = stagingRoot;

const { resolveSource } =
  await import("../src/source-router.mjs");

const jobId = "symlink-test-job";
const jobRoot = path.join(stagingRoot, jobId);
const outsideRoot = fs.mkdtempSync(
  path.join(os.tmpdir(), "source-router-outside-")
);

fs.mkdirSync(jobRoot, { recursive: true });

const validSource = path.join(jobRoot, "valid.sol");
const outsideSource = path.join(outsideRoot, "outside.sol");
const symlinkSource = path.join(jobRoot, "link.sol");

fs.writeFileSync(
  validSource,
  "pragma solidity ^0.8.0;\ncontract Valid {}\n"
);

fs.writeFileSync(
  outsideSource,
  "pragma solidity ^0.8.0;\ncontract Outside {}\n"
);

fs.symlinkSync(
  outsideSource,
  symlinkSource
);

try {
  const allowed = resolveSource(
    jobId,
    "valid.sol"
  );

  assert.equal(
    allowed.allowed,
    true,
    "legitimate staged source must remain allowed"
  );

  const escaped = resolveSource(
    jobId,
    "link.sol"
  );

  assert.equal(
    escaped.allowed,
    false,
    "symlink escaping staging must be rejected"
  );

  assert.equal(
    escaped.code,
    "SOURCE_REJECTED"
  );

  assert.equal(
    escaped.reason,
    "SYMLINK_ESCAPE_OR_OUTSIDE_STAGING"
  );

  console.log(
    "SOURCE ROUTER SYMLINK REGRESSION: PASS"
  );
} finally {
  fs.rmSync(stagingRoot, {
    recursive: true,
    force: true
  });

  fs.rmSync(outsideRoot, {
    recursive: true,
    force: true
  });
}
