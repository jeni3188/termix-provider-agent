import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

import { qualifyJobs } from "./aacp-job-qualifier.mjs";
import { createDeliverable } from "./deliverable-gate.mjs";

const jobFile = process.argv[2];
const sourceFile = process.argv[3];

if (!jobFile || !sourceFile) {
  console.error(
    "Usage: pnpm run process <job.json> <staged-source>"
  );
  process.exit(1);
}

if (!fs.existsSync(jobFile)) {
  console.error(`Job file not found: ${jobFile}`);
  process.exit(1);
}

if (!fs.existsSync(sourceFile)) {
  console.error(`Source file not found: ${sourceFile}`);
  process.exit(1);
}

const job = JSON.parse(
  fs.readFileSync(jobFile, "utf8")
);

const jobId =
  job.jobId ??
  "unknown-job";

const outputDir =
  path.resolve(
    "provider-output",
    jobId
  );

fs.mkdirSync(
  outputDir,
  { recursive: true }
);

console.log("========================================");
console.log(" TermiX Provider Agent");
console.log(" Job Processor v1.6.0");
console.log(" READ ONLY");
console.log(" FAIL-CLOSED QUALIFICATION GATE");
console.log("========================================");
console.log("");

console.log(`Job    : ${jobId}`);
console.log(`Source : ${sourceFile}`);
console.log("");

/* -------------------------------------------------- */
/* 1. Provider capability evaluation                  */
/* -------------------------------------------------- */

console.log(
  "[1/5] Evaluating provider capability..."
);

const evaluationRaw =
  execFileSync(
    process.execPath,
    [
      "src/provider-evaluate.mjs",
      jobFile
    ],
    {
      encoding: "utf8"
    }
  );

const evaluation =
  JSON.parse(evaluationRaw);

console.log(
  `Match    : ${evaluation.matching.score}/100`
);

console.log(
  `Budget   : ${evaluation.pricing.budgetStatus}`
);

console.log(
  `Decision : ${evaluation.decision.status}`
);

/* -------------------------------------------------- */
/* 2. Provider decision gate                          */
/* -------------------------------------------------- */

console.log("");
console.log(
  "[2/5] Applying provider decision gate..."
);

const decision =
  evaluation.decision.status;

let executionPath;

if (decision === "REJECT") {
  executionPath = "REJECT";
} else if (
  decision === "MANUAL_REVIEW"
) {
  executionPath = "MANUAL_REVIEW";
} else if (
  decision === "PROCEED_TO_OFFER_REVIEW"
) {
  executionPath = "OFFER_REVIEW";
} else {
  executionPath = "MANUAL_REVIEW";
}

console.log(
  `Execution path: ${executionPath}`
);

/* -------------------------------------------------- */
/* 3. Qualification gate                             */
/* -------------------------------------------------- */

console.log("");
console.log(
  "[3/5] Applying qualification + artifact gate..."
);

const qualification =
  qualifyJobs([job])[0];

if (!qualification) {
  throw new Error(
    "Qualification failed: no qualification result."
  );
}

console.log(
  `Qualification : ${qualification.qualification}`
);

console.log(
  `Score         : ${qualification.score}/100`
);

console.log(
  `Artifact      : ${
    qualification.artifactStatus
  }`
);

console.log(
  `Trusted       : ${
    qualification.artifactTrusted
  }`
);

/*
 * SECURITY ANALYSIS IS ALLOWED ONLY FOR:
 *
 *   STRONG_MATCH
 *   + trusted artifact
 *
 * Everything else stops before analyze.mjs.
 */

const qualificationAllowed =
  qualification.qualification ===
    "STRONG_MATCH" &&
  qualification.artifactTrusted === true &&
  qualification.artifactStatus ===
    "TRUSTED_ARTIFACT";

let artifactPath =
  qualification.artifactPath ??
  null;

let artifactBindingValid = false;

if (qualificationAllowed) {
  const requestedPath =
    path.resolve(sourceFile);

  const trustedPath =
    path.resolve(
      artifactPath
    );

  if (requestedPath !== trustedPath) {
    console.log("");
    console.log(
      "Artifact source mismatch."
    );

    console.log(
      `Requested: ${requestedPath}`
    );

    console.log(
      `Trusted  : ${trustedPath}`
    );

    artifactPath = null;
  } else {
    artifactBindingValid = true;
  }
}

const analysisAllowed =
  qualificationAllowed &&
  artifactBindingValid &&
  executionPath !== "REJECT";

if (analysisAllowed) {
  console.log(
    "Qualification gate: ALLOWED"
  );

  console.log(
    "Analyzer gate    : OPEN"
  );
} else {
  console.log(
    "Qualification gate: BLOCKED"
  );

  console.log(
    "Analyzer gate    : CLOSED"
  );
}

/* -------------------------------------------------- */
/* 4. Security analysis                               */
/* -------------------------------------------------- */

let analysis = null;
let deliverable = null;

