const BASE_URL =
  process.env.TERMIX_AACP_URL ||
  "https://aacp-backend.termix.live";

const ENDPOINTS = [
  "/api/v1/jobs?status=FUNDED&limit=20",
  "/api/v1/jobs?status=OPEN&limit=20"
];

const TIMEOUT_MS = 15000;

async function fetchEndpoint(endpoint) {
  const url = `${BASE_URL}${endpoint}`;

  console.log(`GET ${url}`);

  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(),
    TIMEOUT_MS
  );

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        Accept: "application/json"
      }
    });

    const contentType =
      response.headers.get("content-type") || "";

    const body =
      await response.text();

    return {
      endpoint,
      url,
      status: response.status,
      ok: response.ok,
      contentType,
      body
    };
  } catch (error) {
    return {
      endpoint,
      url,
      status: 0,
      ok: false,
      contentType: "",
      body: "",
      error:
        error.name === "AbortError"
          ? "TIMEOUT"
          : error.message
    };
  } finally {
    clearTimeout(timer);
  }
}

function parseResponse(result) {
  if (result.error) {
    return {
      status: "ERROR",
      error: result.error,
      jobs: []
    };
  }

  if (result.status === 503) {
    return {
      status: "BACKEND_UNAVAILABLE",
      error: "HTTP 503",
      jobs: []
    };
  }

  if (!result.contentType.includes("application/json")) {
    return {
      status: "NON_JSON_RESPONSE",
      error:
        `HTTP ${result.status} ${result.contentType || "unknown content-type"}`,
      jobs: []
    };
  }

  if (!result.ok) {
    return {
      status: "HTTP_ERROR",
      error: `HTTP ${result.status}`,
      jobs: []
    };
  }

  try {
    const data = JSON.parse(result.body);

    const jobs =
      Array.isArray(data)
        ? data
        : Array.isArray(data.jobs)
          ? data.jobs
          : Array.isArray(data.data)
            ? data.data
            : [];

    return {
      status: "OK",
      error: null,
      jobs
    };
  } catch {
    return {
      status: "INVALID_JSON",
      error: "Response was not valid JSON.",
      jobs: []
    };
  }
}

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" AACP Job Intake v1.3.0");
console.log(" READ ONLY");
console.log("========================================");
console.log("");

console.log(`Backend: ${BASE_URL}`);
console.log("");

const results = [];

for (const endpoint of ENDPOINTS) {
  const raw = await fetchEndpoint(endpoint);
  const parsed = parseResponse(raw);

  results.push({
    ...raw,
    parsed
  });

  console.log(
    `STATUS ${parsed.status}` +
    (parsed.error ? ` — ${parsed.error}` : "")
  );

  console.log(
    `Jobs: ${parsed.jobs.length}`
  );

  console.log("");
}

const allJobs = [];

for (const result of results) {
  for (const job of result.parsed.jobs) {
    const id =
      job.jobId ??
      job.id ??
      JSON.stringify(job);

    if (
      !allJobs.some(
        existing =>
          (existing.jobId ??
            existing.id ??
            JSON.stringify(existing)) === id
      )
    ) {
      allJobs.push(job);
    }
  }
}

const backendErrors =
  results.filter(
    result => result.parsed.status !== "OK"
  ).length;

console.log("========================================");
console.log(" AACP INTAKE SUMMARY");
console.log("========================================");
console.log("");

console.log(
  `Unique jobs retrieved : ${allJobs.length}`
);

console.log(
  `Endpoint errors       : ${backendErrors}/${results.length}`
);

if (backendErrors === results.length) {
  console.log("");
  console.log(
    "AACP backend is unavailable."
  );
  console.log(
    "No jobs are assumed to exist."
  );
} else {
  console.log("");

  for (const job of allJobs) {
    console.log(
      `JOB ${job.jobId ?? job.id ?? "-"}`
    );

    console.log(
      `  Status   : ${job.status ?? "-"}`
    );

    console.log(
      `  Strategy : ${job.strategyType ?? "-"}`
    );

    console.log(
      `  Title    : ${job.title ?? "-"}`
    );

    console.log(
      `  Provider : ${job.providerId ?? "OPEN"}`
    );

    console.log("");
  }
}

const output = {
  intake: "TermiX AACP Job Intake",
  version: "1.3.0",
  backend: BASE_URL,
  mode: "READ_ONLY",
  endpoints: results.map(result => ({
    endpoint: result.endpoint,
    status: result.status,
    contentType: result.contentType,
    parsedStatus: result.parsed.status,
    error: result.parsed.error
  })),
  jobs: allJobs,
  summary: {
    uniqueJobs: allJobs.length,
    endpointErrors: backendErrors,
    backendAvailable:
      backendErrors < results.length
  },
  safety: {
    walletRequired: false,
    offerSubmitted: false,
    transactionSigned: false,
    transactionBroadcast: false
  }
};

const fs =
  await import("node:fs/promises");

await fs.mkdir(
  "provider-output",
  { recursive: true }
);

await fs.writeFile(
  "provider-output/aacp-intake.json",
  JSON.stringify(output, null, 2)
);

console.log(
  "Output: provider-output/aacp-intake.json"
);

console.log("");
console.log("AACP INTAKE COMPLETE");
console.log("Execution: READ_ONLY");
