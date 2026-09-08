#!/usr/bin/env python3

import hashlib
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone


VERSION = "1.0.0"
TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_ATTESTATION_CONSISTENCY_VERIFY"
SOURCE_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION"

ROOT = Path(
    os.environ.get(
        "AACP_OUTPUT_DIR",
        "provider-output/aacp-observer",
    )
)

SOURCE_FILE = (
    ROOT
    / "latest-aacp-evidence-chain-health-integrity-attestation.json"
)

OUTPUT_FILE = (
    ROOT
    / "latest-aacp-evidence-chain-health-attestation-consistency-verify.json"
)

ALLOWED_STATES = {
    "INCOMPLETE",
    "BLOCKED",
    "VERIFIED_READ_ONLY",
}

SAFETY_FALSE = {
    "postPerformed": False,
    "walletUsed": False,
    "signingPerformed": False,
    "broadcastPerformed": False,
    "submissionPerformed": False,
}

POLICY = {
    "readOnly": True,
    "failClosed": True,
    "post": "NOT_PERFORMED",
    "wallet": "NOT_USED",
    "signing": "NOT_PERFORMED",
    "broadcast": "NOT_PERFORMED",
    "submission": "NOT_PERFORMED",
}

FORBIDDEN_COPY_KEYS = {
    "content",
    "report",
    "fullReport",
    "full_report",
    "raw",
    "rawReport",
    "raw_report",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def add_error(errors, code, message):
    errors.append({
        "code": code,
        "message": message,
    })


def safe_exists(path):
    try:
        return path.is_file()
    except Exception:
        return False


def sha256_file(path):
    h = hashlib.sha256()

    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)

        return h.hexdigest()

    except Exception:
        return None


def load_json(path, errors):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    except FileNotFoundError:
        add_error(
            errors,
            "SOURCE_MISSING",
            "Phase 34 attestation source is missing",
        )

    except json.JSONDecodeError:
        add_error(
            errors,
            "SOURCE_INVALID_JSON",
            "Phase 34 attestation source is invalid JSON",
        )

    except Exception:
        add_error(
            errors,
            "SOURCE_READ_ERROR",
            "Phase 34 attestation source could not be read",
        )

    return None


def valid_safety(value):
    return (
        isinstance(value, dict)
        and value == SAFETY_FALSE
    )


def valid_policy(value):
    return (
        isinstance(value, dict)
        and value == POLICY
    )


def validate_common(report, errors):
    if not isinstance(report, dict):
        add_error(
            errors,
            "SOURCE_NOT_OBJECT",
            "Phase 34 attestation must be a JSON object",
        )
        return

    if report.get("type") != SOURCE_TYPE:
        add_error(
            errors,
            "SOURCE_TYPE_INVALID",
            "Phase 34 attestation type is invalid",
        )

    if report.get("mode") != "READ_ONLY":
        add_error(
            errors,
            "MODE_INVALID",
            "Phase 34 attestation mode must be READ_ONLY",
        )

    if report.get("executionAuthorized") is not False:
        add_error(
            errors,
            "EXECUTION_AUTHORIZED",
            "executionAuthorized must be false",
        )

    if report.get("state") not in ALLOWED_STATES:
        add_error(
            errors,
            "STATE_INVALID",
            "Phase 34 state is invalid",
        )

    if report.get("sourceState") not in ALLOWED_STATES:
        add_error(
            errors,
            "SOURCE_STATE_INVALID",
            "Phase 34 sourceState is invalid",
        )

    if not valid_safety(report.get("safety")):
        add_error(
            errors,
            "SAFETY_INVALID",
            "Phase 34 safety metadata is invalid",
        )

    if not valid_policy(report.get("policy")):
        add_error(
            errors,
            "POLICY_INVALID",
            "Phase 34 policy metadata is invalid",
        )


