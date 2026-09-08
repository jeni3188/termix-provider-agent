#!/usr/bin/env python3

import hashlib
import json
import os
import sys
from pathlib import Path


VERSION = "1.0.0"

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY"
)

PHASE31_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY"
)

PHASE32_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY"
)

ROOT = Path(
    os.environ.get(
        "AACP_OUTPUT_DIR",
        "provider-output/aacp-observer",
    )
)

PHASE31_FILE = ROOT / (
    "latest-aacp-evidence-chain-health-audit-history-"
    "audit-history.json"
)

PHASE32_FILE = ROOT / (
    "latest-aacp-evidence-chain-health-audit-history-"
    "audit-history-verify.json"
)

OUTPUT_FILE = ROOT / (
    "latest-aacp-evidence-chain-health-cross-layer-"
    "integrity-verify.json"
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
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, str(exc)


def valid_safety(obj, errors, prefix):
    safety = obj.get("safety")
    if safety != SAFETY_FALSE:
        add_error(
            errors,
            f"{prefix}_SAFETY_VIOLATION",
            "safety invariants are not all false",
        )

    side_effects = obj.get("sideEffects")
    if side_effects != SAFETY_FALSE:
        add_error(
            errors,
            f"{prefix}_SIDE_EFFECTS_VIOLATION",
            "sideEffects invariants are not all false",
        )


def valid_policy(obj, errors, prefix):
    if obj.get("policy") != POLICY:
        add_error(
            errors,
            f"{prefix}_POLICY_VIOLATION",
            "policy does not match READ_ONLY FAIL_CLOSED",
        )


def validate_common(obj, expected_type, errors, prefix):
    if not isinstance(obj, dict):
        add_error(
            errors,
            f"{prefix}_ROOT_INVALID",
            "root object is not a JSON object",
        )
        return

    if obj.get("version") != VERSION:
        add_error(
            errors,
            f"{prefix}_VERSION_INVALID",
            "version must be 1.0.0",
        )

    if obj.get("type") != expected_type:
        add_error(
            errors,
            f"{prefix}_TYPE_INVALID",
            "unexpected report type",
        )

    if obj.get("mode") != "READ_ONLY":
        add_error(
            errors,
            f"{prefix}_MODE_INVALID",
            "mode must be READ_ONLY",
        )

    if obj.get("state") not in ALLOWED_STATES:
        add_error(
            errors,
            f"{prefix}_STATE_INVALID",
            "state is not allowed",
        )

    if obj.get("sourceState") not in ALLOWED_STATES:
        add_error(
            errors,
            f"{prefix}_SOURCE_STATE_INVALID",
            "sourceState is not allowed",
        )

    if obj.get("executionAuthorized") is not False:
        add_error(
            errors,
            f"{prefix}_EXECUTION_AUTHORIZED",
            "executionAuthorized must be false",
        )

    valid_safety(obj, errors, prefix)
    valid_policy(obj, errors, prefix)


def validate_error_model(obj, errors, prefix):
    if not isinstance(obj, dict):
        return

    report_errors = obj.get("errors")

    if not isinstance(report_errors, list):
        add_error(
            errors,
            f"{prefix}_ERRORS_INVALID",
            "errors must be a list",
        )
        return

    count = obj.get("errorCount")

    if not isinstance(count, int):
        add_error(
            errors,
            f"{prefix}_ERROR_COUNT_INVALID",
            "errorCount must be an integer",
        )
    elif count != len(report_errors):
        add_error(
            errors,
            f"{prefix}_ERROR_COUNT_MISMATCH",
            "errorCount does not match errors length",
        )


def validate_file_hash(path, expected_hash, errors, code):
    exists = safe_exists(path)

    if not exists:
        if expected_hash is not None:
            add_error(
                errors,
                code + "_MISSING",
                "referenced file does not exist",
            )
        return

    actual = sha256_file(path)

    if actual != expected_hash:
        add_error(
            errors,
            code + "_SHA_MISMATCH",
            "referenced file SHA-256 does not match",
        )


def validate_phase31(source, errors):
    if not isinstance(source, dict):
        return

    snapshots = source.get("snapshots")

    if not isinstance(snapshots, dict):
        add_error(
            errors,
            "PHASE31_SNAPSHOTS_INVALID",
            "Phase 31 snapshots must be an object",
        )
        return

    expected = {
        "audit": (
            "latest-aacp-evidence-chain-health-audit-history-audit.json"
        ),
        "verify": (
            "latest-aacp-evidence-chain-health-audit-history-"
            "audit-verify.json"
        ),
    }

    for key, filename in expected.items():
        snapshot = snapshots.get(key)

        if not isinstance(snapshot, dict):
            add_error(
                errors,
                f"PHASE31_SNAPSHOT_{key.upper()}_INVALID",
                "snapshot is not an object",
            )
            continue

        if snapshot.get("file") != filename:
            add_error(
                errors,
                f"PHASE31_SNAPSHOT_{key.upper()}_FILE",
                "snapshot filename mismatch",
            )

        path = ROOT / filename

        actual_exists = safe_exists(path)

        if snapshot.get("exists") != actual_exists:
            add_error(
                errors,
                f"PHASE31_SNAPSHOT_{key.upper()}_EXISTS",
                "snapshot existence mismatch",
            )

        if actual_exists:
            actual_sha = sha256_file(path)

            if snapshot.get("sha256") != actual_sha:
                add_error(
                    errors,
                    f"PHASE31_SNAPSHOT_{key.upper()}_SHA",
                    "snapshot SHA-256 mismatch",
                )

            child, child_error = load_json(path)

            if child_error is not None:
                add_error(
                    errors,
                    f"PHASE31_SNAPSHOT_{key.upper()}_JSON",
                    "snapshot target is not valid JSON",
                )
            elif isinstance(child, dict):
                for field in (
                    "state",
                    "sourceState",
                    "executionAuthorized",
                    "errorCount",
                ):
                    if snapshot.get(field) != child.get(field):
                        add_error(
                            errors,
                            f"PHASE31_SNAPSHOT_{key.upper()}_{field.upper()}",
                            f"snapshot {field} mismatch",
                        )

    consistency = source.get("consistency")

    if not isinstance(consistency, dict):
        add_error(
            errors,
            "PHASE31_CONSISTENCY_INVALID",
            "Phase 31 consistency is not an object",
        )
        return

    audit_path = ROOT / expected["audit"]
    verify_path = ROOT / expected["verify"]

    audit, audit_error = load_json(audit_path)
    verify, verify_error = load_json(verify_path)

    audit_exists = audit_error is None
    verify_exists = verify_error is None

    state_match = (
        isinstance(audit, dict)
        and isinstance(verify, dict)
        and audit.get("state") == verify.get("state")
    )

    source_state_match = (
        isinstance(audit, dict)
        and isinstance(verify, dict)
        and audit.get("sourceState")
        == verify.get("sourceState")
    )

    expected_consistency = {
        "auditExists": audit_exists,
        "verifyExists": verify_exists,
        "stateMatch": state_match,
        "sourceStateMatch": source_state_match,
    }

    if consistency != expected_consistency:
        add_error(
            errors,
            "PHASE31_CONSISTENCY_MISMATCH",
            "Phase 31 consistency does not match upstream files",
        )


def validate_phase32(source, phase31, errors):
    if not isinstance(source, dict):
        return

    if phase32_file := PHASE32_FILE:
        exists = safe_exists(phase32_file)

        if not exists:
            add_error(
                errors,
                "PHASE32_MISSING",
                "Phase 32 verifier report does not exist",
            )
            return

        phase32_sha = sha256_file(phase32_file)

        if not isinstance(phase31, dict):
            add_error(
                errors,
                "PHASE31_MISSING",
                "Phase 31 report is missing or invalid",
            )
            return

        if phase31.get("type") != PHASE31_TYPE:
            add_error(
                errors,
                "PHASE31_TYPE_CHAIN_INVALID",
                "Phase 31 type is invalid for Phase 32 chain",
            )

        phase32, phase32_error = load_json(phase32_file)

        if phase32_error is not None:
            add_error(
                errors,
                "PHASE32_JSON_INVALID",
                "Phase 32 verifier report is not valid JSON",
            )
            return

        validate_common(
            phase32,
            PHASE32_TYPE,
            errors,
            "PHASE32",
        )

        validate_error_model(
            phase32,
            errors,
            "PHASE32",
        )

        sources = phase32.get("sources")

        if not isinstance(sources, dict):
            add_error(
                errors,
                "PHASE32_SOURCES_INVALID",
                "Phase 32 sources must be an object",
            )
        else:
            history = sources.get("auditHistory")

            if not isinstance(history, dict):
                add_error(
                    errors,
                    "PHASE32_SOURCE_INVALID",
                    "Phase 32 auditHistory source is invalid",
                )
            else:
                expected_file = PHASE31_FILE.name

                if history.get("file") != expected_file:
                    add_error(
                        errors,
                        "PHASE32_SOURCE_FILE",
                        "Phase 32 source filename mismatch",
                    )

                if history.get("exists") != safe_exists(PHASE31_FILE):
                    add_error(
                        errors,
                        "PHASE32_SOURCE_EXISTS",
                        "Phase 32 source existence mismatch",
                    )

                if history.get("sha256") != sha256_file(PHASE31_FILE):
                    add_error(
                        errors,
                        "PHASE32_SOURCE_SHA",
                        "Phase 32 source SHA-256 mismatch",
                    )

        verification = phase32.get("verification")

        if not isinstance(verification, dict):
            add_error(
                errors,
                "PHASE32_VERIFICATION_INVALID",
                "Phase 32 verification is not an object",
            )
        else:
            if verification.get("sourceExists") != safe_exists(
                PHASE31_FILE
            ):
                add_error(
                    errors,
                    "PHASE32_VERIFICATION_EXISTS",
                    "Phase 32 sourceExists mismatch",
                )

            if verification.get("sha256") != sha256_file(PHASE31_FILE):
                add_error(
                    errors,
                    "PHASE32_VERIFICATION_SHA",
                    "Phase 32 verification SHA mismatch",
                )

            expected_valid = (
                phase32.get("errorCount") == 0
            )

            if verification.get("valid") != expected_valid:
                add_error(
                    errors,
                    "PHASE32_VERIFICATION_VALID",
                    "Phase 32 verification.valid mismatch",
                )

        if (
            isinstance(phase31, dict)
            and isinstance(phase32, dict)
        ):
            if phase32.get("sourceState") != phase31.get("sourceState"):
                add_error(
                    errors,
                    "CROSS_LAYER_SOURCE_STATE",
                    "Phase 32 sourceState does not match Phase 31",
                )

            if phase32.get("executionAuthorized") is not False:
                add_error(
                    errors,
                    "CROSS_LAYER_EXECUTION",
                    "Phase 32 execution authorization is not false",
                )

            if (
                phase31.get("state") == "VERIFIED_READ_ONLY"
                and phase32.get("state") != "VERIFIED_READ_ONLY"
            ):
                add_error(
                    errors,
                    "CROSS_LAYER_STATE",
                    "Phase 32 did not preserve verified Phase 31 state",
                )

        _ = phase32_sha


def validate_no_full_report_copy(obj, errors, prefix):
    if not isinstance(obj, dict):
        return

    found = FORBIDDEN_COPY_KEYS.intersection(obj.keys())

    if found:
        add_error(
            errors,
            f"{prefix}_FULL_REPORT_COPY",
            "full-report copy fields are forbidden",
        )


def build_report(phase31, phase32, errors):
    valid = not errors

    if valid:
        state = "VERIFIED_READ_ONLY"
        source_state = "VERIFIED_READ_ONLY"
    else:
        state = "BLOCKED"
        source_state = "BLOCKED"

    return {
        "version": VERSION,
        "type": TYPE,
        "generatedAt": "",
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": SAFETY_FALSE,
        "sideEffects": SAFETY_FALSE,
        "verification": {
            "valid": valid,
            "phase31Exists": safe_exists(PHASE31_FILE),
            "phase31Sha256": sha256_file(PHASE31_FILE),
            "phase32Exists": safe_exists(PHASE32_FILE),
            "phase32Sha256": sha256_file(PHASE32_FILE),
        },
        "sources": {
            "phase31": {
                "file": PHASE31_FILE.name,
                "exists": safe_exists(PHASE31_FILE),
                "sha256": sha256_file(PHASE31_FILE),
                "type": (
                    phase31.get("type")
                    if isinstance(phase31, dict)
                    else None
                ),
            },
            "phase32": {
                "file": PHASE32_FILE.name,
                "exists": safe_exists(PHASE32_FILE),
                "sha256": sha256_file(PHASE32_FILE),
                "type": (
                    phase32.get("type")
                    if isinstance(phase32, dict)
                    else None
                ),
            },
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": POLICY,
    }


def main():
    errors = []

    phase31, phase31_error = load_json(PHASE31_FILE)

    if phase31_error is not None:
        add_error(
            errors,
            "PHASE31_JSON_INVALID",
            "Phase 31 report cannot be loaded",
        )
        phase31 = None

    phase32, phase32_error = load_json(PHASE32_FILE)

    if phase32_error is not None:
        add_error(
            errors,
            "PHASE32_JSON_INVALID",
            "Phase 32 verifier report cannot be loaded",
        )
        phase32 = None

    validate_common(
        phase31,
        PHASE31_TYPE,
        errors,
        "PHASE31",
    )

    validate_error_model(
        phase31,
        errors,
        "PHASE31",
    )

    validate_common(
        phase32,
        PHASE32_TYPE,
        errors,
        "PHASE32",
    )

    validate_error_model(
        phase32,
        errors,
        "PHASE32",
    )

    validate_no_full_report_copy(
        phase31,
        errors,
        "PHASE31",
    )

    validate_no_full_report_copy(
        phase32,
        errors,
        "PHASE32",
    )

    validate_phase31(
        phase31,
        errors,
    )

    validate_phase32(
        phase32,
        phase31,
        errors,
    )

    report = build_report(
        phase31,
        phase32,
        errors,
    )

    ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    report["generatedAt"] = (
        __import__("datetime")
        .datetime.now(
            __import__("datetime").timezone.utc
        )
        .isoformat()
        .replace("+00:00", "Z")
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            report,
            handle,
            separators=(",", ":"),
        )
        handle.write("\n")

    if errors:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
