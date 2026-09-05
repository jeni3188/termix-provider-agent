import assert from "node:assert/strict";

process.env.AACP_WATCH_TEST = "1";

const {
  check,
  processState
} = await import("../src/aacp-watch.mjs");

function mockResponse(status, body) {
  return {
    status,
    ok: status >= 200 && status < 300,
    async text() {
      return body;
    }
  };
}

const responses = [
  mockResponse(503, "<html>Service Unavailable</html>"),
  mockResponse(503, "<html>Service Unavailable</html>"),
  mockResponse(200, JSON.stringify({ status: "ok" }))
];

let requestCount = 0;

async function mockFetch(url) {
  assert.equal(
    url,
    "https://aacp-backend.termix.live/api/v1/config"
  );

  assert.ok(
    requestCount < responses.length,
    "unexpected extra HTTP request"
  );

  return responses[requestCount++];
}

console.log("========================================");
console.log(" AACP RECOVERY MONITOR REGRESSION");
console.log(" MOCK HTTP / NO REAL NETWORK");
console.log("========================================");

const first = await check(mockFetch);

assert.equal(first.state, "DOWN");
assert.equal(first.httpStatus, 503);
assert.equal(first.reason, "HTTP_503");

console.log("PASS: HTTP 503 → DOWN");

const second = await check(mockFetch);

assert.equal(second.state, "DOWN");
assert.equal(second.httpStatus, 503);

console.log("PASS: repeated HTTP 503 → DOWN");

const third = await check(mockFetch);

assert.equal(third.state, "HEALTHY");
assert.equal(third.httpStatus, 200);
assert.equal(third.reason, "JSON_OK");

console.log("PASS: HTTP 200 JSON → HEALTHY");

const events1 = processState(first);

assert.ok(events1.includes("INITIAL_STATE=DOWN"));

console.log("PASS: initial DOWN state");

const events2 = processState(second);

assert.ok(
  events2.includes("AACP DOWN 503 (HTTP_503)")
);

console.log("PASS: repeated DOWN state");

const events3 = processState(third);

assert.ok(
  events3.includes("STATE_CHANGE DOWN -> HEALTHY")
);

assert.ok(
  events3.includes("AACP_RECOVERED")
);

assert.ok(
  events3.includes("ACTION=READ_ONLY_DISCOVERY_ALLOWED")
);

assert.ok(
  events3.includes("POST=DISABLED")
);

assert.ok(
  events3.includes("WALLET=NOT_USED")
);

assert.ok(
  events3.includes("SIGNING=NOT_USED")
);

assert.ok(
  events3.includes("SUBMISSION=NOT_PERFORMED")
);

console.log("PASS: DOWN → HEALTHY recovery detected");
console.log("PASS: recovery remains read-only");
console.log("PASS: POST remains disabled");
console.log("PASS: wallet remains unused");
console.log("PASS: signing remains unused");
console.log("PASS: submission remains unperformed");

assert.equal(requestCount, 3);

console.log("PASS: exactly 3 mock HTTP requests");

console.log("");
console.log("========================================");
console.log(" RECOVERY TEST SUMMARY");
console.log("========================================");
console.log("Passed: 12/12");
console.log("Failed: 0/12");
console.log("");
console.log("ALL RECOVERY TESTS PASSED");
console.log("");
console.log("Real network : NONE");
console.log("Wallet       : NOT USED");
console.log("Signing      : NOT USED");
console.log("POST         : NOT PERFORMED");
console.log("Submit       : NOT PERFORMED");
