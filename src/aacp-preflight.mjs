const base =
  process.env.TERMIX_AACP_URL ||
  "https://aacp-backend.termix.live";

const api = `${base}/api/v1`;

const checks = [
  ["config", "/config"],
  ["jobs", "/jobs?status=OPEN&limit=1"]
];

let failed = false;

console.log("========================================");
console.log(" AACP PROVIDER PREFLIGHT v1.0.0");
console.log("========================================");
console.log(`Backend: ${base}`);
console.log("");

for (const [name, endpoint] of checks) {
  const url = `${api}${endpoint}`;

  try {
    const r = await fetch(url, {
      signal: AbortSignal.timeout(15000)
    });

    const text = await r.text();

    let json = null;
    try {
      json = JSON.parse(text);
    } catch {}

    if (!r.ok) {
      console.log(`❌ ${name.toUpperCase()}: HTTP ${r.status}`);
      failed = true;
      continue;
    }

    console.log(`✅ ${name.toUpperCase()}: HTTP ${r.status}`);

    if (json !== null) {
      console.log("   JSON response: valid");
    }
  } catch (err) {
    console.log(`❌ ${name.toUpperCase()}: ${err.message}`);
    failed = true;
  }
}

console.log("");

if (failed) {
  console.log("PREFLIGHT: BLOCKED");
  console.log("Reason: AACP backend is unavailable or unhealthy.");
  console.log("No offer request was sent.");
  process.exit(2);
}

console.log("PREFLIGHT: PASS");
console.log("AACP backend is reachable.");
console.log("No offer request was sent.");
