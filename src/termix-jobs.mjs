const BASE_URL =
  process.env.AACP_BASE_URL ||
  "https://aacp-backend.termix.live";

const LIMIT_FUNDED = 20;
const LIMIT_OPEN = 10;

async function request(path) {
  const url = `${BASE_URL}${path}`;

  console.log(`GET ${url}`);

  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      "User-Agent": "TermiX-Provider-Agent/0.6.0"
    }
  });

  const text = await response.text();

  if (!response.ok) {
    const error = new Error(
      `HTTP ${response.status}: ${text.slice(0, 300)}`
    );

    error.status = response.status;
    error.url = url;

    throw error;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function unwrap(response) {
  if (response && typeof response === "object" && "data" in response) {
    return response.data;
  }

  return response;
}

function jobsFrom(response) {
  const data = unwrap(response);

  if (Array.isArray(data)) return data;

  if (data && Array.isArray(data.jobs)) {
    return data.jobs;
  }

  return [];
}

function formatBudget(value) {
  const n = Number(value);

  if (!Number.isFinite(n)) {
    return "-";
  }

  // Backend may expose raw USDC units.
  return (n / 1e6).toLocaleString("en-US", {
    maximumFractionDigits: 6
  });
}

function formatDeadline(value) {
  if (value === undefined || value === null) {
    return "-";
  }

  const n = Number(value);

  if (!Number.isFinite(n) || n <= 0) {
    return "-";
  }

  return new Date(n * 1000).toISOString();
}

function providerLabel(job) {
  return job.providerId ?? "OPEN";
}

function offerCount(job) {
  if (Array.isArray(job.offers)) {
    return job.offers.length;
  }

  if (typeof job.offerCount === "number") {
    return job.offerCount;
  }

  return "-";
}

function printJobs(title, jobs) {
  console.log(`\n${title}`);
  console.log("=".repeat(100));

  if (!jobs.length) {
    console.log("No jobs returned.");
    return;
  }

  for (const job of jobs) {
    console.log(`Job ID    : ${job.jobId ?? "-"}`);
    console.log(`Status    : ${job.status ?? "-"}`);
    console.log(`Strategy  : ${job.strategyType ?? "-"}`);
    console.log(`Budget    : ${formatBudget(job.budget)} USDC`);
    console.log(`Deadline  : ${formatDeadline(job.onchainDeadline)}`);
    console.log(`Provider  : ${providerLabel(job)}`);
    console.log(`Offers    : ${offerCount(job)}`);
    console.log("-".repeat(100));
  }
}

console.log("========================================");
console.log(" TermiX Provider Agent - Job Browser");
console.log(" Version 0.6.0");
console.log(" READ ONLY");
console.log("========================================\n");

console.log(`AACP Base URL: ${BASE_URL}`);
console.log("No wallet / signing / staking / transaction.\n");

const results = {
  funded: null,
  open: null,
  errors: []
};

for (const [name, path] of [
  ["funded", `/api/v1/jobs?status=FUNDED&limit=${LIMIT_FUNDED}`],
  ["open", `/api/v1/jobs?status=OPEN&limit=${LIMIT_OPEN}`]
]) {
  try {
    results[name] = await request(path);
  } catch (error) {
    results.errors.push({
      type: name,
      status: error.status ?? null,
      url: error.url ?? null,
      message: error.message
    });
  }
}

if (results.funded) {
  printJobs(
    "FUNDED JOBS",
    jobsFrom(results.funded)
  );
}

if (results.open) {
  printJobs(
    "OPEN JOBS",
    jobsFrom(results.open)
  );
}

if (results.errors.length) {
  console.log("\nBACKEND STATUS");
  console.log("=".repeat(100));

  for (const error of results.errors) {
    console.log(
      `${error.type.toUpperCase()}: ${error.message}`
    );
  }
}

const fundedJobs = results.funded
  ? jobsFrom(results.funded)
  : [];

const openJobs = results.open
  ? jobsFrom(results.open)
  : [];

console.log("\nSUMMARY");
console.log("=".repeat(100));
console.log(`Funded jobs retrieved : ${fundedJobs.length}`);
console.log(`Open jobs retrieved   : ${openJobs.length}`);
console.log(`Backend errors        : ${results.errors.length}`);

if (
  results.errors.some(error => error.status === 503)
) {
  console.log("");
  console.log(
    "AACP backend is currently unavailable (HTTP 503)."
  );
  console.log(
    "This is not interpreted as zero available jobs."
  );
}

console.log("\nREAD-ONLY JOB BROWSER COMPLETE");
