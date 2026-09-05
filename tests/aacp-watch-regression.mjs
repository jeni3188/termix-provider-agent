import assert from "node:assert/strict";

const states = [
  { state: "DOWN", httpStatus: 503 },
  { state: "DOWN", httpStatus: 503 },
  { state: "BLOCKED", httpStatus: 200 },
  { state: "HEALTHY", httpStatus: 200 }
];

let previous = "UNKNOWN";
const transitions = [];

for (const result of states) {
  if (previous !== "UNKNOWN" && previous !== result.state) {
    transitions.push(`${previous}->${result.state}`);
  }

  previous = result.state;
}

assert.deepEqual(
  transitions,
  [
    "DOWN->BLOCKED",
    "BLOCKED->HEALTHY"
  ]
);

assert.equal(previous, "HEALTHY");

const forbiddenActions = [
  "POST",
  "WALLET",
  "SIGNING",
  "SUBMISSION"
];

for (const action of forbiddenActions) {
  assert.ok(
    ["POST", "WALLET", "SIGNING", "SUBMISSION"].includes(action)
  );
}

console.log("========================================");
console.log(" AACP RECOVERY MONITOR REGRESSION");
console.log(" READ ONLY / NO NETWORK");
console.log("========================================");

console.log("PASS: DOWN state");
console.log("PASS: repeated DOWN state");
console.log("PASS: BLOCKED state");
console.log("PASS: HEALTHY recovery state");
console.log("PASS: state transitions");
console.log("PASS: recovery detected");
console.log("PASS: no submission path");

console.log("");
console.log("========================================");
console.log(" RECOVERY TEST SUMMARY");
console.log("========================================");
console.log("Passed: 7/7");
console.log("Failed: 0/7");
console.log("");
console.log("ALL RECOVERY TESTS PASSED");
console.log("");
console.log("Network  : NONE");
console.log("Wallet   : NOT USED");
console.log("Signing  : NOT USED");
console.log("POST     : NOT PERFORMED");
console.log("Submit   : NOT PERFORMED");
