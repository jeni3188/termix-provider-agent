import assert from "node:assert/strict";
import {
  discoverReadOnly
} from "../src/aacp-readonly-discovery.mjs";

function response(status, body, contentType = "application/json") {
  return new Response(
    typeof body === "string"
      ? body
      : JSON.stringify(body),
    {
      status,
      headers: {
        "content-type": contentType
      }
    }
  );
}

function mockFetch(routes) {
  const calls = [];

  return {
    calls,

    fetch: async (url, options = {}) => {
      calls.push({
        url,
        method: options.method || "GET"
      });

      const route = routes[url];

      if (!route) {
        throw new Error(`Unexpected URL: ${url}`);
      }

      return route;
    }
  };
}

const base = "https://mock-aacp.test";

const configUrl =
  `${base}/api/v1/config`;

const openUrl =
  `${base}/api/v1/jobs?status=OPEN&limit=20`;

const fundedUrl =
  `${base}/api/v1/jobs?status=FUNDED&limit=20`;

/* --------------------------------------------------------- */
/* TEST 1 — healthy read-only discovery                      */
/* --------------------------------------------------------- */

{
  const { fetch, calls } = mockFetch({
    [configUrl]:
      response(200, { network: "bsc-testnet" }),

    [openUrl]:
      response(200, {
        jobs: [
          {
            jobId: "security-001",
            status: "OPEN",
            strategyType: "PROGRAM",
            budget: "500000000",
            title: "Smart Contract Security Audit",
            description:
              "Audit Solidity contract for reentrancy and access control.",
            providerId: null
          }
        ]
      }),

    [fundedUrl]:
      response(200, {
        jobs: []
      })
  });

  const result =
    await discoverReadOnly(fetch, {
      baseUrl: base
    });

  assert.equal(
    result.state,
    "HEALTHY"
  );

  assert.equal(
    result.jobs.length,
    1
  );

  assert.equal(
    result.jobs[0].jobId,
    "security-001"
  );

  assert.equal(
    result.qualification[0].qualification,
    "ARTIFACT_MISSING"
  );

  assert.equal(
    result.safety.postPerformed,
    false
  );

  assert.equal(
    result.safety.walletUsed,
    false
  );

  assert.equal(
    result.safety.signingPerformed,
    false
  );

  assert.equal(
    result.safety.broadcastPerformed,
    false
  );

  assert.equal(
    result.safety.submissionPerformed,
    false
  );

  assert.ok(
    calls.every(
      x => x.method === "GET"
    )
  );

  console.log(
    "PASS: healthy discovery is GET-only"
  );
}

/* --------------------------------------------------------- */
/* TEST 2 — config 503 must block                            */
/* --------------------------------------------------------- */

{
  const { fetch, calls } = mockFetch({
    [configUrl]:
      response(503, "<html>503</html>", "text/html")
  });

  const result =
    await discoverReadOnly(fetch, {
      baseUrl: base
    });

  assert.equal(
    result.state,
    "BACKEND_UNAVAILABLE"
  );

  assert.equal(
    result.jobs.length,
    0
  );

  assert.equal(
    result.safety.postPerformed,
    false
  );

  assert.equal(
    calls.length,
    1
  );

  console.log(
    "PASS: config 503 fails closed"
  );
}

/* --------------------------------------------------------- */
/* TEST 3 — malformed jobs response must block               */
/* --------------------------------------------------------- */

{
  const { fetch } = mockFetch({
    [configUrl]:
      response(200, { network: "bsc-testnet" }),

    [openUrl]:
      response(200, {
        unexpected: "schema"
      }),

    [fundedUrl]:
      response(200, {
        jobs: []
      })
  });

  const result =
    await discoverReadOnly(fetch, {
      baseUrl: base
    });

  assert.equal(
    result.state,
    "MALFORMED_RESPONSE"
  );

  assert.equal(
    result.jobs.length,
    0
  );

  console.log(
    "PASS: malformed jobs schema fails closed"
  );
}

/* --------------------------------------------------------- */
/* TEST 4 — funded failure must not become healthy            */
/* --------------------------------------------------------- */

{
  const { fetch } = mockFetch({
    [configUrl]:
      response(200, { network: "bsc-testnet" }),

    [openUrl]:
      response(200, {
        jobs: []
      }),

    [fundedUrl]:
      response(
        503,
        "<html>503</html>",
        "text/html"
      )
  });

  const result =
    await discoverReadOnly(fetch, {
      baseUrl: base
    });

  assert.equal(
    result.state,
    "BACKEND_UNAVAILABLE"
  );

  assert.equal(
    result.jobs.length,
    0
  );

  console.log(
    "PASS: partial endpoint failure fails closed"
  );
}

/* --------------------------------------------------------- */
/* TEST 5 — POST is impossible                              */
/* --------------------------------------------------------- */

{
  const { fetch, calls } = mockFetch({
    [configUrl]:
      response(200, { network: "bsc-testnet" }),

    [openUrl]:
      response(200, { jobs: [] }),

    [fundedUrl]:
      response(200, { jobs: [] })
  });

  const result =
    await discoverReadOnly(fetch, {
      baseUrl: base
    });

  assert.equal(
    result.state,
    "HEALTHY"
  );

  assert.ok(
    calls.every(
      x => x.method === "GET"
    )
  );

  assert.equal(
    result.safety.postPerformed,
    false
  );

  console.log(
    "PASS: discovery cannot perform POST"
  );
}

console.log("");
console.log("========================================");
console.log(" AACP READ-ONLY DISCOVERY REGRESSION");
console.log("========================================");
console.log("Passed: 5/5");
console.log("Failed: 0/5");
console.log("");
console.log("ALL READ-ONLY DISCOVERY TESTS PASSED");