def validate_verification(report, source_sha, errors):
    verification = report.get("verification")

    if not isinstance(verification, dict):
        add_error(
            errors,
            "VERIFICATION_INVALID",
            "Phase 34 verification object is missing or invalid",
        )
        return

    if verification.get("valid") is not True:
        add_error(
            errors,
            "ATTESTATION_NOT_VALID",
            "Phase 34 attestation is not valid",
        )

    if verification.get("phase31Exists") is not True:
        add_error(
            errors,
            "PHASE31_NOT_PRESENT",
            "Phase 34 does not confirm Phase 31 presence",
        )

    if verification.get("phase32Exists") is not True:
        add_error(
            errors,
            "PHASE32_NOT_PRESENT",
            "Phase 34 does not confirm Phase 32 presence",
        )

    if verification.get("phase33Exists") is not True:
        add_error(
            errors,
            "PHASE33_NOT_PRESENT",
            "Phase 34 does not confirm Phase 33 presence",
        )

    if not isinstance(
        verification.get("canonicalPayloadSha256"),
        str,
    ):
        add_error(
            errors,
            "CANONICAL_DIGEST_INVALID",
            "canonicalPayloadSha256 is missing or invalid",
        )

    if not isinstance(
        verification.get("attestationDigest"),
        str,
    ):
        add_error(
            errors,
            "ATTESTATION_DIGEST_INVALID",
            "attestationDigest is missing or invalid",
        )

    if (
        source_sha
        and isinstance(verification.get("sourceSha256"), str)
        and verification.get("sourceSha256") != source_sha
    ):
        add_error(
            errors,
            "SOURCE_SHA_MISMATCH",
            "Phase 34 source SHA metadata does not match its file SHA",
        )


def validate_no_full_report_copy(report, errors):
    if not isinstance(report, dict):
        return

    for key in FORBIDDEN_COPY_KEYS:
        if key in report:
            add_error(
                errors,
                "FULL_REPORT_COPY",
                f"Forbidden full-report field present: {key}",
            )


def reconstruct_digest(report, errors):
    verification = report.get("verification", {})

    payload = {
        "phase31Sha256": verification.get("phase31Sha256"),
        "phase32Sha256": verification.get("phase32Sha256"),
        "phase33Sha256": verification.get("phase33Sha256"),
    }

    if not all(
        isinstance(value, str)
        and len(value) == 64
        for value in payload.values()
    ):
        add_error(
            errors,
            "SOURCE_HASHES_INVALID",
            "Phase 34 source hashes are incomplete or invalid",
        )
        return None, payload

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    digest = hashlib.sha256(canonical).hexdigest()

    return digest, payload


def validate_digest(report, errors):
    digest, payload = reconstruct_digest(
        report,
        errors,
    )

    if digest is None:
        return

    verification = report.get("verification", {})

    canonical_expected = verification.get(
        "canonicalPayloadSha256"
    )

    attestation_expected = verification.get(
        "attestationDigest"
    )

    if digest != canonical_expected:
        add_error(
            errors,
            "CANONICAL_DIGEST_MISMATCH",
            "Reconstructed canonical digest does not match Phase 34",
        )

    if digest != attestation_expected:
        add_error(
            errors,
            "ATTESTATION_DIGEST_MISMATCH",
            "Reconstructed attestation digest does not match Phase 34",
        )


def build_report(
    source_exists,
    source_sha,
    errors,
):
    valid = (
        source_exists
        and len(errors) == 0
    )

    state = (
        "VERIFIED_READ_ONLY"
        if valid
        else "BLOCKED"
    )

    source_state = (
        "VERIFIED_READ_ONLY"
        if valid
        else "BLOCKED"
    )

    return {
        "version": VERSION,
        "type": TYPE,
        "generatedAt": now_iso(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": dict(SAFETY_FALSE),
        "sideEffects": {
            "network": False,
            "filesystemWrite": True,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "verification": {
            "valid": valid,
            "sourceExists": source_exists,
            "sourceSha256": source_sha,
        },
        "sources": {
            "phase34": {
                "file": str(SOURCE_FILE),
                "exists": source_exists,
                "sha256": source_sha,
                "type": SOURCE_TYPE,
            }
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": dict(POLICY),
    }


def main():
    errors = []

    source_exists = safe_exists(SOURCE_FILE)

    source_sha = (
        sha256_file(SOURCE_FILE)
        if source_exists
        else None
    )

    report = None

    if source_exists:
        report = load_json(
            SOURCE_FILE,
            errors,
        )

    if report is not None:
        validate_common(
            report,
            errors,
        )

        validate_verification(
            report,
            source_sha,
            errors,
        )

        validate_digest(
            report,
            errors,
        )

        validate_no_full_report_copy(
            report,
            errors,
        )

    output = build_report(
        source_exists,
        source_sha,
        errors,
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as fh:
        json.dump(
            output,
            fh,
            indent=2,
            sort_keys=False,
        )
        fh.write("\n")

    print(
        f"STATE: {output['state']}"
    )
    print(
        f"SOURCE STATE: {output['sourceState']}"
    )
    print(
        f"VALID: {output['verification']['valid']}"
    )
    print(
        f"ERROR COUNT: {output['errorCount']}"
    )

    return 0 if output["verification"]["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
