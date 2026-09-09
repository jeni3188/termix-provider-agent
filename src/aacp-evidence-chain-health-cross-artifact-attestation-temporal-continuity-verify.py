#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("provider-output/aacp-observer")

PHASE45 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-identity-attestation.json"
)

PHASE46 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-consistency-verify.json"
)

PHASE47 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-drift-verify.json"
)

PHASE48 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-drift-continuity-verify.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-"
    "cross-artifact-attestation-temporal-continuity-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-temporal-continuity-verify.json"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_"
    "CROSS_ARTIFACT_ATTESTATION_TEMPORAL_CONTINUITY_VERIFY"
)

EXPECTED = {
    45: "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_IDENTITY_ATTESTATION",
    46: "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_CONSISTENCY_VERIFY",
    47: "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_DRIFT_VERIFY",
    48: "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_DRIFT_CONTINUITY_VERIFY",
}

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        raise ValueError(f"invalid JSON: {path}: {exc}")


def parse_timestamp(value, label):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} generatedAt missing")

    try:
        parsed = datetime.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"{label} generatedAt malformed: {exc}")

    if parsed.tzinfo is None:
        raise ValueError(f"{label} generatedAt timezone missing")

    return parsed.astimezone(timezone.utc)


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

    return not any(
        isinstance(value, bool) and value is True
        for value in safety.values()
    )


def validate_common(obj, phase, expected_type):
    if obj.get("type") != expected_type:
        raise ValueError(f"phase{phase} type mismatch")

    if obj.get("mode") != "READ_ONLY":
        raise ValueError(f"phase{phase} mode violation")

    if obj.get("executionAuthorized") is not False:
        raise ValueError(f"phase{phase} execution authorization violation")

    if not safety_ok(obj):
        raise ValueError(f"phase{phase} safety violation")

    if obj.get("errorCount") != 0:
        raise ValueError(f"phase{phase} errorCount violation")

    if obj.get("errors") != []:
        raise ValueError(f"phase{phase} errors violation")


def validate_phase45(obj):
    validate_common(obj, 45, EXPECTED[45])

    if obj.get("state") != "VERIFIED_READ_ONLY":
        raise ValueError("phase45 state violation")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        raise ValueError("phase45 source state violation")

    readiness = obj.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("ready") is not True:
        raise ValueError("phase45 readiness violation")

    verification = obj.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("phase45 verification missing")

    if verification.get("valid") is not True:
        raise ValueError("phase45 validity violation")

    if verification.get("requiredLayers") != 14:
        raise ValueError("phase45 requiredLayers violation")

    if verification.get("verifiedLayers") != 14:
        raise ValueError("phase45 verifiedLayers violation")

    if verification.get("checkpoint") != "VERIFIED":
        raise ValueError("phase45 checkpoint violation")

    digest_value = verification.get("attestationDigest")
    if not isinstance(digest_value, str) or not HEX64.fullmatch(digest_value):
        raise ValueError("phase45 attestationDigest invalid")


def validate_phase46(obj):
    validate_common(obj, 46, EXPECTED[46])

    if obj.get("state") != "VERIFIED_READ_ONLY":
        raise ValueError("phase46 state violation")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        raise ValueError("phase46 source state violation")

    readiness = obj.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("ready") is not True:
        raise ValueError("phase46 readiness violation")

    verification = obj.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("phase46 verification missing")

    if verification.get("valid") is not True:
        raise ValueError("phase46 validity violation")

    if verification.get("requiredLayers") != 14:
        raise ValueError("phase46 requiredLayers violation")

    if verification.get("verifiedLayers") != 14:
        raise ValueError("phase46 verifiedLayers violation")

    if verification.get("checkpoint") != "VERIFIED":
        raise ValueError("phase46 checkpoint violation")

    digest_value = verification.get("consistencyDigest")
    if not isinstance(digest_value, str) or not HEX64.fullmatch(digest_value):
        raise ValueError("phase46 consistencyDigest invalid")


def validate_phase47(obj):
    validate_common(obj, 47, EXPECTED[47])

    if obj.get("state") != "VERIFIED_READ_ONLY":
        raise ValueError("phase47 state violation")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        raise ValueError("phase47 source state violation")

    readiness = obj.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("ready") is not True:
        raise ValueError("phase47 readiness violation")

    verification = obj.get("verification")
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

    digest_value = verification.get("driftDigest")
    if not isinstance(digest_value, str) or not HEX64.fullmatch(digest_value):
        raise ValueError("phase47 driftDigest invalid")


