import assert from "node:assert/strict";

const { observeRecovery } =
  await import("../src/aacp-recovery-observer.mjs");

const healthyPayload = {
  jobs: [
    {
      jobId: "real-like-001",
      status: "OPEN",
      strategyType: "PROGRAM",
      budget: "500000000",
      title: "Smart Contract Audit",
      description: "Audit Solidity contract",
      deadline: 1799000000,
      providerId: null
    }
  ]
};

let getCalls = [];

const fetchMock = async (url, options = {}) => {
  getCalls.push({
    url: String(url),
    method: options.method ?? "GET"
  });

  if (String(url).includes("/api/v1/config")) {
    return new Response(
      JSON.stringify({ chainId: 97 }),
      {
        status: 200,
        headers: { "content-type": "application/json" }
      }
    );
  }

  if (String(url).includes("/api/v1/jobs")) {
    return new Response(
      JSON.stringify(healthyPayload),
      {
        status: 200,
        headers: { "content-type": "application/json" }
      }
    );
  }

  return new Response("not found", { status: 404 });
};

const result = await observeRecovery(fetchMock, {
  previousState: "DOWN"
});

assert.equal(result.recovered, true);
assert.equal(result.state, "HEALTHY");
assert.equal(result.jobs.length, 1);
assert.equal(result.jobs[0].jobId, "real-like-001");

assert.ok(
  getCalls.every((call) => call.method === "GET"),
  "observer must use GET only"
);

assert.equal(result.safety.postPerformed, false);
assert.equal(result.safety.walletUsed, false);
assert.equal(result.safety.signingPerformed, false);
assert.equal(result.safety.broadcastPerformed, false);
assert.equal(result.safety.submissionPerformed, false);

console.log("========================================");
console.log(" AACP RECOVERY OBSERVER REGRESSION");
console.log(" READ ONLY / GET ONLY");
console.log("========================================");
console.log("");
console.log("PASS: DOWN -> HEALTHY detected");
console.log("PASS: real-like job captured");
console.log("PASS: job metadata preserved");
console.log("PASS: GET-only network behavior");
console.log("PASS: POST never performed");
console.log("PASS: wallet never used");
console.log("PASS: signing never performed");
console.log("PASS: broadcast never performed");
console.log("PASS: submission never performed");
console.log("");
console.log("AACP RECOVERY OBSERVER REGRESSION PASSED");
