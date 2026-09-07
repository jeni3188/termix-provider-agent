import {
  inspectJobs
} from "./aacp-job-inspector.mjs";

import {
  qualifyJobs
} from "./aacp-job-qualifier.mjs";

const DEFAULT_BASE_URL =
  process.env.AACP_BACKEND_URL ||
  "https://aacp-backend.termix.live";

const DEFAULT_TIMEOUT_MS = 15000;

function safetyState() {
  return {
    postPerformed: false,
    walletUsed: false,
    signingPerformed: false,
    broadcastPerformed: false,
    submissionPerformed: false
  };
}

async function fetchJson(
  fetchImpl,
  url,
  timeoutMs
) {
  const controller =
    new AbortController();

  const timer =
    setTimeout(
      () => controller.abort(),
      timeoutMs
    );

  try {
    const response =
      await fetchImpl(
        url,
        {
          method: "GET",
          headers: {
            Accept: "application/json"
          },
          signal: controller.signal
        }
      );

    const contentType =
      response.headers.get(
        "content-type"
      ) || "";

    const text =
      await response.text();

    let data = null;

    if (text.trim()) {
      try {
        data = JSON.parse(text);
      } catch {
        return {
          ok: false,
          status: response.status,
          contentType,
          data: null,
          error: "NON_JSON_RESPONSE"
        };
      }
    }

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        contentType,
        data,
        error: `HTTP_${response.status}`
      };
    }

    if (
      !data ||
      typeof data !== "object" ||
      Array.isArray(data)
    ) {
      return {
        ok: false,
        status: response.status,
        contentType,
        data,
        error: "JSON_ROOT_NOT_OBJECT"
      };
    }

    return {
      ok: true,
      status: response.status,
      contentType,
      data,
      error: null
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      contentType: "",
      data: null,
      error:
        error?.name === "AbortError"
          ? "TIMEOUT"
          : String(
              error?.message ||
              error
            )
    };
  } finally {
    clearTimeout(timer);
  }
}

function parseJobs(payload) {
  if (
    Array.isArray(payload)
  ) {
    return payload;
  }

  if (
    payload &&
    Array.isArray(payload.jobs)
  ) {
    return payload.jobs;
  }

  if (
    payload &&
    payload.data &&
    Array.isArray(payload.data)
  ) {
    return payload.data;
  }

  if (
    payload &&
    payload.data &&
    Array.isArray(payload.data.jobs)
  ) {
    return payload.data.jobs;
  }

  return null;
}

function dedupeJobs(jobs) {
  const seen =
    new Set();

  const result = [];

  for (const job of jobs) {
    if (
      !job ||
      typeof job !== "object" ||
      Array.isArray(job)
    ) {
      continue;
    }

    const id =
      job.jobId ??
      job.id ??
      null;

    const key =
      id === null
        ? JSON.stringify(job)
        : String(id);

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    result.push(job);
  }

  return result;
}

function failureState(result) {
  if (
    result.status >= 500
  ) {
    return "BACKEND_UNAVAILABLE";
  }

  if (
    result.error ===
    "NON_JSON_RESPONSE" ||
    result.error ===
    "JSON_ROOT_NOT_OBJECT"
  ) {
    return "MALFORMED_RESPONSE";
  }

  return "BACKEND_REQUEST_FAILED";
}

export async function discoverReadOnly(
  fetchImpl = fetch,
  options = {}
) {
  const baseUrl =
    options.baseUrl ||
    DEFAULT_BASE_URL;

  const timeoutMs =
    Number(options.timeoutMs) ||
    DEFAULT_TIMEOUT_MS;

  const safety =
    safetyState();

  const config =
    await fetchJson(
      fetchImpl,
      `${baseUrl}/api/v1/config`,
      timeoutMs
    );

  if (!config.ok) {
    return {
      state: failureState(config),
      config,
      endpoints: {},
      jobs: [],
      inspectedJobs: [],
      qualification: [],
      safety
    };
  }

  const [
    open,
    funded
  ] = await Promise.all([
    fetchJson(
      fetchImpl,
      `${baseUrl}/api/v1/jobs?status=OPEN&limit=20`,
      timeoutMs
    ),

    fetchJson(
      fetchImpl,
      `${baseUrl}/api/v1/jobs?status=FUNDED&limit=20`,
      timeoutMs
    )
  ]);

  if (!open.ok) {
    return {
      state: failureState(open),
      config,
      endpoints: {
        open,
        funded
      },
      jobs: [],
      inspectedJobs: [],
      qualification: [],
      safety
    };
  }

  if (!funded.ok) {
    return {
      state: failureState(funded),
      config,
      endpoints: {
        open,
        funded
      },
      jobs: [],
      inspectedJobs: [],
      qualification: [],
      safety
    };
  }

  const openJobs =
    parseJobs(open.data);

  const fundedJobs =
    parseJobs(funded.data);

  if (
    openJobs === null ||
    fundedJobs === null
  ) {
    return {
      state: "MALFORMED_RESPONSE",
      config,
      endpoints: {
        open,
        funded
      },
      jobs: [],
      inspectedJobs: [],
      qualification: [],
      safety
    };
  }

  const jobs =
    dedupeJobs([
      ...openJobs,
      ...fundedJobs
    ]);

  const inspectedJobs =
    inspectJobs(jobs);

  const qualification =
    qualifyJobs(jobs);

  return {
    state: "HEALTHY",

    config,

    endpoints: {
      open,
      funded
    },

    jobs,

    inspectedJobs,

    qualification,

    safety
  };
}

if (
  process.argv[1] &&
  process.argv[1].endsWith(
    "aacp-readonly-discovery.mjs"
  )
) {
  const result =
    await discoverReadOnly();

  console.log("");
  console.log("========================================");
  console.log(" AACP READ-ONLY DISCOVERY");
  console.log("========================================");
  console.log(
    `State : ${result.state}`
  );
  console.log(
    `Jobs  : ${result.jobs.length}`
  );
  console.log(
    `POST  : ${
      result.safety.postPerformed
        ? "PERFORMED"
        : "NOT PERFORMED"
    }`
  );
  console.log(
    `Wallet: ${
      result.safety.walletUsed
        ? "USED"
        : "NOT USED"
    }`
  );
  console.log(
    `Sign  : ${
      result.safety.signingPerformed
        ? "PERFORMED"
        : "NOT PERFORMED"
    }`
  );
  console.log(
    `Submit: ${
      result.safety.submissionPerformed
        ? "PERFORMED"
        : "NOT PERFORMED"
    }`
  );
}
