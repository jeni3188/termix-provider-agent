const BASE_URL =
  process.env.AACP_BASE_URL ||
  "https://aacp-backend.termix.live";

const endpoints = [
  "/",
  "/api/v1/config",
  "/api/v1/stats/jobs?period=7d",
  "/api/v1/jobs?status=OPEN&limit=1"
];

console.log("========================================");
console.log(" TermiX AACP Health Check");
console.log(" READ ONLY");
console.log("========================================\n");

for (const path of endpoints) {
  const url = `${BASE_URL}${path}`;

  try {
    const response = await fetch(url, {
      headers: {
        Accept: "application/json",
        "User-Agent": "TermiX-Provider-Agent/0.6.0"
      }
    });

    const text = await response.text();
    const contentType =
      response.headers.get("content-type") || "unknown";

    let kind = "UNKNOWN";

    if (contentType.includes("application/json")) {
      kind = "JSON";
    } else if (text.trimStart().startsWith("<")) {
      kind = "HTML";
    }

    console.log(`${response.status} ${kind} ${path}`);
    console.log(`Content-Type: ${contentType}`);

    if (!response.ok) {
      console.log(`Body: ${text.slice(0, 120).replace(/\n/g, " ")}`);
    }

    console.log("");
  } catch (error) {
    console.log(`ERROR ${path}`);
    console.log(error.message);
    console.log("");
  }
}