def validate_phase48(obj):
    validate_common(obj, 48, EXPECTED[48])

    if obj.get("state") != "VERIFIED_READ_ONLY":
        raise ValueError("phase48 state violation")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        raise ValueError("phase48 source state violation")

    readiness = obj.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("ready") is not True:
        raise ValueError("phase48 readiness violation")

    verification = obj.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("phase48 verification missing")

    if verification.get("valid") is not True:
        raise ValueError("phase48 validity violation")

    if verification.get("requiredLayers") != 14:
        raise ValueError("phase48 requiredLayers violation")

    if verification.get("verifiedLayers") != 14:
        raise ValueError("phase48 verifiedLayers violation")

    if verification.get("checkpoint") != "VERIFIED":
        raise ValueError("phase48 checkpoint violation")

    digest_value = verification.get("continuityDigest")
    if not isinstance(digest_value, str) or not HEX64.fullmatch(digest_value):
        raise ValueError("phase48 continuityDigest invalid")


def build_projection(phases):
    return {
        "version": 1,
        "type": TYPE,
        "mode": "READ_ONLY",
        "phases": [
            {
                "phase": phase,
                "type": obj["type"],
                "generatedAt": obj["generatedAt"],
                "digest": digest(
                    {
                        "phase": phase,
                        "type": obj["type"],
                        "mode": obj["mode"],
                        "state": obj["state"],
                        "sourceState": obj["sourceState"],
                        "verification": obj["verification"],
                    }
                ),
            }
            for phase, obj in phases
        ],
    }


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint_state,
    verified_layers,
    temporal_digest,
    phases,
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
                "ALL_REQUIRED_ATTESTATION_TEMPORAL_LAYERS_VERIFIED"
                if ready
                else "CHECKPOINT_ESTABLISHED"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 4,
            "verifiedLayers": verified_layers,
            "checkpoint": checkpoint_state,
            "temporalDigest": temporal_digest,
            "phases": [
                {
                    "phase": phase,
                    "type": obj["type"],
                    "generatedAt": obj["generatedAt"],
                }
                for phase, obj in phases
            ],
        },
        "sources": {
            "phase45": str(PHASE45),
            "phase46": str(PHASE46),
            "phase47": str(PHASE47),
            "phase48": str(PHASE48),
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
    try:
        paths = {
            45: PHASE45,
            46: PHASE46,
            47: PHASE47,
            48: PHASE48,
        }

        phases = []

        for phase in range(45, 49):
            path = paths[phase]

            if not path.exists():
                raise ValueError(f"phase{phase} artifact missing")

            obj = load_json(path)

            if phase == 45:
                validate_phase45(obj)
            elif phase == 46:
                validate_phase46(obj)
            elif phase == 47:
                validate_phase47(obj)
            else:
                validate_phase48(obj)

            parse_timestamp(obj.get("generatedAt"), f"phase{phase}")
            phases.append((phase, obj))

        timestamps = [
            parse_timestamp(obj["generatedAt"], f"phase{phase}")
            for phase, obj in phases
        ]

        for index in range(1, len(timestamps)):
            if timestamps[index] < timestamps[index - 1]:
                raise ValueError(
                    f"timestamp regression: phase{phases[index][0]} "
                    f"before phase{phases[index - 1][0]}"
                )

        projection = build_projection(phases)
        temporal_digest = digest(projection)

        if not CHECKPOINT.exists():
            CHECKPOINT.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "type": TYPE,
                        "createdAt": now(),
                        "temporalDigest": temporal_digest,
                        "temporalProjection": projection,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )

            OUTPUT.write_text(
                json.dumps(
                    build_output(
                        "CHECKPOINT_ESTABLISHED",
                        "CHECKPOINT_ESTABLISHED",
                        False,
                        True,
                        "ESTABLISHED",
                        0,
                        temporal_digest,
                        phases,
                        [],
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )

            print("STATE: CHECKPOINT_ESTABLISHED")
            print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
            print("READY: False")
            print("VALID: True")
            print("CHECKPOINT: ESTABLISHED")
            print("VERIFIED LAYERS: 0/4")
            print(f"TEMPORAL DIGEST: {temporal_digest}")
            print("ERROR COUNT: 0")
            return 0

        checkpoint = load_json(CHECKPOINT)

        if checkpoint.get("type") != TYPE:
            raise ValueError("checkpoint type mismatch")

        if checkpoint.get("temporalDigest") != temporal_digest:
            raise ValueError("checkpoint: temporal drift detected")

        if checkpoint.get("temporalProjection") != projection:
            raise ValueError("checkpoint: temporal projection drift detected")

        OUTPUT.write_text(
            json.dumps(
                build_output(
                    "VERIFIED_READ_ONLY",
                    "VERIFIED_READ_ONLY",
                    True,
                    True,
                    "VERIFIED",
                    4,
                    temporal_digest,
                    phases,
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
        print("VERIFIED LAYERS: 4/4")
        print(f"TEMPORAL DIGEST: {temporal_digest}")
        print("ERROR COUNT: 0")
        return 0

    except Exception as exc:
        error = str(exc)

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
                    [],
                    [error],
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
        print("VERIFIED LAYERS: 0/4")
        print("TEMPORAL DIGEST:")
        print("ERROR COUNT: 1")
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
