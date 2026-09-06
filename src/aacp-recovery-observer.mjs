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
  if (Array.isArray(payload)) return payload;

  if (payload && Array.isArray(payload.jobs)) {
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

  return [];
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

  const jobs = dedupeJobs([
    ...normalizeJobs(open.data),
    ...normalizeJobs(funded.data)
  ]);

  const healthy =
    open.ok || funded.ok;

  const state =
    healthy ? "HEALTHY" : "BLOCKED";

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
