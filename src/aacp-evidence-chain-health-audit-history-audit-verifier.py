#!/usr/bin/env python3

import hashlib
import json
import os
import sys
from pathlib import Path


VERSION = "1.0.0"
TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_VERIFY"

ROOT = Path(os.environ.get(
    "AACP_OUTPUT_DIR",
    "provider-output/aacp-observer"
))

AUDIT_FILE = ROOT / "latest-aacp-evidence-chain-health-audit-history-audit.json"
HISTORY_FILE = ROOT / "latest-aacp-evidence-chain-health-audit-history.json"
HISTORY_VERIFY_FILE = ROOT / "latest-aacp-evidence-chain-health-audit-history-verify.json"
CHAIN_AUDIT_FILE = ROOT / "latest-aacp-evidence-chain-health-audit.json"
CHAIN_VERIFY_FILE = ROOT / "latest-aacp-evidence-chain-health-audit-verify.json"

OUTPUT_FILE = ROOT / "latest-aacp-evidence-chain-health-audit-history-audit-verify.json"

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
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:
        return None, str(exc)


def add_error(errors, code):
    if code not in errors:
        errors.append(code)


def valid_safety(obj):
    return obj.get("safety") == SAFETY_FALSE and \
           obj.get("sideEffects") == SAFETY_FALSE


def valid_policy(obj):
    return obj.get("policy") == POLICY


def validate_root(obj, errors):
    if not isinstance(obj, dict):
        add_error(errors, "AUDIT_VERIFY_ROOT_INVALID")
        return

    if obj.get("version") != VERSION:
        add_error(errors, "AUDIT_VERIFY_VERSION_INVALID")

    if obj.get("type") != "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT":
        add_error(errors, "AUDIT_VERIFY_SOURCE_TYPE_INVALID")

    if obj.get("mode") != "READ_ONLY":
        add_error(errors, "AUDIT_VERIFY_MODE_INVALID")

    if obj.get("state") not in ALLOWED_STATES:
        add_error(errors, "AUDIT_VERIFY_STATE_INVALID")

    if obj.get("sourceState") not in ALLOWED_STATES:
        add_error(errors, "AUDIT_VERIFY_SOURCE_STATE_INVALID")

    if obj.get("executionAuthorized") is not False:
        add_error(errors, "AUDIT_VERIFY_EXECUTION_AUTHORIZED")

    if not valid_safety(obj):
        add_error(errors, "AUDIT_VERIFY_SAFETY_VIOLATION")

    if not valid_policy(obj):
        add_error(errors, "AUDIT_VERIFY_POLICY_VIOLATION")


def validate_audit_section(obj, errors):
    audit = obj.get("audit")

    if not isinstance(audit, dict):
        add_error(errors, "AUDIT_SECTION_MISSING")
        return

    required = {
        "valid",
        "historyExists",
        "verifierExists",
        "crossLayerValid",
    }

    missing = required - set(audit.keys())

    if missing:
        add_error(errors, "AUDIT_SECTION_FIELDS_MISSING")

    if audit.get("valid") is not True:
        add_error(errors, "AUDIT_SECTION_VALID_FALSE")

    if audit.get("historyExists") is not True:
        add_error(errors, "AUDIT_HISTORY_MISSING")

    if audit.get("verifierExists") is not True:
        add_error(errors, "AUDIT_VERIFIER_MISSING")

    if audit.get("crossLayerValid") is not True:
        add_error(errors, "AUDIT_CROSS_LAYER_INVALID")


def validate_sources(obj, errors):
    sources = obj.get("sources")

    if not isinstance(sources, dict):
        add_error(errors, "AUDIT_VERIFY_SOURCES_MISSING")
        return

    expected = {
        "history": HISTORY_FILE.name,
        "verifier": HISTORY_VERIFY_FILE.name,
    }

    for key, expected_name in expected.items():
        source = sources.get(key)

        if not isinstance(source, dict):
            add_error(errors, f"SOURCE_{key.upper()}_INVALID")
            continue

        if source.get("file") != expected_name:
            add_error(errors, f"SOURCE_{key.upper()}_FILE_INVALID")

        actual_path = ROOT / expected_name
        actual_exists = safe_exists(actual_path)

        if source.get("exists") is not actual_exists:
            add_error(errors, f"SOURCE_{key.upper()}_EXISTS_MISMATCH")

        if actual_exists:
            actual_sha = safe_sha(actual_path)
            if source.get("sha256") != actual_sha:
                add_error(errors, f"SOURCE_{key.upper()}_SHA_MISMATCH")


def validate_upstream(path, expected_type, expected_state, errors, label):
    obj, err = load_json(path)

    if err is not None:
        add_error(errors, f"{label}_JSON_INVALID")
        return None

    if not isinstance(obj, dict):
        add_error(errors, f"{label}_ROOT_INVALID")
        return None

    if obj.get("type") != expected_type:
        add_error(errors, f"{label}_TYPE_INVALID")

    if obj.get("state") != expected_state:
        add_error(errors, f"{label}_STATE_MISMATCH")

    if obj.get("executionAuthorized") is not False:
        add_error(errors, f"{label}_EXECUTION_AUTHORIZED")

    if not valid_safety(obj):
        add_error(errors, f"{label}_SAFETY_VIOLATION")

    if not valid_policy(obj):
        add_error(errors, f"{label}_POLICY_VIOLATION")

    return obj


