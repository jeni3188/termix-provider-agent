import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

import { verifyManifest } from "./artifact-manifest.mjs";

function sha256Buffer(buffer) {
  return crypto
    .createHash("sha256")
    .update(buffer)
    .digest("hex");
}

function sha256File(filePath) {
  return sha256Buffer(
    fs.readFileSync(filePath)
  );
}

function validAnalysis(analysis) {
  return (
    analysis &&
    typeof analysis === "object" &&
    Array.isArray(analysis.findings) &&
    analysis.summary &&
    typeof analysis.summary === "object" &&
    Number.isInteger(analysis.summary.total) &&
    typeof analysis.summary.riskLevel === "string" &&
    Number.isFinite(analysis.summary.riskScore)
  );
}

export function createDeliverable({
  job,
  artifactPath,
  analysis,
  analyzerCalled = false
}) {
  const jobId =
    job?.jobId ?? null;

  if (!jobId) {
    return {
      allowed: false,
      code: "JOB_ID_REQUIRED",
      message: "A valid job ID is required."
    };
  }

  if (!artifactPath) {
    return {
      allowed: false,
      code: "ARTIFACT_REQUIRED",
      message: "A verified artifact path is required."
    };
  }

  if (!analyzerCalled) {
    return {
      allowed: false,
      code: "ANALYZER_NOT_CALLED",
      message:
        "Deliverable generation requires a completed analyzer execution."
    };
  }

  if (!validAnalysis(analysis)) {
    return {
      allowed: false,
      code: "ANALYSIS_INVALID",
      message:
        "Analyzer result is missing or structurally invalid."
    };
  }

  /*
   * Re-verify the manifest + job binding immediately
   * before creating the deliverable.
   *
   * This prevents a previously trusted artifact from
   * silently becoming stale or tampered.
   */
  const manifestCheck =
    verifyManifest(jobId, job);

  if (!manifestCheck.allowed) {
    return {
      allowed: false,
      code: "ARTIFACT_VERIFICATION_FAILED",
      message:
        "Artifact manifest verification failed.",
      reason:
        manifestCheck.code
    };
  }

  /*
   * verifyManifest() returns artifact as the
   * verified absolute path string.
   *
   * Integrity metadata lives inside manifest.artifact.
   */
  const verifiedPath =
    path.resolve(
      manifestCheck.artifact
    );

  const manifestData =
    manifestCheck.manifest ?? {};

  const manifestArtifact =
    manifestData.artifact ?? {};

  const manifestSha256 =
    manifestArtifact.sha256 ??
    manifestData.sha256 ??
    null;

  const manifestSize =
    manifestArtifact.size ??
    manifestData.size ??
    null;

  const requestedPath =
    path.resolve(artifactPath);

  if (verifiedPath !== requestedPath) {
    return {
      allowed: false,
      code: "ARTIFACT_BINDING_MISMATCH",
      message:
        "Artifact path does not match the verified manifest artifact."
    };
  }

  if (!fs.existsSync(verifiedPath)) {
    return {
      allowed: false,
      code: "ARTIFACT_MISSING",
      message:
        "Verified artifact no longer exists."
    };
  }

  const stat =
    fs.statSync(verifiedPath);

  if (!stat.isFile()) {
    return {
      allowed: false,
      code: "ARTIFACT_NOT_FILE",
      message:
        "Verified artifact is not a regular file."
    };
  }

  const artifactBytes =
    fs.readFileSync(verifiedPath);

  const artifactSha256 =
    sha256Buffer(artifactBytes);

  /*
   * Compare against the SHA-256 recorded in the
   * verified manifest.
   */

  if (
    artifactSha256 !==
    manifestSha256
  ) {
    return {
      allowed: false,
      code: "ARTIFACT_HASH_MISMATCH",
      message:
        "Artifact SHA-256 no longer matches the verified manifest.",
      expected:
        manifestSha256,
      actual:
        artifactSha256
    };
  }

  if (
    manifestSize === null ||
    stat.size !==
    Number(manifestSize)
  ) {
    return {
      allowed: false,
      code: "ARTIFACT_SIZE_MISMATCH",
      message:
        "Artifact size no longer matches the verified manifest.",
      expected:
        Number(manifestSize),
      actual:
        stat.size
    };
  }

  /*
   * Create an immutable fingerprint of the analysis
   * used for this deliverable.
   */
  const analysisCanonical =
    JSON.stringify({
      findings:
        analysis.findings,
      summary:
        analysis.summary
    });

  const analysisSha256 =
    sha256Buffer(
      Buffer.from(
        analysisCanonical,
        "utf8"
      )
    );

  const generatedAt =
    new Date().toISOString();

  const base =
    path.basename(
      verifiedPath,
      path.extname(verifiedPath)
    );

  const outDir =
    path.dirname(verifiedPath);

  const jsonPath =
    path.join(
      outDir,
      `${base}-TERMiX-DELIVERABLE.json`
    );

  const mdPath =
    path.join(
      outDir,
      `${base}-TERMiX-DELIVERABLE.md`
    );

  const deliverable = {
    deliverable:
      "TermiX Provider Security Assessment",

    version:
      "2.0.0",

    generatedAt,

    gate: {
      version:
        "1.0.0",

      status:
        "DELIVERABLE_ALLOWED",

      analyzerCalled:
        true,

      artifactTrusted:
        true,

      artifactBindingValid:
        true,

      jobBindingVerified:
        true
    },

    integrity: {
      artifactSha256,
      artifactSize:
        stat.size,

      analysisSha256,

      analysisCanonical:
        "findings+summary"
    },

    job: {
      jobId,
      strategyType:
        job.strategyType ?? null,
      title:
        job.title ?? null
    },

    target: {
      sourceFile:
        verifiedPath,

      bytes:
        stat.size,

      lines:
        fs
          .readFileSync(
            verifiedPath,
            "utf8"
          )
          .split("\n")
          .length
    },

    assessment: {
      findings:
        analysis.findings,

      summary:
        analysis.summary
    },

    methodology: [
      "Static Solidity source inspection",
      "Pattern-based vulnerability detection",
      "Severity classification",
      "Confidence classification",
      "Risk score calculation"
    ],

    limitations: [
      "Automated heuristic analysis is not a formal security audit.",
      "Findings require manual validation.",
      "No exploit execution was performed.",
      "No transaction was signed or broadcast.",
      "On-chain verification requires a separate RPC inspection."
    ],

    execution: {
      mode:
        "READ_ONLY",

      walletRequired:
        false,

      transactionSigned:
        false,

      transactionBroadcast:
        false
    }
  };

  fs.writeFileSync(
    jsonPath,
    JSON.stringify(
      deliverable,
      null,
      2
    ) + "\n"
  );

  const md = `# TermiX Provider Security Deliverable

## Deliverable Gate

- Status: **DELIVERABLE_ALLOWED**
- Gate Version: \`1.0.0\`
- Analyzer Called: **Yes**
- Artifact Trusted: **Yes**
- Artifact Binding Valid: **Yes**
- Job Binding Verified: **Yes**

## Integrity

- Artifact SHA-256: \`${artifactSha256}\`
- Artifact Size: ${stat.size} bytes
- Analysis SHA-256: \`${analysisSha256}\`

## Job

- Job ID: \`${jobId}\`
- Strategy: \`${job.strategyType ?? "-"}\`
- Title: ${job.title ?? "-"}

## Target

- Source: \`${verifiedPath}\`
- Lines: ${deliverable.target.lines}
- Bytes: ${deliverable.target.bytes}

## Assessment

| Metric | Result |
|---|---:|
| Findings | ${analysis.summary.total} |
| Critical | ${analysis.summary.critical} |
| High | ${analysis.summary.high} |
| Medium | ${analysis.summary.medium} |
| Low | ${analysis.summary.low} |
| Risk Score | ${analysis.summary.riskScore} |
| Risk Level | **${analysis.summary.riskLevel}** |

## Findings

${analysis.findings.map((f, i) => `
### ${i + 1}. ${f.title}

- Severity: **${f.severity}**
- Confidence: **${f.confidence}**
- Line: ${f.line ?? "-"}
- Description: ${f.description}
`).join("\n")}

## Methodology

${deliverable.methodology.map(x => `- ${x}`).join("\n")}

## Limitations

${deliverable.limitations.map(x => `- ${x}`).join("\n")}

## Execution Safety

- Mode: **READ_ONLY**
- Wallet required: **No**
- Transaction signed: **No**
- Transaction broadcast: **No**
`;

  fs.writeFileSync(
    mdPath,
    md
  );

  return {
    allowed: true,
    code:
      "DELIVERABLE_ALLOWED",

    json:
      jsonPath,

    markdown:
      mdPath,

    artifactSha256,
    artifactSize:
      stat.size,

    analysisSha256
  };
}

if (
  process.argv[1] ===
  new URL(import.meta.url).pathname
) {
  console.error(
    "This module is invoked by the provider processor."
  );

  process.exit(2);
}
