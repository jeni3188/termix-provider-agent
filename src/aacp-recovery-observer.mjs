import { setTimeout as sleep } from "node:timers/promises";

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

async function fetchJson(fetchImpl, url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchImpl(url, {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      signal: controller.signal
    });

    const contentType =
      response.headers.get("content-type") || "";

    const text = await response.text();

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
      error: error?.name === "AbortError"
        ? "TIMEOUT"
        : String(error?.message || error)
    };
  } finally {
    clearTimeout(timer);
  }
}

function normalizeJobs(payload) {
  if (Array.isArray(payload)) {
    return {
      valid: true,
      jobs: payload,
      error: null
    };
  }

  if (
    payload &&
    Array.isArray(payload.jobs)
  ) {
    return {
      valid: true,
      jobs: payload.jobs,
      error: null
    };
  }

  if (
    payload &&
    payload.data &&
    Array.isArray(payload.data)
  ) {
    return {
      valid: true,
      jobs: payload.data,
      error: null
    };
  }

  if (
    payload &&
    payload.data &&
    Array.isArray(payload.data.jobs)
  ) {
    return {
      valid: true,
      jobs: payload.data.jobs,
      error: null
    };
  }

  return {
    valid: false,
    jobs: [],
    error: "JOBS_SCHEMA_INVALID"
  };
}

function validateJobShape(job) {
  if (!job || typeof job !== "object" || Array.isArray(job)) {
    return {
      valid: false,
      code: "JOB_NOT_OBJECT"
    };
  }

  const id =
    job.jobId ??
    job.id ??
    null;

  if (
    typeof id !== "string" ||
    id.trim() === ""
  ) {
    return {
      valid: false,
      code: "JOB_ID_MISSING"
    };
  }

  const status =
    String(job.status || "").toUpperCase();

  if (
    !["OPEN", "FUNDED"].includes(status)
  ) {
    return {
      valid: false,
      code: "JOB_STATUS_INVALID"
    };
  }

  return {
    valid: true,
    code: null
  };
}

function validateJobs(jobs) {
  const invalid = [];

  for (let index = 0; index < jobs.length; index++) {
    const validation =
      validateJobShape(jobs[index]);

    if (!validation.valid) {
      invalid.push({
        index,
        code: validation.code
      });
    }
  }

  return {
    valid: invalid.length === 0,
    invalid
  };
}

function dedupeJobs(jobs) {
  const seen = new Set();
  const result = [];

  for (const job of jobs) {
    if (!job || typeof job !== "object") continue;

    const jobId =
      job.jobId ??
      job.id ??
      null;

    const key =
      jobId === null
        ? JSON.stringify(job)
        : String(jobId);

    if (seen.has(key)) continue;

    seen.add(key);
    result.push(job);
  }

  return result;
}

export async function observeRecovery(
  fetchImpl = fetch,
  options = {}
) {
  const baseUrl =
    options.baseUrl ||
    DEFAULT_BASE_URL;

  const timeoutMs =
    Number(options.timeoutMs) ||
    DEFAULT_TIMEOUT_MS;

  const previousState =
    options.previousState || "NONE";

  const safety = safetyState();

  const config = await fetchJson(
    fetchImpl,
    `${baseUrl}/api/v1/config`,
    timeoutMs
  );

  if (!config.ok) {
    return {
      recovered: false,
      previousState,
      state: "DOWN",
      config,
      jobs: [],
      safety
    };
  }

  const [open, funded] = await Promise.all([
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

  /*
   * Fail closed on partial endpoint failure.
   *
   * Recovery is considered HEALTHY only when both
   * OPEN and FUNDED endpoints return valid HTTP 2xx
   * responses. A single failed endpoint means the
   * observer cannot establish a complete recovery state.
   */
  if (!open.ok || !funded.ok) {
    return {
      recovered: false,
      previousState,
      state: "DOWN",
      config,
      endpoints: {
        open,
        funded
      },
      jobs: [],
      safety
    };
  }

  const openResult =
    normalizeJobs(open.data);

  const fundedResult =
    normalizeJobs(funded.data);

  /*
   * HTTP 200 is not sufficient to establish recovery.
   * Both job endpoints must also expose a recognized
   * response schema.
   */
  if (
    !openResult.valid ||
    !fundedResult.valid
  ) {
    return {
      recovered: false,
      previousState,
      state: "BLOCKED",
      config,
      endpoints: {
        open: {
          ...open,
          schemaValid: openResult.valid,
          schemaError: openResult.error
        },
        funded: {
          ...funded,
          schemaValid: fundedResult.valid,
          schemaError: fundedResult.error
        }
      },
      jobs: [],
      safety
    };
  }

  const combinedJobs = [
    ...openResult.jobs,
    ...fundedResult.jobs
  ];

  const jobValidation =
    validateJobs(combinedJobs);

  /*
   * HTTP 200 + recognized container schema is still
   * insufficient for recovery. Every individual job
   * must have a valid identity and supported status.
   *
   * Fail closed on the first malformed job set.
   */
  if (!jobValidation.valid) {
    return {
      recovered: false,
      previousState,
      state: "BLOCKED",
      config,
      endpoints: {
        open: {
          ...open,
          schemaValid: true,
          schemaError: null
        },
        funded: {
          ...funded,
          schemaValid: true,
          schemaError: null
        }
      },
      jobs: [],
      invalidJobs: jobValidation.invalid,
      safety
    };
  }

  const jobs = dedupeJobs(combinedJobs);

  const state = "HEALTHY";

  return {
    recovered:
      previousState === "DOWN" &&
      state === "HEALTHY",

    previousState,
    state,
    config,
    endpoints: {
      open,
      funded
    },
    jobs,
    safety
  };
}

export function summarizeJob(job) {
  if (!job || typeof job !== "object") {
    return null;
  }

  return {
    jobId: job.jobId ?? job.id ?? null,
    status: job.status ?? null,
    strategyType: job.strategyType ?? null,
    budget: job.budget ?? null,
    title: job.title ?? null,
    description: job.description ?? null,
    deadline: job.deadline ?? null,
    providerId: job.providerId ?? null,

    // Observational only: preserve possible artifact fields
    // without downloading or resolving anything.
    observedFields: Object.keys(job).sort()
  };
}
