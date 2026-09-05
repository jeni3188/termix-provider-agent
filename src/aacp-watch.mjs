const intervalMs =
  Number(process.env.AACP_WATCH_INTERVAL_MS || 1800000);

const base =
  process.env.TERMIX_AACP_URL ||
  "https://aacp-backend.termix.live";

const api = `${base}/api/v1`;

async function check() {
  const started = new Date().toISOString();

  try {
    const response = await fetch(`${api}/config`, {
      signal: AbortSignal.timeout(15000)
    });

    const text = await response.text();

    let json = null;
    try {
      json = JSON.parse(text);
    } catch {}

    if (!response.ok) {
      console.log(
        `[${started}] AACP DOWN HTTP ${response.status}`
      );
      return false;
    }

    if (!json) {
      console.log(
        `[${started}] AACP BLOCKED: non-JSON response`
      );
      return false;
    }

    console.log(`[${started}] AACP HEALTHY`);
    return true;
  } catch (err) {
    console.log(
      `[${started}] AACP ERROR: ${err.message}`
    );
    return false;
  }
}

console.log("========================================");
console.log(" AACP BACKEND WATCHER v1.0.0");
console.log("========================================");
console.log(`Backend : ${base}`);
console.log(
  `Interval: ${Math.round(intervalMs / 1000)} seconds`
);
console.log("Mode    : READ-ONLY");
console.log("POST    : DISABLED");
console.log("Wallet  : NOT USED");
console.log("Signing : NOT USED");
console.log("");

while (true) {
  const healthy = await check();

  if (healthy) {
    console.log("");
    console.log("AACP backend is back.");
    console.log("Watcher stopping.");
    console.log("No offer was submitted.");
    process.exit(0);
  }

  console.log(
    `Next check in ${Math.round(intervalMs / 1000)} seconds...`
  );

  await new Promise(resolve =>
    setTimeout(resolve, intervalMs)
  );
}