if (analysisAllowed) {
  console.log("");
  console.log(
    "[4/5] Running security assessment..."
  );

  /*
   * CRITICAL SECURITY PROPERTY:
   *
   * analyze.mjs receives ONLY the exact artifact
   * path previously verified by the qualifier.
   */

  const analysisRaw =
    execFileSync(
      process.execPath,
      [
        "src/analyze.mjs",
        artifactPath
      ],
      {
        encoding: "utf8"
      }
    );

  analysis =
    JSON.parse(analysisRaw);

  console.log(
    `Findings : ${analysis.summary.total}`
  );

  console.log(
    `Risk     : ${analysis.summary.riskLevel}`
  );

  console.log(
    `Score    : ${analysis.summary.riskScore}`
  );

  const base =
    path.basename(
      artifactPath,
      path.extname(artifactPath)
    );

  const sourceDir =
    path.dirname(
      path.resolve(
        artifactPath
      )
    );

  const deliverableJsonPath =
    path.join(
      sourceDir,
      `${base}-TERMiX-DELIVERABLE.json`
    );

  const deliverableMdPath =
    path.join(
      sourceDir,
      `${base}-TERMiX-DELIVERABLE.md`
    );

  const deliverableResult =
    createDeliverable({
      job,
      artifactPath,
      analysis,
      analyzerCalled:
        analysis !== null
    });

  if (!deliverableResult.allowed) {
    throw new Error(
      `Deliverable gate blocked: ${deliverableResult.code}`
    );
  }

  deliverable = {
    json:
      deliverableResult.json,

    markdown:
      deliverableResult.markdown,

    gate:
      deliverableResult.code,

    artifactSha256:
      deliverableResult.artifactSha256,

    artifactSize:
      deliverableResult.artifactSize,

    analysisSha256:
      deliverableResult.analysisSha256
  };
} else {
  console.log("");
  console.log(
    "[4/5] Security assessment BLOCKED."
  );

  console.log(
    "Analyzer: NOT CALLED"
  );
}

/* -------------------------------------------------- */
/* 5. Processor result                                */
/* -------------------------------------------------- */

console.log("");
console.log(
  "[5/5] Building processor result..."
);

const result = {
  processor:
    "TermiX Job Processor",

  version:
    "1.6.0",

  job: {
    jobId,

    status:
      job.status ??
      null,

    strategyType:
      job.strategyType ??
      null,

    title:
      job.title ??
      null,

    budgetUSDC:
      Number(
        job.budget ??
        0
      ) / 1_000_000
  },

  evaluation,

  qualification,

  artifactGate: {
    allowed:
      analysisAllowed,

    qualification:
      qualification.qualification,

    artifactStatus:
      qualification.artifactStatus,

    artifactTrusted:
      qualification.artifactTrusted,

    artifactBindingValid,

    path:
      qualification.artifactPath ??
      null,

    size:
      qualification.artifactSize ??
      null,

    sha256:
      qualification.artifactSha256 ??
      null
  },

  execution: {
    path:
      analysisAllowed
        ? executionPath
        : "BLOCKED_QUALIFICATION_GATE",

    securityAssessment:
      analysis !== null,

    analyzerCalled:
      analysis !== null,

    walletRequired:
      false,

    offerSubmitted:
      false,

    transactionSigned:
      false,

    transactionBroadcast:
      false
  },

  security:
    analysis
      ? {
          findings:
            analysis.summary.total,

          critical:
            analysis.summary.critical,

          high:
            analysis.summary.high,

          medium:
            analysis.summary.medium,

          low:
            analysis.summary.low,

          riskScore:
            analysis.summary.riskScore,

          riskLevel:
            analysis.summary.riskLevel
        }
      : null,

  deliverable,

  safety: {
    mode:
      "READ_ONLY",

    failClosedQualificationGate:
      true,

    trustedArtifactRequired:
      true,

    strongMatchRequired:
      true,

    networkFetch:
      false,

    walletUsed:
      false,

    signingPerformed:
      false,

    broadcastPerformed:
      false,

    submissionPerformed:
      false,

    noAutomaticSubmission:
      true,

    noAutomaticSigning:
      true,

    noAutomaticBroadcast:
      true
  }
};

const outputPath =
  path.join(
    outputDir,
    "processor-result.json"
  );

fs.writeFileSync(
  outputPath,
  JSON.stringify(
    result,
    null,
    2
  ) + "\n"
);

console.log("");
console.log("========================================");
console.log(" JOB PROCESSOR COMPLETE");
console.log("========================================");
console.log("");

console.log(
  `Qualification : ${
    qualification.qualification
  }`
);

console.log(
  `Artifact      : ${
    qualification.artifactTrusted
      ? "TRUSTED"
      : "BLOCKED"
  }`
);

console.log(
  `Analyzer      : ${
    analysis
      ? "CALLED"
      : "NOT CALLED"
  }`
);

console.log(
  `Output        : ${outputPath}`
);

console.log("");
console.log("Wallet: NOT USED");
console.log("Signing: NOT USED");
console.log("Submission: NOT USED");
console.log("Broadcast: NOT USED");
