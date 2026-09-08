#!/usr/bin/env python3
"""
TERMiX AACP Evidence Chain Health Audit History Auditor v1.0

READ ONLY / FAIL CLOSED

Audits:
  Phase 27:
    latest-aacp-evidence-chain-health-audit-history.json

  Phase 28:
    latest-aacp-evidence-chain-health-audit-history-verify.json

  Upstream:
    Phase 25:
      latest-aacp-evidence-chain-health-audit.json
    Phase 26:
      latest-aacp-evidence-chain-health-audit-verify.json

This module NEVER performs:
  - POST
  - wallet access
  - private-key access
  - signing
  - broadcast
  - submission
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(
    os.environ.get(
        "AACP_OUTPUT_DIR",
        "provider-output/aacp-observer",
    )
)

HISTORY_FILE = ROOT / "latest-aacp-evidence-chain-health-audit-history.json"
VERIFIER_FILE = ROOT / "latest-aacp-evidence-chain-health-audit-history-verify.json"

AUDIT_FILE = ROOT / "latest-aacp-evidence-chain-health-audit.json"
AUDIT_VERIFY_FILE = ROOT / "latest-aacp-evidence-chain-health-audit-verify.json"

OUTPUT_FILE = ROOT / "latest-aacp-evidence-chain-health-audit-history-audit.json"

ALLOWED_STATES = {
    "INCOMPLETE",
    "BLOCKED",
    "VERIFIED_READ_ONLY",
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

FALSE_SAFETY = {
    "postPerformed": False,
    "walletUsed": False,
    "signingPerformed": False,
    "broadcastPerformed": False,
    "submissionPerformed": False,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def exists(path: Path) -> bool:
    try:
        return path.is_file()
    except Exception:
        return False


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
        if not isinstance(value, dict):
            return None, "JSON_ROOT_NOT_OBJECT"
        return value, None
    except FileNotFoundError:
        return None, "FILE_MISSING"
    except json.JSONDecodeError:
        return None, "INVALID_JSON"
    except Exception as exc:
        return None, f"READ_ERROR:{type(exc).__name__}"


def source_meta(path: Path) -> dict[str, Any]:
    return {
        "file": path.name,
        "exists": exists(path),
        "sha256": sha256_file(path),
    }


def add_error(errors: list[str], code: str) -> None:
    if code not in errors:
        errors.append(code)


def valid_safety(obj: Any) -> bool:
    return isinstance(obj, dict) and obj == FALSE_SAFETY


def valid_policy(obj: Any) -> bool:
    return isinstance(obj, dict) and obj == POLICY


def valid_root_common(
    obj: dict[str, Any],
    expected_type: str,
) -> list[str]:
    errors: list[str] = []

    if obj.get("version") != "1.0.0":
        add_error(errors, "ROOT_VERSION_INVALID")

    if obj.get("type") != expected_type:
        add_error(errors, "ROOT_TYPE_INVALID")

    if obj.get("mode") != "READ_ONLY":
        add_error(errors, "ROOT_MODE_INVALID")

    if obj.get("state") not in ALLOWED_STATES:
        add_error(errors, "ROOT_STATE_INVALID")

    if obj.get("sourceState") not in ALLOWED_STATES:
        add_error(errors, "ROOT_SOURCE_STATE_INVALID")

    if obj.get("executionAuthorized") is not False:
        add_error(errors, "EXECUTION_AUTHORIZED_VIOLATION")

    if not valid_safety(obj.get("safety")):
        add_error(errors, "SAFETY_VIOLATION")

    if not valid_safety(obj.get("sideEffects")):
        add_error(errors, "SIDE_EFFECTS_VIOLATION")

    if not valid_policy(obj.get("policy")):
        add_error(errors, "POLICY_VIOLATION")

    return errors


def audit_history_structure(
    history: dict[str, Any],
    errors: list[str],
) -> None:
    errors.extend(
        x for x in valid_root_common(
            history,
            "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY",
        )
        if x not in errors
    )

    snapshots = history.get("snapshots")
    consistency = history.get("consistency")

    if not isinstance(snapshots, dict):
        add_error(errors, "HISTORY_SNAPSHOTS_INVALID")
        return

    for name in ("audit", "verify"):
        snap = snapshots.get(name)
        if not isinstance(snap, dict):
            add_error(errors, f"HISTORY_SNAPSHOT_{name.upper()}_INVALID")
            continue

        required = {
            "file",
            "exists",
            "sha256",
            "state",
            "sourceState",
            "errorCount",
        }

        validity_field = (
            "auditValid"
            if name == "audit"
            else "verificationValid"
        )

        if validity_field not in snap:
            add_error(
                errors,
                f"HISTORY_SNAPSHOT_{name.upper()}_FIELDS_MISSING",
            )

        missing = required - set(snap.keys())
        if missing:
            add_error(
                errors,
                f"HISTORY_SNAPSHOT_{name.upper()}_FIELDS_MISSING",
            )

        if snap.get("state") not in ALLOWED_STATES:
            add_error(
                errors,
                f"HISTORY_SNAPSHOT_{name.upper()}_STATE_INVALID",
            )

        if snap.get("sourceState") not in ALLOWED_STATES:
            add_error(
                errors,
                f"HISTORY_SNAPSHOT_{name.upper()}_SOURCE_STATE_INVALID",
            )

        if not isinstance(snap.get("exists"), bool):
            add_error(
                errors,
                f"HISTORY_SNAPSHOT_{name.upper()}_EXISTS_INVALID",
            )

        if snap.get(validity_field) is not True:
            add_error(
                errors,
                f"HISTORY_SNAPSHOT_{name.upper()}_VALID_FALSE",
            )

        if not isinstance(snap.get("errorCount"), int):
            add_error(
                errors,
                f"HISTORY_SNAPSHOT_{name.upper()}_ERROR_COUNT_INVALID",
            )

    if not isinstance(consistency, dict):
        add_error(errors, "HISTORY_CONSISTENCY_INVALID")


def verify_history_upstreams(
    history: dict[str, Any],
    errors: list[str],
) -> None:
    snapshots = history.get("snapshots")
    if not isinstance(snapshots, dict):
        return

    mappings = {
        "audit": AUDIT_FILE,
        "verify": AUDIT_VERIFY_FILE,
    }

    for key, actual_path in mappings.items():
        snap = snapshots.get(key)
        if not isinstance(snap, dict):
            continue

        actual_exists = exists(actual_path)
        claimed_exists = snap.get("exists")

        if claimed_exists != actual_exists:
            add_error(
                errors,
                f"HISTORY_{key.upper()}_EXISTS_MISMATCH",
            )

        claimed_sha = snap.get("sha256")
        actual_sha = sha256_file(actual_path)

        if actual_exists and claimed_sha != actual_sha:
            add_error(
                errors,
                f"HISTORY_{key.upper()}_SHA256_MISMATCH",
            )

        actual_obj, read_error = read_json(actual_path)

        if actual_exists and read_error:
            add_error(
                errors,
                f"HISTORY_{key.upper()}_SOURCE_{read_error}",
            )
            continue

        if actual_obj is None:
            continue

        if snap.get("state") != actual_obj.get("state"):
            add_error(
                errors,
                f"HISTORY_{key.upper()}_STATE_LINK_MISMATCH",
            )

        if snap.get("sourceState") != actual_obj.get("sourceState"):
            add_error(
                errors,
                f"HISTORY_{key.upper()}_SOURCE_STATE_LINK_MISMATCH",
            )

        validity_field = (
            "auditValid"
            if key == "audit"
            else "verificationValid"
        )

        if snap.get(validity_field) is True:
            if actual_obj.get("errorCount") not in (0, None):
                add_error(
                    errors,
                    f"HISTORY_{key.upper()}_ERROR_COUNT_MISMATCH",
                )


def verify_history_consistency(
    history: dict[str, Any],
    errors: list[str],
) -> None:
    snapshots = history.get("snapshots")
    consistency = history.get("consistency")

    if not isinstance(snapshots, dict):
        return
    if not isinstance(consistency, dict):
        return

    audit = snapshots.get("audit", {})
    verify = snapshots.get("verify", {})

    expected = {
        "auditExists": audit.get("exists") is True,
        "verifyExists": verify.get("exists") is True,
        "stateMatch": audit.get("state") == verify.get("state"),
        "sourceStateMatch": (
            audit.get("sourceState") == verify.get("sourceState")
        ),
    }

    for key, value in expected.items():
        if consistency.get(key) is not value:
            add_error(
                errors,
                f"HISTORY_CONSISTENCY_{key.upper()}_VIOLATION",
            )

    if history.get("state") != audit.get("state"):
        add_error(errors, "HISTORY_ROOT_AUDIT_STATE_MISMATCH")

    if history.get("state") != verify.get("state"):
        add_error(errors, "HISTORY_ROOT_VERIFY_STATE_MISMATCH")

    if history.get("sourceState") != audit.get("sourceState"):
        add_error(errors, "HISTORY_ROOT_AUDIT_SOURCE_STATE_MISMATCH")

    if history.get("sourceState") != verify.get("sourceState"):
        add_error(errors, "HISTORY_ROOT_VERIFY_SOURCE_STATE_MISMATCH")


def verify_verifier_structure(
    verifier: dict[str, Any],
    errors: list[str],
) -> None:
    errors.extend(
        x for x in valid_root_common(
            verifier,
            "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_VERIFY",
        )
        if x not in errors
    )

    verification = verifier.get("verification")
    sources = verifier.get("sources")

    if not isinstance(verification, dict):
        add_error(errors, "VERIFIER_VERIFICATION_INVALID")
    else:
        for key in ("valid", "historyExists", "auditExists", "verifyExists"):
            if not isinstance(verification.get(key), bool):
                add_error(
                    errors,
                    f"VERIFIER_{key.upper()}_INVALID",
                )

        if verification.get("valid") is not True:
            add_error(errors, "VERIFIER_VALID_FALSE")

    if not isinstance(sources, dict):
        add_error(errors, "VERIFIER_SOURCES_INVALID")
        return

    for key in ("history", "audit", "verify"):
        item = sources.get(key)
        if not isinstance(item, dict):
            add_error(
                errors,
                f"VERIFIER_SOURCE_{key.upper()}_INVALID",
            )
            continue

        if "file" not in item:
            add_error(
                errors,
                f"VERIFIER_SOURCE_{key.upper()}_FILE_MISSING",
            )

        if "exists" not in item:
            add_error(
                errors,
                f"VERIFIER_SOURCE_{key.upper()}_EXISTS_MISSING",
            )

        if "sha256" not in item:
            add_error(
                errors,
                f"VERIFIER_SOURCE_{key.upper()}_SHA_MISSING",
            )


def verify_verifier_sources(
    verifier: dict[str, Any],
    errors: list[str],
) -> None:
    sources = verifier.get("sources")
    if not isinstance(sources, dict):
        return

    mappings = {
        "history": HISTORY_FILE,
        "audit": AUDIT_FILE,
        "verify": AUDIT_VERIFY_FILE,
    }

    for key, actual_path in mappings.items():
        claim = sources.get(key)
        if not isinstance(claim, dict):
            continue

        actual_exists = exists(actual_path)

        if claim.get("exists") != actual_exists:
            add_error(
                errors,
                f"VERIFIER_SOURCE_{key.upper()}_EXISTS_MISMATCH",
            )

        actual_sha = sha256_file(actual_path)

        if actual_exists and claim.get("sha256") != actual_sha:
            add_error(
                errors,
                f"VERIFIER_SOURCE_{key.upper()}_SHA256_MISMATCH",
            )

        if actual_exists and claim.get("file") != actual_path.name:
            add_error(
                errors,
                f"VERIFIER_SOURCE_{key.upper()}_FILE_MISMATCH",
            )


def verify_verifier_cross_layer(
    history: dict[str, Any],
    verifier: dict[str, Any],
    errors: list[str],
) -> None:
    if verifier.get("state") != history.get("state"):
        add_error(errors, "VERIFIER_HISTORY_STATE_MISMATCH")

    if verifier.get("sourceState") != history.get("sourceState"):
        add_error(errors, "VERIFIER_HISTORY_SOURCE_STATE_MISMATCH")

    verification = verifier.get("verification")
    if not isinstance(verification, dict):
        return

    if verification.get("historyExists") is not True:
        add_error(errors, "VERIFIER_HISTORY_EXISTS_FALSE")

    if verification.get("auditExists") is not True:
        add_error(errors, "VERIFIER_AUDIT_EXISTS_FALSE")

    if verification.get("verifyExists") is not True:
        add_error(errors, "VERIFIER_VERIFY_EXISTS_FALSE")

    if verification.get("valid") is not True:
        add_error(errors, "VERIFIER_CROSS_LAYER_INVALID")


def determine_state(
    history: dict[str, Any] | None,
    verifier: dict[str, Any] | None,
    errors: list[str],
) -> str:
    if errors:
        return "BLOCKED"

    if history is None or verifier is None:
        return "BLOCKED"

    if history.get("state") == "VERIFIED_READ_ONLY":
        return "VERIFIED_READ_ONLY"

    return "INCOMPLETE"


def build_report() -> tuple[dict[str, Any], int]:
    errors: list[str] = []

    history, history_error = read_json(HISTORY_FILE)
    verifier, verifier_error = read_json(VERIFIER_FILE)

    if history_error == "FILE_MISSING":
        add_error(errors, "HISTORY_MISSING")
    elif history_error:
        add_error(errors, f"HISTORY_{history_error}")

    if verifier_error == "FILE_MISSING":
        add_error(errors, "VERIFIER_MISSING")
    elif verifier_error:
        add_error(errors, f"VERIFIER_{verifier_error}")

    if history is not None:
        audit_history_structure(history, errors)
        verify_history_upstreams(history, errors)
        verify_history_consistency(history, errors)

    if verifier is not None:
        verify_verifier_structure(verifier, errors)
        verify_verifier_sources(verifier, errors)

    if history is not None and verifier is not None:
        verify_verifier_cross_layer(history, verifier, errors)

    state = determine_state(history, verifier, errors)

    source_state = (
        history.get("sourceState")
        if isinstance(history, dict)
        else "INCOMPLETE"
    )

    valid = len(errors) == 0

    findings: list[str] = []

    if not valid:
        findings.append("AUDIT_FAILED")
    elif state == "INCOMPLETE":
        findings.append("CHAIN_INCOMPLETE")
    else:
        findings.append("CHAIN_VERIFIED")

    report = {
        "version": "1.0.0",
        "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT",
        "generatedAt": now_iso(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": dict(FALSE_SAFETY),
        "sideEffects": dict(FALSE_SAFETY),
        "audit": {
            "valid": valid,
            "historyExists": exists(HISTORY_FILE),
            "verifierExists": exists(VERIFIER_FILE),
            "crossLayerValid": (
                valid
                and history is not None
                and verifier is not None
            ),
        },
        "sources": {
            "history": source_meta(HISTORY_FILE),
            "verifier": source_meta(VERIFIER_FILE),
        },
        "findings": findings,
        "errors": errors,
        "errorCount": len(errors),
        "policy": dict(POLICY),
    }

    return report, (1 if errors else 0)


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)

    try:
        report, code = build_report()

        temp = OUTPUT_FILE.with_suffix(".json.tmp")

        with temp.open("w", encoding="utf-8") as f:
            json.dump(
                report,
                f,
                indent=2,
                ensure_ascii=False,
            )
            f.write("\n")

        temp.replace(OUTPUT_FILE)

        print(
            "TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT "
            "HISTORY AUDITOR v1.0"
        )
        print("READ ONLY / FAIL CLOSED")
        print(f"STATE: {report['state']}")
        print(f"SOURCE STATE: {report['sourceState']}")
        print(f"VALID: {str(report['audit']['valid']).lower()}")
        print(f"FINDINGS: {len(report['findings'])}")
        print(f"ERRORS: {report['errorCount']}")
        print(
            "EXECUTION AUTHORIZED: "
            f"{str(report['executionAuthorized']).lower()}"
        )
        print(f"REPORT: {OUTPUT_FILE}")

        return code

    except Exception as exc:
        # Last-resort fail-closed report.
        fallback = {
            "version": "1.0.0",
            "type": "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT",
            "generatedAt": now_iso(),
            "mode": "READ_ONLY",
            "state": "BLOCKED",
            "sourceState": "INCOMPLETE",
            "executionAuthorized": False,
            "safety": dict(FALSE_SAFETY),
            "sideEffects": dict(FALSE_SAFETY),
            "audit": {
                "valid": False,
                "historyExists": exists(HISTORY_FILE),
                "verifierExists": exists(VERIFIER_FILE),
                "crossLayerValid": False,
            },
            "sources": {
                "history": source_meta(HISTORY_FILE),
                "verifier": source_meta(VERIFIER_FILE),
            },
            "findings": ["AUDITOR_INTERNAL_ERROR"],
            "errors": [f"INTERNAL_ERROR:{type(exc).__name__}"],
            "errorCount": 1,
            "policy": dict(POLICY),
        }

        try:
            with OUTPUT_FILE.open("w", encoding="utf-8") as f:
                json.dump(
                    fallback,
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
                f.write("\n")
        except Exception:
            pass

        print(
            "TERMiX AACP EVIDENCE CHAIN HEALTH AUDIT "
            "HISTORY AUDITOR v1.0"
        )
        print("READ ONLY / FAIL CLOSED")
        print("STATE: BLOCKED")
        print("SOURCE STATE: INCOMPLETE")
        print("VALID: false")
        print("FINDINGS: 1")
        print("ERRORS: 1")
        print("EXECUTION AUTHORIZED: false")
        print(f"REPORT: {OUTPUT_FILE}")

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
