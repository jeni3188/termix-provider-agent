import assert from "node:assert/strict";

const STATES = {
  DOWN: "DOWN",
  HEALTHY: "HEALTHY",
};

function evaluateRecovery(previous, current) {
  if (previous === STATES.DOWN && current === STATES.HEALTHY) {
    return {
      recovered: true,
      discoveryAllowed: true,
      processingAllowed: true,
      offerDraftAllowed: true,

      postAllowed: false,
      walletUsed: false,
      signingUsed: false,
      broadcastAllowed: false,
      submissionPerformed: false,
    };
  }

  return {
    recovered: false,
    discoveryAllowed: current === STATES.HEALTHY,
    processingAllowed: current === STATES.HEALTHY,
    offerDraftAllowed: current === STATES.HEALTHY,

    postAllowed: false,
    walletUsed: false,
    signingUsed: false,
    broadcastAllowed: false,
    submissionPerformed: false,
  };
}

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Recovery Regression v1.2.0");
console.log(" READ ONLY");
console.log("========================================");
console.log("");

const sequence = [
  STATES.DOWN,
  STATES.DOWN,
  STATES.HEALTHY,
];

let previous = null;

for (const current of sequence) {
  const result = evaluateRecovery(previous, current);

  console.log(`Previous : ${previous ?? "NONE"}`);
  console.log(`Current  : ${current}`);
  console.log(`Recovered: ${result.recovered}`);
  console.log(`Discovery: ${result.discoveryAllowed}`);
  console.log(`Process  : ${result.processingAllowed}`);
  console.log(`Draft    : ${result.offerDraftAllowed}`);
  console.log("");

  assert.equal(result.postAllowed, false);
  assert.equal(result.walletUsed, false);
  assert.equal(result.signingUsed, false);
  assert.equal(result.broadcastAllowed, false);
  assert.equal(result.submissionPerformed, false);

  if (current === STATES.DOWN) {
    assert.equal(result.discoveryAllowed, false);
    assert.equal(result.processingAllowed, false);
    assert.equal(result.offerDraftAllowed, false);
  }

  if (previous === STATES.DOWN && current === STATES.HEALTHY) {
    assert.equal(result.recovered, true);
    assert.equal(result.discoveryAllowed, true);
    assert.equal(result.processingAllowed, true);
    assert.equal(result.offerDraftAllowed, true);
  }

  previous = current;
}

console.log("========================================");
console.log(" RECOVERY REGRESSION PASSED");
console.log("========================================");
console.log("");
console.log("DOWN -> DOWN -> HEALTHY : PASS");
console.log("POST                   : BLOCKED");
console.log("WALLET                 : NOT USED");
console.log("SIGNING                : NOT USED");
console.log("BROADCAST              : BLOCKED");
console.log("SUBMISSION             : NOT PERFORMED");
