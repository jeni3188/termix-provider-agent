const cases = [
  {
    name: "HTTP 503",
    response: new Response("<html>down</html>", {
      status: 503,
      headers: { "content-type": "text/html" }
    }),
    expected: "BACKEND_UNAVAILABLE"
  },
  {
    name: "HTTP 500",
    response: new Response("server error", {
      status: 500
    }),
    expected: "BACKEND_UNAVAILABLE"
  },
  {
    name: "HTTP 200 HTML",
    response: new Response("<html>ok</html>", {
      status: 200,
      headers: { "content-type": "text/html" }
    }),
    expected: "MALFORMED_RESPONSE"
  },
  {
    name: "HTTP 200 null",
    response: new Response("null", {
      status: 200,
      headers: { "content-type": "application/json" }
    }),
    expected: "MALFORMED_RESPONSE"
  },
  {
    name: "HTTP 200 string",
    response: new Response('"healthy"', {
      status: 200,
      headers: { "content-type": "application/json" }
    }),
    expected: "MALFORMED_RESPONSE"
  },
  {
    name: "HTTP 200 valid JSON",
    response: new Response('{"data":{}}', {
      status: 200,
      headers: { "content-type": "application/json" }
    }),
    expected: "HEALTHY"
  }
];

function classify(response, json) {
  if (!response.ok) {
    return response.status >= 500
      ? "BACKEND_UNAVAILABLE"
      : "BACKEND_REQUEST_FAILED";
  }

  if (
    json === null ||
    typeof json !== "object"
  ) {
    return "MALFORMED_RESPONSE";
  }

  return "HEALTHY";
}

let passed = 0;

for (const test of cases) {
  const text = await test.response.text();

  let json = null;

  try {
    json = JSON.parse(text);
  } catch {}

  const actual = classify(test.response, json);

  if (actual === test.expected) {
    console.log(`PASS: ${test.name} → ${actual}`);
    passed++;
  } else {
    console.log(
      `FAIL: ${test.name} → expected ${test.expected}, got ${actual}`
    );
  }
}

console.log("");
console.log(`PREFLIGHT REGRESSION: ${passed}/${cases.length} PASS`);

if (passed !== cases.length) {
  process.exit(1);
}

console.log("POST: NOT PERFORMED");
console.log("WALLET: NOT USED");
console.log("SIGNING: NOT PERFORMED");
console.log("SUBMISSION: NOT PERFORMED");
