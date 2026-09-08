#!/usr/bin/env python3

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


VERSION = "1.0.0"
TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION"

PHASE31_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY"
PHASE32_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY"
PHASE33_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY"

ROOT = Path(
    os.environ.get("AACP_OUTPUT_DIR", "provider-output/aacp-observer")
)

PHASE31_FILE = (
    ROOT / "latest-aacp-evidence-chain-health-audit-history-audit-history.json"
)
PHASE32_FILE = (
    ROOT / "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json"
)
PHASE33_FILE = (
    ROOT / "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json"
)

OUTPUT_FILE = (
    ROOT / "latest-aacp-evidence-chain-health-integrity-attestation.json"
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
        return path.exists() and path.is_file()
    except Exception:
        return False


def sha256_file(path):
    if not safe_exists(path):
        return None

    h = hashlib.sha256()

    try:
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def load_json(path, errors, label):
    if not safe_exists(path):
        add_error(
            errors,
            f"{label.upper()}_MISSING",
            f"{label} report is missing",
        )
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
    except Exception as exc:
        add_error(
            errors,
            f"{label.upper()}_INVALID_JSON",
            f"{label} report is invalid JSON: {type(exc).__name__}",
        )
        return None

    if not isinstance(value, dict):
        add_error(
            errors,
            f"{label.upper()}_INVALID_ROOT",
            f"{label} report root must be an object",
        )
        return None

    return value


def valid_safety(value):
    return value == SAFETY_FALSE


def valid_policy(value):
    return value == POLICY


def validate_common(report, expected_type, label, errors):
    if not isinstance(report, dict):
        return

    if report.get("version") != VERSION:
        add_error(
            errors,
            f"{label.upper()}_VERSION",
            f"{label} version is invalid",
        )

    if report.get("type") != expected_type:
        add_error(
            errors,
            f"{label.upper()}_TYPE",
            f"{label} type is invalid",
        )

    if report.get("mode") != "READ_ONLY":
        add_error(
            errors,
            f"{label.upper()}_MODE",
            f"{label} mode is not READ_ONLY",
        )

    if report.get("executionAuthorized") is not False:
        add_error(
            errors,
            f"{label.upper()}_EXECUTION_AUTHORIZED",
            f"{label} executionAuthorized must be false",
        )

    if not valid_safety(report.get("safety")):
        add_error(
            errors,
            f"{label.upper()}_SAFETY",
            f"{label} safety policy is invalid",
        )

    if not valid_policy(report.get("policy")):
        add_error(
            errors,
            f"{label.upper()}_POLICY",
            f"{label} policy is invalid",
        )


def validate_error_model(report, label, errors):
    if not isinstance(report, dict):
        return

    report_errors = report.get("errors")
    error_count = report.get("errorCount")

    if not isinstance(report_errors, list):
        add_error(
            errors,
            f"{label.upper()}_ERRORS",
            f"{label} errors must be a list",
        )
        return

    if error_count != len(report_errors):
        add_error(
            errors,
            f"{label.upper()}_ERROR_COUNT",
            f"{label} errorCount does not match errors length",
        )


def validate_state(report, label, errors):
    if not isinstance(report, dict):
        return

    state = report.get("state")

    if state not in ALLOWED_STATES:
        add_error(
            errors,
            f"{label.upper()}_STATE",
            f"{label} state is invalid",
        )


def validate_phase31(report, errors):
    label = "phase31"

    validate_common(
        report,
        PHASE31_TYPE,
        label,
        errors,
    )

    validate_state(report, label, errors)
    validate_error_model(report, label, errors)

    if isinstance(report, dict):
        if report.get("state") == "VERIFIED_READ_ONLY":
            if report.get("sourceState") != "VERIFIED_READ_ONLY":
                add_error(
                    errors,
                    "PHASE31_SOURCE_STATE",
                    "Phase 31 verified state requires VERIFIED_READ_ONLY sourceState",
                )


def validate_phase32(report, phase31, phase31_sha, errors):
    label = "phase32"

    validate_common(
        report,
        PHASE32_TYPE,
        label,
        errors,
    )

    validate_state(report, label, errors)
    validate_error_model(report, label, errors)

    if not isinstance(report, dict):
        return

    if report.get("sourceState") not in ALLOWED_STATES:
        add_error(
            errors,
            "PHASE32_SOURCE_STATE",
            "Phase 32 sourceState is invalid",
        )

    verification = report.get("verification")

    if not isinstance(verification, dict):
        add_error(
            errors,
            "PHASE32_VERIFICATION",
            "Phase 32 verification must be an object",
        )
    else:
        if verification.get("valid") is not True:
            add_error(
                errors,
                "PHASE32_VERIFICATION_INVALID",
                "Phase 32 verification.valid must be true",
            )

        if verification.get("sourceExists") is not True:
            add_error(
                errors,
                "PHASE32_SOURCE_MISSING",
                "Phase 32 must confirm Phase 31 source exists",
            )

        if phase31_sha is not None:
            if verification.get("sha256") != phase31_sha:
                add_error(
                    errors,
                    "PHASE32_SOURCE_SHA_MISMATCH",
                    "Phase 32 verification SHA does not match Phase 31 SHA",
                )

    sources = report.get("sources")

    if not isinstance(sources, dict):
        add_error(
            errors,
            "PHASE32_SOURCES",
            "Phase 32 sources must be an object",
        )
    else:
        audit_history = sources.get("auditHistory")

        if not isinstance(audit_history, dict):
            add_error(
                errors,
                "PHASE32_AUDIT_HISTORY_SOURCE",
                "Phase 32 auditHistory source is invalid",
            )
        else:
            if audit_history.get("exists") is not True:
                add_error(
                    errors,
                    "PHASE32_AUDIT_HISTORY_MISSING",
                    "Phase 32 auditHistory source must exist",
                )

            if phase31_sha is not None:
                if audit_history.get("sha256") != phase31_sha:
                    add_error(
                        errors,
                        "PHASE32_AUDIT_HISTORY_SHA_MISMATCH",
                        "Phase 32 auditHistory SHA does not match Phase 31 SHA",
                    )

    if report.get("executionAuthorized") is not False:
        add_error(
            errors,
            "PHASE32_EXECUTION_AUTHORIZED",
            "Phase 32 executionAuthorized must be false",
        )

    if not isinstance(phase31, dict):
        add_error(
            errors,
            "PHASE32_PHASE31_INVALID",
            "Phase 31 dependency is missing or invalid",
        )


def validate_phase33(report, phase31, phase32, phase31_sha, phase32_sha, errors):
    label = "phase33"

    validate_common(
        report,
        PHASE33_TYPE,
        label,
        errors,
    )

    validate_state(report, label, errors)
    validate_error_model(report, label, errors)

    if not isinstance(report, dict):
        return

    if report.get("sourceState") not in ALLOWED_STATES:
        add_error(
            errors,
            "PHASE33_SOURCE_STATE",
            "Phase 33 sourceState is invalid",
        )

    verification = report.get("verification")

    if not isinstance(verification, dict):
        add_error(
            errors,
            "PHASE33_VERIFICATION",
            "Phase 33 verification must be an object",
        )
    else:
        if verification.get("valid") is not True:
            add_error(
                errors,
                "PHASE33_VERIFICATION_INVALID",
                "Phase 33 verification.valid must be true",
            )

        if phase31_sha is not None:
            if verification.get("phase31Sha256") != phase31_sha:
                add_error(
                    errors,
                    "PHASE33_PHASE31_SHA_MISMATCH",
                    "Phase 33 Phase 31 SHA does not match actual Phase 31 SHA",
                )

        if phase32_sha is not None:
            if verification.get("phase32Sha256") != phase32_sha:
                add_error(
                    errors,
                    "PHASE33_PHASE32_SHA_MISMATCH",
                    "Phase 33 Phase 32 SHA does not match actual Phase 32 SHA",
                )

    sources = report.get("sources")

    if not isinstance(sources, dict):
        add_error(
            errors,
            "PHASE33_SOURCES",
            "Phase 33 sources must be an object",
        )
    else:
        source31 = sources.get("phase31")
        source32 = sources.get("phase32")

        if not isinstance(source31, dict):
            add_error(
                errors,
                "PHASE33_PHASE31_SOURCE",
                "Phase 33 phase31 source is invalid",
            )
        else:
            if source31.get("exists") is not True:
                add_error(
                    errors,
                    "PHASE33_PHASE31_SOURCE_MISSING",
                    "Phase 33 must confirm Phase 31 exists",
                )

            if source31.get("type") != PHASE31_TYPE:
                add_error(
                    errors,
                    "PHASE33_PHASE31_SOURCE_TYPE",
                    "Phase 33 Phase 31 source type is invalid",
                )

            if phase31_sha is not None:
                if source31.get("sha256") != phase31_sha:
                    add_error(
                        errors,
                        "PHASE33_PHASE31_SOURCE_SHA",
                        "Phase 33 Phase 31 source SHA does not match",
                    )

        if not isinstance(source32, dict):
            add_error(
                errors,
                "PHASE33_PHASE32_SOURCE",
                "Phase 33 phase32 source is invalid",
            )
        else:
            if source32.get("exists") is not True:
                add_error(
                    errors,
                    "PHASE33_PHASE32_SOURCE_MISSING",
                    "Phase 33 must confirm Phase 32 exists",
                )

            if source32.get("type") != PHASE32_TYPE:
                add_error(
                    errors,
                    "PHASE33_PHASE32_SOURCE_TYPE",
                    "Phase 33 Phase 32 source type is invalid",
                )

            if phase32_sha is not None:
                if source32.get("sha256") != phase32_sha:
                    add_error(
                        errors,
                        "PHASE33_PHASE32_SOURCE_SHA",
                        "Phase 33 Phase 32 source SHA does not match",
                    )

    if report.get("executionAuthorized") is not False:
        add_error(
            errors,
            "PHASE33_EXECUTION_AUTHORIZED",
            "Phase 33 executionAuthorized must be false",
        )

    if not isinstance(phase31, dict):
        add_error(
            errors,
            "PHASE33_PHASE31_INVALID",
            "Phase 31 dependency is missing or invalid",
        )

    if not isinstance(phase32, dict):
        add_error(
            errors,
            "PHASE33_PHASE32_INVALID",
            "Phase 32 dependency is missing or invalid",
        )


def validate_no_full_report_copy(report, label, errors):
    if not isinstance(report, dict):
        return

    for key in FORBIDDEN_COPY_KEYS:
        if key in report:
            add_error(
                errors,
                f"{label.upper()}_FULL_REPORT_COPY",
                f"{label} contains forbidden full-report field: {key}",
            )


def canonical_attestation_payload(
    phase31_sha,
    phase32_sha,
    phase33_sha,
):
    payload = {
        "phase31Sha256": phase31_sha,
        "phase32Sha256": phase32_sha,
        "phase33Sha256": phase33_sha,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def build_report(
    phase31,
    phase32,
    phase33,
    phase31_sha,
    phase32_sha,
    phase33_sha,
    errors,
):
    valid = len(errors) == 0

    state = "VERIFIED_READ_ONLY" if valid else "BLOCKED"

    canonical = canonical_attestation_payload(
        phase31_sha,
        phase32_sha,
        phase33_sha,
    )

    attestation_digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest() if valid else None

    # Phase 32 may legitimately report INCOMPLETE while its
    # verification remains valid. Phase 33 establishes the
    # cross-layer integrity state, so a successful Phase 34
    # attestation must inherit VERIFIED_READ_ONLY rather than
    # treating an upstream INCOMPLETE state as BLOCKED.
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
            "post": False,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "verification": {
            "valid": valid,
            "phase31Exists": phase31_sha is not None,
            "phase31Sha256": phase31_sha,
            "phase32Exists": phase32_sha is not None,
            "phase32Sha256": phase32_sha,
            "phase33Exists": phase33_sha is not None,
            "phase33Sha256": phase33_sha,
            "canonicalPayloadSha256": (
                hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                if valid
                else None
            ),
            "attestationDigest": attestation_digest,
        },
        "sources": {
            "phase31": {
                "file": str(PHASE31_FILE),
                "exists": phase31_sha is not None,
                "sha256": phase31_sha,
                "type": PHASE31_TYPE,
            },
            "phase32": {
                "file": str(PHASE32_FILE),
                "exists": phase32_sha is not None,
                "sha256": phase32_sha,
                "type": PHASE32_TYPE,
            },
            "phase33": {
                "file": str(PHASE33_FILE),
                "exists": phase33_sha is not None,
                "sha256": phase33_sha,
                "type": PHASE33_TYPE,
            },
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": dict(POLICY),
    }


def write_output(report):
    ROOT.mkdir(parents=True, exist_ok=True)

    temp_file = OUTPUT_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            sort_keys=False,
            ensure_ascii=False,
        )
        f.write("\n")

    temp_file.replace(OUTPUT_FILE)


def main():
    errors = []

    phase31_sha = sha256_file(PHASE31_FILE)
    phase32_sha = sha256_file(PHASE32_FILE)
    phase33_sha = sha256_file(PHASE33_FILE)

    phase31 = load_json(PHASE31_FILE, errors, "phase31")
    phase32 = load_json(PHASE32_FILE, errors, "phase32")
    phase33 = load_json(PHASE33_FILE, errors, "phase33")

    validate_phase31(phase31, errors)

    validate_phase32(
        phase32,
        phase31,
        phase31_sha,
        errors,
    )

    validate_phase33(
        phase33,
        phase31,
        phase32,
        phase31_sha,
        phase32_sha,
        errors,
    )

    validate_no_full_report_copy(
        phase31,
        "phase31",
        errors,
    )
    validate_no_full_report_copy(
        phase32,
        "phase32",
        errors,
    )
    validate_no_full_report_copy(
        phase33,
        "phase33",
        errors,
    )

    report = build_report(
        phase31,
        phase32,
        phase33,
        phase31_sha,
        phase32_sha,
        phase33_sha,
        errors,
    )

    try:
        write_output(report)
    except Exception as exc:
        print(
            f"FATAL: unable to write attestation: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 2

    print(json.dumps(report, indent=2))

    return 0 if report["verification"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
