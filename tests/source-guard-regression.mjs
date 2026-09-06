import fs from "node:fs";
import { spawnSync } from "node:child_process";

const root = process.cwd();
const intake = "/tmp/source-guard-intake.json";
const source = "samples/Vulnerable.sol";

fs.writeFileSync(
  intake,
  JSON.stringify({
    summary: {
      backendAvailable: false
    },
    jobs: []
  }, null, 2)
);

let passed = 0;
let failed = 0;

function check(name, condition) {
  if (condition) {
    console.log(`PASS: ${name}`);
    passed++;
  } else {
    console.log(`FAIL: ${name}`);
    failed++;
  }
}

console.log("========================================");
console.log(" TERMIX SOURCE GUARD REGRESSION");
console.log(" READ ONLY / NO NETWORK");
console.log("========================================");

// ------------------------------------------------------------
// 1. Production without source must be blocked
// ------------------------------------------------------------

const noSource = spawnSync(
  process.execPath,
  ["src/auto-processor.mjs", intake],
  {
    cwd: root,
    encoding: "utf8"
  }
);

check(
  "no source exits with code 2",
  noSource.status === 2
);

check(
  "no source emits SOURCE_REQUIRED",
  `${noSource.stdout}\n${noSource.stderr}`
    .includes("SOURCE_REQUIRED")
);

// ------------------------------------------------------------
// 2. Production with explicit source must be allowed
// ------------------------------------------------------------

const explicitSource = spawnSync(
  process.execPath,
  [
    "src/auto-processor.mjs",
    intake,
    source
  ],
  {
    cwd: root,
    encoding: "utf8"
  }
);

const explicitOutput =
  `${explicitSource.stdout}\n${explicitSource.stderr}`;

check(
  "explicit source does not trigger SOURCE_REQUIRED",
  !explicitOutput.includes("SOURCE_REQUIRED")
);

check(
  "explicit source reaches normal intake handling",
  explicitOutput.includes("Backend available")
);

// ------------------------------------------------------------
// 3. Simulation without source must still be blocked
// ------------------------------------------------------------

const simulationNoSource = spawnSync(
  process.execPath,
  [
    "src/auto-processor.mjs",
    intake
  ],
  {
    cwd: root,
    encoding: "utf8",
    env: {
      ...process.env,
      PROVIDER_DAEMON_SIMULATION: "1"
    }
  }
);

const simulationOutput =
  `${simulationNoSource.stdout}\n${simulationNoSource.stderr}`;

check(
  "simulation without source exits with code 2",
  simulationNoSource.status === 2
);

check(
  "simulation without source emits SIMULATION_SOURCE_REQUIRED",
  simulationOutput.includes("SIMULATION_SOURCE_REQUIRED")
);

// ------------------------------------------------------------
// Summary
// ------------------------------------------------------------

console.log("");
console.log("========================================");
console.log(" SOURCE GUARD SUMMARY");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

fs.rmSync(intake, { force: true });

if (failed === 0) {
  console.log("");
  console.log("ALL SOURCE GUARD TESTS PASSED");
  console.log("");
  console.log("Sample fallback : BLOCKED");
  console.log("Explicit source : ALLOWED");
  console.log("Network         : NONE");
  console.log("Wallet          : NOT USED");
  process.exit(0);
}

console.log("");
console.log("SOURCE GUARD TEST FAILED");
process.exit(1);
