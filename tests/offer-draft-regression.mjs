import fs from "fs";
import { execFileSync } from "child_process";

const fair =
  "provider-output/demo-security-fair-001/processor-result.json";

const under =
  "provider-output/demo-security-001/processor-result.json";

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`PASS: ${name}`);
    passed++;
  } catch (e) {
    console.log(`FAIL: ${name}`);
    console.log(`      ${e.message}`);
    failed++;
  }
}

test("FAIR job creates offer draft", () => {
  execFileSync(
    process.execPath,
    ["src/offer-draft.mjs", fair],
    { encoding: "utf8" }
  );

  const file =
    "provider-output/demo-security-fair-001/OFFER-DRAFT.json";

  const data =
    JSON.parse(fs.readFileSync(file, "utf8"));

  if (
    data.review.status !==
    "PENDING_MANUAL_REVIEW"
  ) {
    throw new Error(
      `Unexpected review status: ${data.review.status}`
    );
  }

  if (
    data.pricing.proposedPriceUSDC !== 500
  ) {
    throw new Error(
      `Unexpected price: ${data.pricing.proposedPriceUSDC}`
    );
  }

  if (
    data.execution.offerSubmitted !== false
  ) {
    throw new Error(
      "Offer submission flag is not false"
    );
  }
});

test("UNDERVALUED job is blocked", () => {
  try {
    execFileSync(
      process.execPath,
      ["src/offer-draft.mjs", under],
      { encoding: "utf8" }
    );

    throw new Error(
      "Expected offer draft to be blocked"
    );
  } catch (e) {
    if (e.status !== 2) {
      throw e;
    }
  }
});

console.log("");
console.log("========================================");
console.log(" OFFER DRAFT REGRESSION");
console.log("========================================");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed > 0) {
  process.exit(1);
}

console.log("");
console.log("ALL OFFER DRAFT TESTS PASSED");
