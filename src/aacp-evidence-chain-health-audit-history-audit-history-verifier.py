#!/usr/bin/env python3

import hashlib
import json
import os
import sys
from pathlib import Path


VERSION = "1.0.0"
TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY"
)
SOURCE_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY"
)

ROOT = Path(os.environ.get(
    "AACP_OUTPUT_DIR",
    "provider-output/aacp-observer",
))

SOURCE_FILE = ROOT / (
    "latest-aacp-evidence-chain-health-audit-history-audit-history.json"
)

OUTPUT_FILE = ROOT / (
    "latest-aacp-evidence-chain-health-audit-history-"
    "audit-history-verify.json"
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

SNAPSHOT_KEYS = {
    "file",
    "exists",
    "sha256",
    "state",
    "sourceState",
    "executionAuthorized",
    "errorCount",
}

EXPECTED_SNAPSHOTS = {
    "audit": (
        "latest-aacp-evidence-chain-health-audit-history-audit.json"
    ),
    "verify": (
        "latest-aacp-evidence-chain-health-audit-history-"
        "audit-verify.json"
    ),
}


def add_error(errors, code):
    if code not in errors:
        errors.append(code)


def safe_exists(path):
    try:
        return path.is_file()
    except Exception:
        return False


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def safe_sha(path):
    try:
        return sha256_file(path) if path.is_file() else None
    except Exception:
        return None


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, str(exc)


def valid_safety(obj):
    return (
        isinstance(obj, dict)
        and obj.get("safety") == SAFETY_FALSE
        and obj.get("sideEffects") == SAFETY_FALSE
        and obj.get("executionAuthorized") is False
    )


def valid_policy(obj):
    return (
        isinstance(obj, dict)
        and obj.get("policy") == POLICY
    )


def validate_root(obj, errors):
    if not isinstance(obj, dict):
        add_error(errors, "ROOT_INVALID")
        return

    if obj.get("version") != VERSION:
        add_error(errors, "VERSION_INVALID")

    if obj.get("type") != SOURCE_TYPE:
        add_error(errors, "SOURCE_TYPE_INVALID")

    if obj.get("mode") != "READ_ONLY":
        add_error(errors, "MODE_INVALID")

    if obj.get("state") not in ALLOWED_STATES:
        add_error(errors, "STATE_INVALID")

    if obj.get("sourceState") not in ALLOWED_STATES:
        add_error(errors, "SOURCE_STATE_INVALID")

    if obj.get("executionAuthorized") is not False:
        add_error(errors, "EXECUTION_AUTHORIZED")

    if not valid_safety(obj):
        add_error(errors, "SAFETY_VIOLATION")

    if not valid_policy(obj):
        add_error(errors, "POLICY_VIOLATION")


def validate_error_model(obj, errors):
    if not isinstance(obj.get("errors"), list):
        add_error(errors, "ERRORS_INVALID")

    if not isinstance(obj.get("errorCount"), int):
        add_error(errors, "ERROR_COUNT_INVALID")
        return

    if isinstance(obj.get("errors"), list):
        if obj.get("errorCount") != len(obj["errors"]):
            add_error(errors, "ERROR_COUNT_MISMATCH")


def validate_snapshots(obj, errors):
    snapshots = obj.get("snapshots")

    if not isinstance(snapshots, dict):
        add_error(errors, "SNAPSHOTS_INVALID")
        return

    if set(snapshots.keys()) != set(EXPECTED_SNAPSHOTS.keys()):
        add_error(errors, "SNAPSHOT_KEYS_INVALID")

    for label, expected_name in EXPECTED_SNAPSHOTS.items():
        snapshot = snapshots.get(label)

        if not isinstance(snapshot, dict):
            add_error(
                errors,
                f"SNAPSHOT_{label.upper()}_INVALID",
            )
            continue

        if set(snapshot.keys()) != SNAPSHOT_KEYS:
            add_error(
                errors,
                f"SNAPSHOT_{label.upper()}_FIELDS_INVALID",
            )

        if snapshot.get("file") != expected_name:
            add_error(
                errors,
                f"SNAPSHOT_{label.upper()}_FILE_INVALID",
            )

        actual_path = ROOT / expected_name
        actual_exists = safe_exists(actual_path)

        if snapshot.get("exists") is not actual_exists:
            add_error(
                errors,
                f"SNAPSHOT_{label.upper()}_EXISTS_MISMATCH",
            )

        actual_sha = safe_sha(actual_path)

        if snapshot.get("sha256") != actual_sha:
            add_error(
                errors,
                f"SNAPSHOT_{label.upper()}_SHA_MISMATCH",
            )

        if actual_exists:
            source_obj, parse_error = load_json(actual_path)

            if parse_error is not None:
                add_error(
                    errors,
                    f"SNAPSHOT_{label.upper()}_JSON_INVALID",
                )
                continue

            if not isinstance(source_obj, dict):
                add_error(
                    errors,
                    f"SNAPSHOT_{label.upper()}_ROOT_INVALID",
                )
                continue

            if snapshot.get("state") != source_obj.get("state"):
                add_error(
                    errors,
                    f"SNAPSHOT_{label.upper()}_STATE_MISMATCH",
                )

            if (
                snapshot.get("sourceState")
                != source_obj.get("sourceState")
            ):
                add_error(
                    errors,
                    f"SNAPSHOT_{label.upper()}_SOURCE_STATE_MISMATCH",
                )

            if (
                snapshot.get("executionAuthorized")
                != source_obj.get("executionAuthorized")
            ):
                add_error(
                    errors,
                    f"SNAPSHOT_{label.upper()}_EXECUTION_MISMATCH",
                )

            if snapshot.get("errorCount") != source_obj.get(
                "errorCount"
            ):
                add_error(
                    errors,
                    f"SNAPSHOT_{label.upper()}_ERROR_COUNT_MISMATCH",
                )


def validate_consistency(obj, errors):
    consistency = obj.get("consistency")

    if not isinstance(consistency, dict):
        add_error(errors, "CONSISTENCY_INVALID")
        return

    required = {
        "auditExists",
        "verifyExists",
        "stateMatch",
        "sourceStateMatch",
    }

    if set(consistency.keys()) != required:
        add_error(errors, "CONSISTENCY_FIELDS_INVALID")

    audit_path = ROOT / EXPECTED_SNAPSHOTS["audit"]
    verify_path = ROOT / EXPECTED_SNAPSHOTS["verify"]

    audit_exists = safe_exists(audit_path)
    verify_exists = safe_exists(verify_path)

    if consistency.get("auditExists") is not audit_exists:
        add_error(errors, "CONSISTENCY_AUDIT_EXISTS_MISMATCH")

    if consistency.get("verifyExists") is not verify_exists:
        add_error(errors, "CONSISTENCY_VERIFY_EXISTS_MISMATCH")

    audit_obj, audit_err = load_json(audit_path)
    verify_obj, verify_err = load_json(verify_path)

    if audit_err is None and verify_err is None:
        state_match = (
            isinstance(audit_obj, dict)
            and isinstance(verify_obj, dict)
            and audit_obj.get("state") == verify_obj.get("state")
        )

        source_state_match = (
            isinstance(audit_obj, dict)
            and isinstance(verify_obj, dict)
            and audit_obj.get("sourceState")
            == verify_obj.get("sourceState")
        )

        if consistency.get("stateMatch") is not state_match:
            add_error(
                errors,
                "CONSISTENCY_STATE_MATCH_MISMATCH",
            )

        if (
            consistency.get("sourceStateMatch")
            is not source_state_match
        ):
            add_error(
                errors,
                "CONSISTENCY_SOURCE_STATE_MATCH_MISMATCH",
            )


def validate_no_full_report_copy(obj, errors):
    forbidden = {
        "content",
        "report",
        "fullReport",
        "full_report",
        "raw",
        "rawReport",
        "raw_report",
    }

    present = forbidden.intersection(obj.keys())

    if present:
        add_error(errors, "FULL_REPORT_COPY_FORBIDDEN")


def build_report(source, errors):
    source_state = (
        source.get("sourceState", "BLOCKED")
        if isinstance(source, dict)
        else "BLOCKED"
    )

    state = (
        source.get("state", "BLOCKED")
        if isinstance(source, dict)
        else "BLOCKED"
    )

    if errors:
        state = "BLOCKED"
        source_state = "BLOCKED"

    report = {
        "version": VERSION,
        "type": TYPE,
        "generatedAt": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": dict(SAFETY_FALSE),
        "sideEffects": dict(SAFETY_FALSE),
        "verification": {
            "valid": not bool(errors),
            "sourceExists": safe_exists(SOURCE_FILE),
            "sha256": safe_sha(SOURCE_FILE),
        },
        "sources": {
            "auditHistory": {
                "file": SOURCE_FILE.name,
                "exists": safe_exists(SOURCE_FILE),
                "sha256": safe_sha(SOURCE_FILE),
            },
        },
        "errors": list(errors),
        "errorCount": len(errors),
        "policy": dict(POLICY),
    }

    return report


def main():
    ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    errors = []

    if not safe_exists(SOURCE_FILE):
        add_error(errors, "SOURCE_MISSING")
        source = None
    else:
        source, parse_error = load_json(SOURCE_FILE)

        if parse_error is not None:
            add_error(errors, "SOURCE_INVALID_JSON")
            source = None

    if source is not None:
        validate_root(source, errors)
        validate_error_model(source, errors)
        validate_snapshots(source, errors)
        validate_consistency(source, errors)
        validate_no_full_report_copy(source, errors)

    report = build_report(source, errors)

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "TERMiX AACP EVIDENCE CHAIN HEALTH "
        "AUDIT HISTORY AUDIT HISTORY VERIFY v1.0"
    )
    print("READ ONLY / FAIL CLOSED")
    print(f"STATE: {report['state']}")
    print(f"SOURCE STATE: {report['sourceState']}")
    print(
        f"VALID: {str(report['verification']['valid']).lower()}"
    )
    print(f"ERRORS: {report['errorCount']}")
    print("EXECUTION AUTHORIZED: false")
    print(f"REPORT: {OUTPUT_FILE}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
