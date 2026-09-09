#!/usr/bin/env python3

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


VERSION = "1.0.0"
TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_FINAL_READINESS"

ROOT = Path(
    os.environ.get(
        "AACP_OUTPUT_DIR",
        "provider-output/aacp-observer",
    )
)

OUTPUT_FILE = (
    ROOT / "latest-aacp-evidence-chain-health-final-readiness.json"
)

LAYERS = {
    "phase31": {
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
        "file": ROOT / "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
    },
    "phase32": {
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
        "file": ROOT / "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
    },
    "phase33": {
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
        "file": ROOT / "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
    },
    "phase34": {
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION",
        "file": ROOT / "latest-aacp-evidence-chain-health-integrity-attestation.json",
    },
    "phase35": {
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_ATTESTATION_CONSISTENCY_VERIFY",
        "file": ROOT / "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
    },
}

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


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as fh:
            value = json.load(fh)

        if not isinstance(value, dict):
            return None

        return value
    except Exception:
        return None


def valid_safety(value):
    return value == SAFETY_FALSE


def valid_policy(value):
    return value == POLICY


def validate_common(name, report, errors):
    if not isinstance(report, dict):
        add_error(errors, f"{name.upper()}_INVALID", "Layer report is missing or invalid")
        return

    expected = LAYERS[name]["type"]

    if report.get("type") != expected:
        add_error(
            errors,
            f"{name.upper()}_TYPE",
            f"Unexpected type for {name}",
        )

    if report.get("version") != VERSION:
        add_error(
            errors,
            f"{name.upper()}_VERSION",
            f"Unexpected version for {name}",
        )

    if report.get("mode") != "READ_ONLY":
        add_error(
            errors,
            f"{name.upper()}_MODE",
            f"{name} is not READ_ONLY",
        )

    if report.get("executionAuthorized") is not False:
        add_error(
            errors,
            f"{name.upper()}_EXECUTION_AUTHORIZED",
            f"{name} executionAuthorized must be false",
        )

    if report.get("state") not in ALLOWED_STATES:
        add_error(
            errors,
            f"{name.upper()}_STATE",
            f"{name} has invalid state",
        )

    if report.get("sourceState") not in ALLOWED_STATES:
        add_error(
            errors,
            f"{name.upper()}_SOURCE_STATE",
            f"{name} has invalid sourceState",
        )

    if not valid_safety(report.get("safety")):
        add_error(
            errors,
            f"{name.upper()}_SAFETY",
            f"{name} safety policy violated",
        )

    if not valid_policy(report.get("policy")):
        add_error(
            errors,
            f"{name.upper()}_POLICY",
            f"{name} policy violated",
        )

    if not isinstance(report.get("errors"), list):
        add_error(
            errors,
            f"{name.upper()}_ERROR_MODEL",
            f"{name} errors must be a list",
        )
    elif report.get("errorCount") != len(report["errors"]):
        add_error(
            errors,
            f"{name.upper()}_ERROR_COUNT",
            f"{name} errorCount mismatch",
        )


def validate_layer_semantics(name, report, errors):
    if not isinstance(report, dict):
        return

    # Phase 31 uses a consistency-based schema rather than a
    # verification object. INCOMPLETE is legitimate here as long
    # as both snapshots exist and their state metadata agrees.
    if name == "phase31":
        consistency = report.get("consistency")

        if not isinstance(consistency, dict):
            add_error(
                errors,
                "PHASE31_CONSISTENCY",
                "phase31 consistency object missing",
            )
            return

        required_true = (
            "auditExists",
            "verifyExists",
            "stateMatch",
            "sourceStateMatch",
        )

        for key in required_true:
            if consistency.get(key) is not True:
                add_error(
                    errors,
                    f"PHASE31_{key.upper()}",
                    f"phase31 consistency.{key} must be true",
                )

        if report.get("errorCount") != 0:
            add_error(
                errors,
                "PHASE31_ERRORS",
                "phase31 errorCount must be zero",
            )

        return

    verification = report.get("verification")

    if not isinstance(verification, dict):
        add_error(
            errors,
            f"{name.upper()}_VERIFICATION",
            f"{name} verification object missing",
        )
        return

    if verification.get("valid") is not True:
        add_error(
            errors,
            f"{name.upper()}_NOT_VALID",
            f"{name} verification is not valid",
        )

    if name == "phase35":
        if verification.get("sourceExists") is not True:
            add_error(
                errors,
                "PHASE35_SOURCE_MISSING",
                "Phase 35 source does not exist",
            )

        source_sha = verification.get("sourceSha256")
        if not isinstance(source_sha, str) or len(source_sha) != 64:
            add_error(
                errors,
                "PHASE35_SOURCE_SHA",
                "Phase 35 source SHA-256 is invalid",
            )


def validate_state_chain(reports, errors):
    for name, report in reports.items():
        if not isinstance(report, dict):
            continue

        if report.get("state") == "BLOCKED":
            add_error(
                errors,
                f"{name.upper()}_BLOCKED",
                f"{name} is BLOCKED",
            )

        if report.get("sourceState") == "BLOCKED":
            add_error(
                errors,
                f"{name.upper()}_SOURCE_BLOCKED",
                f"{name} sourceState is BLOCKED",
            )


