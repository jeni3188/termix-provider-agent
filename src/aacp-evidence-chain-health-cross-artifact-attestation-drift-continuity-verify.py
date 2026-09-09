#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("provider-output/aacp-observer")

PHASE47 = BASE / "latest-aacp-evidence-chain-health-cross-artifact-attestation-drift-verify.json"

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-cross-artifact-attestation-drift-continuity-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-cross-artifact-attestation-drift-continuity-verify.json"
)

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_DRIFT_CONTINUITY_VERIFY"
PHASE47_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_DRIFT_VERIFY"

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        raise ValueError(f"invalid JSON: {path}: {exc}")


def digest(value):
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def safety_ok(obj):
    safety = obj.get("safety")
    if not isinstance(safety, dict):
        return False

    # Fail closed only when an explicitly declared safety flag is True.
    # Phase47 may expose a compatible safety schema with additional fields.
    return not any(
        isinstance(value, bool) and value is True
        for value in safety.values()
    )


def phase47_projection(phase47):
    verification = phase47.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("phase47 verification missing")

    return {
        "version": phase47.get("version"),
        "type": phase47.get("type"),
        "mode": phase47.get("mode"),
        "state": phase47.get("state"),
        "sourceState": phase47.get("sourceState"),
        "executionAuthorized": phase47.get("executionAuthorized"),
        "safety": phase47.get("safety"),
        "sideEffects": phase47.get("sideEffects"),
        "verification": verification,
        "sources": phase47.get("sources"),
        "errors": phase47.get("errors"),
        "errorCount": phase47.get("errorCount"),
        "policy": phase47.get("policy"),
    }


def validate_phase47(phase47):
    if phase47.get("type") != PHASE47_TYPE:
        raise ValueError("phase47 type mismatch")

    if phase47.get("mode") != "READ_ONLY":
        raise ValueError("phase47 mode violation")

    if phase47.get("executionAuthorized") is not False:
        raise ValueError("phase47 execution authorization violation")

    if not safety_ok(phase47):
        raise ValueError("phase47 safety violation")

    if phase47.get("errorCount") != 0:
        raise ValueError("phase47 errorCount violation")

    if phase47.get("errors") != []:
        raise ValueError("phase47 errors violation")

    if phase47.get("state") != "VERIFIED_READ_ONLY":
        raise ValueError("phase47 state violation")

    if phase47.get("sourceState") != "VERIFIED_READ_ONLY":
        raise ValueError("phase47 source state violation")

    readiness = phase47.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("ready") is not True:
        raise ValueError("phase47 readiness violation")

    verification = phase47.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("phase47 verification missing")

    if verification.get("valid") is not True:
        raise ValueError("phase47 validity violation")

    if verification.get("requiredLayers") != 14:
        raise ValueError("phase47 requiredLayers violation")

    if verification.get("verifiedLayers") != 14:
        raise ValueError("phase47 verifiedLayers violation")

    if verification.get("checkpoint") != "VERIFIED":
        raise ValueError("phase47 checkpoint violation")

    drift = verification.get("driftDigest")
    if not isinstance(drift, str) or not HEX64.fullmatch(drift):
        raise ValueError("phase47 driftDigest invalid")


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint_state,
    verified_layers,
    continuity_digest,
    errors,
):
    return {
        "version": 1,
        "type": TYPE,
        "generatedAt": now(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": {
            "postPerformed": False,
            "walletUsed": False,
            "signingPerformed": False,
            "broadcastPerformed": False,
            "submissionPerformed": False,
        },
        "sideEffects": {
            "filesystemRead": True,
            "filesystemWrite": True,
            "networkAccess": False,
            "walletAccess": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "readiness": {
            "ready": ready,
            "reason": (
                "ALL_REQUIRED_DRIFT_CONTINUITY_VERIFIED"
                if ready
                else "CHECKPOINT_ESTABLISHED"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 14,
            "verifiedLayers": verified_layers,
            "checkpoint": checkpoint_state,
            "continuityDigest": continuity_digest,
        },
        "sources": {
            "phase47": str(PHASE47),
            "checkpoint": str(CHECKPOINT),
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "readOnly": True,
            "failClosed": True,
            "networkAllowed": False,
            "walletAllowed": False,
            "signingAllowed": False,
            "broadcastAllowed": False,
            "submissionAllowed": False,
        },
    }


def main():
    errors = []

    try:
        if not PHASE47.exists():
            raise ValueError("phase47 artifact missing")

        phase47 = load_json(PHASE47)
        validate_phase47(phase47)

        verification = phase47["verification"]

        projection = {
            "version": phase47.get("version"),
            "type": PHASE47_TYPE,
            "mode": phase47.get("mode"),
            "driftDigest": verification.get("driftDigest"),
            "requiredLayers": verification.get("requiredLayers"),
            "verifiedLayers": verification.get("verifiedLayers"),
        }

        continuity_digest = digest(projection)

        if not CHECKPOINT.exists():
            checkpoint = {
                "version": 1,
                "type": TYPE,
                "createdAt": now(),
                "continuityDigest": continuity_digest,
                "continuityProjection": projection,
            }

            OUTPUT.write_text(
                json.dumps(
                    build_output(
                        "CHECKPOINT_ESTABLISHED",
                        "CHECKPOINT_ESTABLISHED",
                        False,
                        True,
                        "ESTABLISHED",
                        0,
                        continuity_digest,
                        [],
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )

            CHECKPOINT.write_text(
                json.dumps(checkpoint, indent=2, sort_keys=True)
            )

            print("STATE: CHECKPOINT_ESTABLISHED")
            print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
            print("READY: False")
            print("VALID: True")
            print("CHECKPOINT: ESTABLISHED")
            print("VERIFIED LAYERS: 0/14")
            print(f"CONTINUITY DIGEST: {continuity_digest}")
            print("ERROR COUNT: 0")
            return 0

        checkpoint = load_json(CHECKPOINT)

        if checkpoint.get("type") != TYPE:
            raise ValueError("checkpoint type mismatch")

        if checkpoint.get("continuityDigest") != continuity_digest:
            raise ValueError("checkpoint: continuity drift detected")

        if checkpoint.get("continuityProjection") != projection:
            raise ValueError("checkpoint: projection drift detected")

        OUTPUT.write_text(
            json.dumps(
                build_output(
                    "VERIFIED_READ_ONLY",
                    "VERIFIED_READ_ONLY",
                    True,
                    True,
                    "VERIFIED",
                    14,
                    continuity_digest,
                    [],
                ),
                indent=2,
                sort_keys=True,
            )
        )

        print("STATE: VERIFIED_READ_ONLY")
        print("SOURCE STATE: VERIFIED_READ_ONLY")
        print("READY: True")
        print("VALID: True")
        print("CHECKPOINT: VERIFIED")
        print("VERIFIED LAYERS: 14/14")
        print(f"CONTINUITY DIGEST: {continuity_digest}")
        print("ERROR COUNT: 0")
        return 0

    except Exception as exc:
        errors.append(str(exc))

        OUTPUT.write_text(
            json.dumps(
                build_output(
                    "BLOCKED",
                    "BLOCKED",
                    False,
                    False,
                    "BLOCKED",
                    0,
                    "",
                    errors,
                ),
                indent=2,
                sort_keys=True,
            )
        )

        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: BLOCKED")
        print("VERIFIED LAYERS: 0/14")
        print("CONTINUITY DIGEST:")
        print(f"ERROR COUNT: {len(errors)}")
        for error in errors:
            print(f"ERROR: {error}")

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