def validate_cross_layer(audit_obj, history_obj, history_verify_obj,
                         chain_audit_obj, chain_verify_obj, errors):

    if audit_obj is None or history_obj is None or \
       history_verify_obj is None or chain_audit_obj is None or \
       chain_verify_obj is None:
        add_error(errors, "CROSS_LAYER_SOURCES_INCOMPLETE")
        return

    audit_state = audit_obj.get("state")
    audit_source_state = audit_obj.get("sourceState")

    if history_obj.get("state") != audit_state:
        add_error(errors, "AUDIT_TO_HISTORY_STATE_MISMATCH")

    if history_obj.get("sourceState") != audit_source_state:
        add_error(errors, "AUDIT_TO_HISTORY_SOURCE_STATE_MISMATCH")

    if history_verify_obj.get("state") != history_obj.get("state"):
        add_error(errors, "HISTORY_TO_VERIFY_STATE_MISMATCH")

    if history_verify_obj.get("sourceState") != history_obj.get("sourceState"):
        add_error(errors, "HISTORY_TO_VERIFY_SOURCE_STATE_MISMATCH")

    if chain_audit_obj.get("state") != history_obj.get("state"):
        add_error(errors, "CHAIN_AUDIT_STATE_MISMATCH")

    if chain_verify_obj.get("state") != chain_audit_obj.get("state"):
        add_error(errors, "CHAIN_VERIFY_STATE_MISMATCH")


def build_report(errors, audit_obj=None):
    state = "INCOMPLETE"
    source_state = "INCOMPLETE"

    if isinstance(audit_obj, dict):
        state = audit_obj.get("state", "INCOMPLETE")
        source_state = audit_obj.get("sourceState", "INCOMPLETE")

    if errors:
        state = "BLOCKED"

    history_exists = safe_exists(HISTORY_FILE)
    verifier_exists = safe_exists(HISTORY_VERIFY_FILE)

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
            "auditExists": safe_exists(AUDIT_FILE),
            "historyExists": history_exists,
            "verifierExists": verifier_exists,
        },
        "sources": {
            "audit": {
                "file": AUDIT_FILE.name,
                "exists": safe_exists(AUDIT_FILE),
                "sha256": safe_sha(AUDIT_FILE),
            },
            "history": {
                "file": HISTORY_FILE.name,
                "exists": history_exists,
                "sha256": safe_sha(HISTORY_FILE),
            },
            "verifier": {
                "file": HISTORY_VERIFY_FILE.name,
                "exists": verifier_exists,
                "sha256": safe_sha(HISTORY_VERIFY_FILE),
            },
        },
        "errors": list(errors),
        "errorCount": len(errors),
        "policy": dict(POLICY),
    }

    return report


def main():
    ROOT.mkdir(parents=True, exist_ok=True)

    errors = []

    audit_obj, audit_err = load_json(AUDIT_FILE)

    if audit_err is not None:
        add_error(errors, "AUDIT_HISTORY_AUDIT_JSON_INVALID")
        audit_obj = None

    if audit_obj is not None:
        validate_root(audit_obj, errors)
        validate_audit_section(audit_obj, errors)
        validate_sources(audit_obj, errors)

    if not safe_exists(AUDIT_FILE):
        add_error(errors, "AUDIT_HISTORY_AUDIT_MISSING")

    history_obj = validate_upstream(
        HISTORY_FILE,
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY",
        audit_obj.get("state") if isinstance(audit_obj, dict)
        else "INCOMPLETE",
        errors,
        "HISTORY"
    ) if safe_exists(HISTORY_FILE) else None

    history_verify_obj = validate_upstream(
        HISTORY_VERIFY_FILE,
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_VERIFY",
        history_obj.get("state") if isinstance(history_obj, dict)
        else "INCOMPLETE",
        errors,
        "HISTORY_VERIFY"
    ) if safe_exists(HISTORY_VERIFY_FILE) else None

    chain_audit_obj = validate_upstream(
        CHAIN_AUDIT_FILE,
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT",
        history_obj.get("state") if isinstance(history_obj, dict)
        else "INCOMPLETE",
        errors,
        "CHAIN_AUDIT"
    ) if safe_exists(CHAIN_AUDIT_FILE) else None

    chain_verify_obj = validate_upstream(
        CHAIN_VERIFY_FILE,
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_VERIFY",
        chain_audit_obj.get("state") if isinstance(chain_audit_obj, dict)
        else "INCOMPLETE",
        errors,
        "CHAIN_VERIFY"
    ) if safe_exists(CHAIN_VERIFY_FILE) else None

    validate_cross_layer(
        audit_obj,
        history_obj,
        history_verify_obj,
        chain_audit_obj,
        chain_verify_obj,
        errors,
    )

    report = build_report(errors, audit_obj)

    OUTPUT_FILE.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT HISTORY AUDIT VERIFY v1.0")
    print("READ ONLY / FAIL CLOSED")
    print(f"STATE: {report['state']}")
    print(f"SOURCE STATE: {report['sourceState']}")
    print(f"VALID: {str(report['verification']['valid']).lower()}")
    print(f"ERRORS: {report['errorCount']}")
    print("EXECUTION AUTHORIZED: false")
    print(f"REPORT: {OUTPUT_FILE}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