def validate_hash_chain(reports, errors):
    p31 = reports.get("phase31")
    p32 = reports.get("phase32")
    p33 = reports.get("phase33")
    p34 = reports.get("phase34")
    p35 = reports.get("phase35")

    if not all(isinstance(x, dict) for x in (p31, p32, p33, p34, p35)):
        return

    sha31 = sha256_file(LAYERS["phase31"]["file"])
    sha32 = sha256_file(LAYERS["phase32"]["file"])
    sha33 = sha256_file(LAYERS["phase33"]["file"])
    sha34 = sha256_file(LAYERS["phase34"]["file"])

    v32 = p32.get("verification", {})
    v33 = p33.get("verification", {})
    v34 = p34.get("verification", {})
    v35 = p35.get("verification", {})

    if isinstance(v32, dict):
        if v32.get("sha256") != sha31:
            add_error(
                errors,
                "PHASE32_CHAIN_SHA",
                "Phase 32 does not reference the current Phase 31 SHA-256",
            )

    if isinstance(v33, dict):
        if v33.get("phase31Sha256") != sha31:
            add_error(
                errors,
                "PHASE33_PHASE31_SHA",
                "Phase 33 does not reference the current Phase 31 SHA-256",
            )

        if v33.get("phase32Sha256") != sha32:
            add_error(
                errors,
                "PHASE33_PHASE32_SHA",
                "Phase 33 does not reference the current Phase 32 SHA-256",
            )

    if isinstance(v34, dict):
        if v34.get("phase31Sha256") != sha31:
            add_error(
                errors,
                "PHASE34_PHASE31_SHA",
                "Phase 34 does not reference the current Phase 31 SHA-256",
            )

        if v34.get("phase32Sha256") != sha32:
            add_error(
                errors,
                "PHASE34_PHASE32_SHA",
                "Phase 34 does not reference the current Phase 32 SHA-256",
            )

        if v34.get("phase33Sha256") != sha33:
            add_error(
                errors,
                "PHASE34_PHASE33_SHA",
                "Phase 34 does not reference the current Phase 33 SHA-256",
            )

    if isinstance(v35, dict):
        if v35.get("sourceSha256") != sha34:
            add_error(
                errors,
                "PHASE35_PHASE34_SHA",
                "Phase 35 does not reference the current Phase 34 SHA-256",
            )


def validate_no_full_report_copy(report, errors):
    if not isinstance(report, dict):
        return

    def walk(value, path=""):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in FORBIDDEN_COPY_KEYS:
                    add_error(
                        errors,
                        "FULL_REPORT_COPY",
                        f"Forbidden full-report field at {path}/{key}",
                    )
                walk(child, f"{path}/{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}/{index}")

    walk(report)


def build_report(reports, errors):
    valid = len(errors) == 0

    layer_states = {}

    for name, report in reports.items():
        if isinstance(report, dict):
            layer_states[name] = report.get("state")
        else:
            layer_states[name] = "BLOCKED"

    state = "VERIFIED_READ_ONLY" if valid else "BLOCKED"
    source_state = "VERIFIED_READ_ONLY" if valid else "BLOCKED"

    return {
        "version": VERSION,
        "type": TYPE,
        "generatedAt": now_iso(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": SAFETY_FALSE.copy(),
        "sideEffects": {
            "network": False,
            "filesystemWrite": True,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "readiness": {
            "ready": valid,
            "reason": (
                "ALL_REQUIRED_LAYERS_VERIFIED"
                if valid
                else "REQUIRED_LAYER_VERIFICATION_FAILED"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 5,
            "verifiedLayers": sum(
                1
                for name, report in reports.items()
                if isinstance(report, dict)
                and (
                    (
                        name == "phase31"
                        and isinstance(report.get("consistency"), dict)
                        and report["consistency"].get("auditExists") is True
                        and report["consistency"].get("verifyExists") is True
                        and report["consistency"].get("stateMatch") is True
                        and report["consistency"].get("sourceStateMatch") is True
                        and report.get("errorCount") == 0
                    )
                    or (
                        name != "phase31"
                        and isinstance(report.get("verification"), dict)
                        and report["verification"].get("valid") is True
                    )
                )
            ),
            "layers": layer_states,
        },
        "sources": {
            name: {
                "file": str(spec["file"]),
                "exists": safe_exists(spec["file"]),
                "sha256": sha256_file(spec["file"]),
                "type": spec["type"],
            }
            for name, spec in LAYERS.items()
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": POLICY.copy(),
    }


def main():
    errors = []
    reports = {}

    ROOT.mkdir(parents=True, exist_ok=True)

    for name, spec in LAYERS.items():
        path = spec["file"]

        if not safe_exists(path):
            reports[name] = None
            add_error(
                errors,
                f"{name.upper()}_MISSING",
                f"{name} report is missing",
            )
            continue

        report = load_json(path)
        reports[name] = report

        if report is None:
            add_error(
                errors,
                f"{name.upper()}_INVALID_JSON",
                f"{name} report is invalid JSON",
            )

    for name, report in reports.items():
        validate_common(name, report, errors)
        validate_layer_semantics(name, report, errors)
        validate_no_full_report_copy(report, errors)

    validate_state_chain(reports, errors)
    validate_hash_chain(reports, errors)

    report = build_report(reports, errors)

    try:
        OUTPUT_FILE.write_text(
            json.dumps(
                report,
                indent=2,
                sort_keys=False,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"OUTPUT_WRITE_FAILED: {exc}", file=sys.stderr)
        return 2

    print(f"STATE: {report['state']}")
    print(f"SOURCE STATE: {report['sourceState']}")
    print(f"READY: {report['readiness']['ready']}")
    print(f"VALID: {report['verification']['valid']}")
    print(f"VERIFIED LAYERS: {report['verification']['verifiedLayers']}/5")
    print(f"ERROR COUNT: {report['errorCount']}")

    return 0 if report["verification"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
