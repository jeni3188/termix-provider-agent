import { execFileSync } from "child_process";

const tests = [
  {
    name: "UNDERVALUED job",
    job: "samples/jobs/security-audit.json",
    expectedDecision: "MANUAL_REVIEW",
    expectedPath: "MANUAL_REVIEW"
  },
  {
    name: "FAIR job",
    job: "samples/jobs/security-audit-fair.json",
    expectedDecision: "PROCEED_TO_OFFER_REVIEW",
    expectedPath: "OFFER_REVIEW"
  },
  {
    name: "POOR MATCH job",
    job: "samples/jobs/poor-match.json",
    expectedDecision: "REJECT",
    expectedPath: "REJECT"
  }
];

let failed = 0;

for (const test of tests) {
  console.log(`TEST: ${test.name}`);

  try {
    const raw = execFileSync(
      process.execPath,
      [
        "src/job-processor.mjs",
        test.job,
        "samples/Vulnerable.sol"
      ],
      { encoding: "utf8" }
    );

    const marker =
      "Output   : ";

    const line =
      raw.split("\n")
        .find(x => x.includes(marker));

    if (!line) {
      throw new Error(
        "Processor output path not found."
      );
    }

    const outputPath =
      line.split(marker)[1].trim();

    const fs =
      await import("node:fs");

    const result =
      JSON.parse(
        fs.readFileSync(
          outputPath,
          "utf8"
        )
      );

    const actualDecision =
      result.evaluation.decision.status;

    const actualPath =
      result.execution.path;

    if (
      actualDecision !==
        test.expectedDecision ||
      actualPath !==
        test.expectedPath
    ) {
      throw new Error(
        `Expected ${test.expectedDecision}/${test.expectedPath}, ` +
        `got ${actualDecision}/${actualPath}`
      );
    }

    console.log("  PASS");
    console.log(
      `  ${actualDecision} → ${actualPath}`
    );
    console.log("");

  } catch (error) {
    failed++;

    console.log("  FAIL");
    console.log(
      `  ${error.message}`
    );
    console.log("");
  }
}

console.log("========================================");
console.log(" REGRESSION TEST SUMMARY");
console.log("========================================");

console.log(
  `Passed: ${tests.length - failed}/${tests.length}`
);

console.log(
  `Failed: ${failed}/${tests.length}`
);

if (failed > 0) {
  process.exit(1);
}

console.log("");
console.log("ALL TESTS PASSED");
