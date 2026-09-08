#!/usr/bin/env python3

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


VERSION = "1.0.0"
TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY"

ROOT = Path(os.environ.get(
    "AACP_OUTPUT_DIR",
    "provider-output/aacp-observer"
))

AUDIT_FILE = ROOT / \
    "latest-aacp-evidence-chain-health-audit-history-audit.json"

VERIFY_FILE = ROOT / \
    "latest-aacp-evidence-chain-health-audit-history-audit-verify.json"

OUTPUT_FILE = ROOT / \
    "latest-aacp-evidence-chain-health-audit-history-audit-history.json"

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


def safe_exists(path):
    try:
        return path.is_file()
    except Exception:
        return False


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, str(exc)


def add_error(errors, code):
    if code not in errors:
        errors.append(code)


def valid_safety(obj):
    return (
        isinstance(obj, dict)
        and obj.get("safety") == SAFETY_FALSE
        and obj.get("sideEffects") == SAFETY_FALSE
        and obj.get("executionAuthorized") is False
    )


def valid_policy(obj):
    return obj.get("policy") == POLICY


def valid_root(obj, expected_type):
    if not isinstance(obj, dict):
        return False

    if obj.get("version") != VERSION:
        return False

    if obj.get("type") != expected_type:
        return False

    if obj.get("mode") != "READ_ONLY":
        return False

    if obj.get("state") not in ALLOWED_STATES:
        return False

    if obj.get("sourceState") not in ALLOWED_STATES:
        return False

    if not valid_safety(obj):
        return False

    if not valid_policy(obj):
        return False

    return True


def compact_snapshot(path, obj):
    return {
        "file": path.name,
        "exists": safe_exists(path),
        "sha256": safe_sha(path),
        "state": obj.get("state"),
        "sourceState": obj.get("sourceState"),
        "executionAuthorized": obj.get(
            "executionAuthorized"
        ),
        "errorCount": obj.get("errorCount"),
    }


def validate_source(
    path,
    expected_type,
    label,
    errors,
):
    if not safe_exists(path):
        add_error(
            errors,
            f"{label.upper()}_MISSING",
        )
        return None

    obj, parse_error = load_json(path)

    if parse_error is not None:
        add_error(
            errors,
            f"{label.upper()}_INVALID_JSON",
        )
        return None

    if not valid_root(obj, expected_type):
        add_error(
            errors,
            f"{label.upper()}_INVALID_ROOT",
        )

    if obj.get("executionAuthorized") is not False:
        add_error(
            errors,
            f"{label.upper()}_EXECUTION_AUTHORIZED",
        )

    return obj


def validate_cross_layer(audit, verify, errors):
    if audit is None or verify is None:
        return

    if audit.get("state") != verify.get("state"):
        add_error(
            errors,
            "STATE_MISMATCH",
        )

    if audit.get("sourceState") != verify.get(
        "sourceState"
    ):
        add_error(
            errors,
            "SOURCE_STATE_MISMATCH",
        )

    audit_section = audit.get("audit")

    if not isinstance(audit_section, dict):
        add_error(
            errors,
            "AUDIT_SECTION_INVALID",
        )
    else:
        for field in (
            "valid",
            "historyExists",
            "verifierExists",
            "crossLayerValid",
        ):
            if audit_section.get(field) is not True:
                add_error(
                    errors,
                    f"AUDIT_{field.upper()}_INVALID",
                )


def build_report(
    state,
    source_state,
    audit,
    verify,
    errors,
):
    report = {
        "version": VERSION,
        "type": TYPE,
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": dict(SAFETY_FALSE),
        "sideEffects": dict(SAFETY_FALSE),
        "snapshots": {
            "audit": compact_snapshot(
                AUDIT_FILE,
                audit or {},
            ),
            "verify": compact_snapshot(
                VERIFY_FILE,
                verify or {},
            ),
        },
        "consistency": {
            "auditExists": safe_exists(AUDIT_FILE),
            "verifyExists": safe_exists(VERIFY_FILE),
            "stateMatch": (
                audit is not None
                and verify is not None
                and audit.get("state")
                == verify.get("state")
            ),
            "sourceStateMatch": (
                audit is not None
                and verify is not None
                and audit.get("sourceState")
                == verify.get("sourceState")
            ),
        },
        "errors": list(errors),
        "errorCount": len(errors),
        "policy": dict(POLICY),
    }

    ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            report,
            handle,
            indent=2,
        )
        handle.write("\n")

    return report


def main():
    errors = []

    audit = validate_source(
        AUDIT_FILE,
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT",
        "audit",
        errors,
    )

    verify = validate_source(
        VERIFY_FILE,
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_VERIFY",
        "verify",
        errors,
    )

    validate_cross_layer(
        audit,
        verify,
        errors,
    )

    if audit is not None:
        state = audit.get(
            "state",
            "BLOCKED",
        )
        source_state = audit.get(
            "sourceState",
            "BLOCKED",
        )
    elif verify is not None:
        state = verify.get(
            "state",
            "BLOCKED",
        )
        source_state = verify.get(
            "sourceState",
            "BLOCKED",
        )
    else:
        state = "BLOCKED"
        source_state = "BLOCKED"

    if errors:
        state = "BLOCKED"
        source_state = "BLOCKED"

    report = build_report(
        state,
        source_state,
        audit,
        verify,
        errors,
    )

    print(
        "TERMiX AACP EVIDENCE CHAIN HEALTH "
        "AUDIT HISTORY AUDIT HISTORY v1.0"
    )
    print("READ ONLY / FAIL CLOSED")
    print(f"STATE: {report['state']}")
    print(f"SOURCE STATE: {report['sourceState']}")
    print(
        f"VALID: {report['errorCount'] == 0}"
    )
    print(f"ERRORS: {report['errorCount']}")
    print(
        "EXECUTION AUTHORIZED: "
        f"{report['executionAuthorized']}"
    )
    print(
        f"REPORT: {OUTPUT_FILE}"
    )

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
