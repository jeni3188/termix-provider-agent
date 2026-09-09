#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
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

PHASE49 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-temporal-continuity-verify.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-"
    "cross-artifact-attestation-chain-finality-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-chain-finality-verify.json"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_"
    "CROSS_ARTIFACT_ATTESTATION_CHAIN_FINALITY_VERIFY"
)

EXPECTED = {
    45: (
        "AACP_EVIDENCE_CHAIN_HEALTH_"
        "CROSS_ARTIFACT_IDENTITY_ATTESTATION"
    ),
    46: (
        "AACP_EVIDENCE_CHAIN_HEALTH_"
        "CROSS_ARTIFACT_ATTESTATION_CONSISTENCY_VERIFY"
    ),
    47: (
        "AACP_EVIDENCE_CHAIN_HEALTH_"
        "CROSS_ARTIFACT_ATTESTATION_DRIFT_VERIFY"
    ),
    48: (
        "AACP_EVIDENCE_CHAIN_HEALTH_"
        "CROSS_ARTIFACT_ATTESTATION_DRIFT_CONTINUITY_VERIFY"
    ),
    49: (
        "AACP_EVIDENCE_CHAIN_HEALTH_"
        "CROSS_ARTIFACT_ATTESTATION_TEMPORAL_CONTINUITY_VERIFY"
    ),
}

PHASES = {
    45: PHASE45,
    46: PHASE46,
    47: PHASE47,
    48: PHASE48,
    49: PHASE49,
}


def canonical(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(obj):
    return hashlib.sha256(
        canonical(obj).encode("utf-8")
    ).hexdigest()


def load_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def safety_ok(obj):
    safety = obj.get("safety")
    if not isinstance(safety, dict):
        return False

    return not any(
        isinstance(value, bool) and value is True
        for value in safety.values()
    )


def validate_common(obj, expected_type):
    if not isinstance(obj, dict):
        return False

    if obj.get("type") != expected_type:
        return False

    if obj.get("mode") != "READ_ONLY":
        return False

    if obj.get("executionAuthorized") is not False:
        return False

    if not safety_ok(obj):
        return False

    if obj.get("errorCount") != 0:
        return False

    if obj.get("errors") != []:
        return False

    generated_at = obj.get("generatedAt")

    if not isinstance(generated_at, str):
        return False

    try:
        datetime.fromisoformat(generated_at)
    except ValueError:
        return False

    return True


def verified(obj, verification, required):
    if obj.get("state") != "VERIFIED_READ_ONLY":
        return False

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        return False

    readiness = obj.get("readiness")

    if not isinstance(readiness, dict):
        return False

    if readiness.get("ready") is not True:
        return False

    if not isinstance(verification, dict):
        return False

    if verification.get("valid") is not True:
        return False

    if verification.get("requiredLayers") != required:
        return False

    if verification.get("verifiedLayers") != required:
        return False

    if verification.get("checkpoint") != "VERIFIED":
        return False

    return True


def validate_phase45(obj):
    if not validate_common(obj, EXPECTED[45]):
        return False

    verification = obj.get("verification")

    if not verified(obj, verification, 14):
        return False

    value = verification.get("attestationDigest")

    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def validate_phase46(obj):
    if not validate_common(obj, EXPECTED[46]):
        return False

    verification = obj.get("verification")

    if not verified(obj, verification, 14):
        return False

    value = verification.get("consistencyDigest")

    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def validate_phase47(obj):
    if not validate_common(obj, EXPECTED[47]):
        return False

    verification = obj.get("verification")

    if not verified(obj, verification, 14):
        return False

    value = verification.get("driftDigest")

    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def validate_phase48(obj):
    if not validate_common(obj, EXPECTED[48]):
        return False

    verification = obj.get("verification")

    if not verified(obj, verification, 14):
        return False

    value = verification.get("continuityDigest")

    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def validate_phase49(obj):
    if not validate_common(obj, EXPECTED[49]):
        return False

    verification = obj.get("verification")

    if not verified(obj, verification, 4):
        return False

    if verification.get("temporalDigest") is None:
        return False

    if not isinstance(verification.get("temporalDigest"), str):
        return False

    if re.fullmatch(
        r"[0-9a-f]{64}",
        verification["temporalDigest"],
    ) is None:
        return False

    phases = verification.get("phases")

    if not isinstance(phases, list):
        return False

    if len(phases) != 4:
        return False

    return True


def build_projection(objects):
    phases = []

    for phase in range(45, 50):
        obj = objects[phase]
        verification = obj["verification"]

        phases.append(
            {
                "phase": phase,
                "type": obj["type"],
                "generatedAt": obj["generatedAt"],
                "state": obj["state"],
                "sourceState": obj["sourceState"],
                "ready": obj["readiness"]["ready"],
                "valid": verification["valid"],
                "checkpoint": verification["checkpoint"],
                "digest": digest(
                    {
                        "phase": phase,
                        "type": obj["type"],
                        "mode": obj["mode"],
                        "generatedAt": obj["generatedAt"],
                        "state": obj["state"],
                        "sourceState": obj["sourceState"],
                        "readiness": obj["readiness"],
                        "verification": verification,
                    }
                ),
            }
        )

    return {
        "version": 1,
        "type": TYPE,
        "mode": "READ_ONLY",
        "phases": phases,
    }


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint_state,
    finality_digest,
    phases,
    errors,
):
    return {
        "version": 1,
        "type": TYPE,
        "generatedAt": datetime.now().astimezone().isoformat(),
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
                "FINAL_CROSS_ARTIFACT_CHAIN_VERIFIED"
                if ready
                else (
                    "FINAL_CROSS_ARTIFACT_CHAIN_CHECKPOINT_ESTABLISHED"
                    if valid and checkpoint_state == "ESTABLISHED"
                    else "FINAL_CROSS_ARTIFACT_CHAIN_BLOCKED"
                )
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 5,
            "verifiedLayers": 5 if ready else 0,
            "checkpoint": checkpoint_state,
            "finalityDigest": finality_digest,
            "phases": phases,
        },
        "sources": {
            "phase45": str(PHASE45),
            "phase46": str(PHASE46),
            "phase47": str(PHASE47),
            "phase48": str(PHASE48),
            "phase49": str(PHASE49),
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "readOnly": True,
            "executionAuthorized": False,
            "networkAccessAllowed": False,
            "walletAccessAllowed": False,
            "signingAllowed": False,
            "broadcastAllowed": False,
            "submissionAllowed": False,
        },
    }


def main():
    BASE.mkdir(parents=True, exist_ok=True)

    errors = []
    objects = {}

    validators = {
        45: validate_phase45,
        46: validate_phase46,
        47: validate_phase47,
        48: validate_phase48,
        49: validate_phase49,
    }

    for phase in range(45, 50):
        path = PHASES[phase]

        if not path.exists():
            errors.append(f"PHASE{phase}_MISSING")
            continue

        obj = load_json(path)

        if obj is None:
            errors.append(f"PHASE{phase}_CORRUPT")
            continue

        objects[phase] = obj

        if not validators[phase](obj):
            errors.append(f"PHASE{phase}_INVALID")

    if errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "BLOCKED",
            None,
            [],
            errors,
        )
        OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True))
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: BLOCKED")
        print("VERIFIED LAYERS: 0/5")
        print("FINALITY DIGEST: None")
        print(f"ERROR COUNT: {len(errors)}")
        return 1

    projection = build_projection(objects)
    finality_digest = digest(projection)

    checkpoint = load_json(CHECKPOINT) if CHECKPOINT.exists() else None

    if checkpoint is None:
        checkpoint = {
            "version": 1,
            "type": TYPE,
            "createdAt": datetime.now().astimezone().isoformat(),
            "finalityDigest": finality_digest,
            "finalityProjection": projection,
        }

        CHECKPOINT.write_text(
            json.dumps(
                checkpoint,
                indent=2,
                sort_keys=True,
            )
        )

        output = build_output(
            "CHECKPOINT_ESTABLISHED",
            "CHECKPOINT_ESTABLISHED",
            False,
            True,
            "ESTABLISHED",
            finality_digest,
            projection["phases"],
            [],
        )

        OUTPUT.write_text(
            json.dumps(
                output,
                indent=2,
                sort_keys=True,
            )
        )

        print("STATE: CHECKPOINT_ESTABLISHED")
        print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
        print("READY: False")
        print("VALID: True")
        print("CHECKPOINT: ESTABLISHED")
        print("VERIFIED LAYERS: 0/5")
        print(f"FINALITY DIGEST: {finality_digest}")
        print("ERROR COUNT: 0")
        return 0

    checkpoint_errors = []

    if checkpoint.get("version") != 1:
        checkpoint_errors.append("CHECKPOINT_VERSION_INVALID")

    if checkpoint.get("type") != TYPE:
        checkpoint_errors.append("CHECKPOINT_TYPE_INVALID")

    if checkpoint.get("finalityDigest") != finality_digest:
        checkpoint_errors.append("FINALITY_DIGEST_DRIFT")

    if checkpoint.get("finalityProjection") != projection:
        checkpoint_errors.append("FINALITY_PROJECTION_DRIFT")

    if checkpoint_errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "BLOCKED",
            finality_digest,
            projection["phases"],
            checkpoint_errors,
        )

        OUTPUT.write_text(
            json.dumps(
                output,
                indent=2,
                sort_keys=True,
            )
        )

        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: BLOCKED")
        print("VERIFIED LAYERS: 0/5")
        print(f"FINALITY DIGEST: {finality_digest}")
        print(f"ERROR COUNT: {len(checkpoint_errors)}")
        return 1

    output = build_output(
        "VERIFIED_READ_ONLY",
        "VERIFIED_READ_ONLY",
        True,
        True,
        "VERIFIED",
        finality_digest,
        projection["phases"],
        [],
    )

    OUTPUT.write_text(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
    )

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("VERIFIED LAYERS: 5/5")
    print(f"FINALITY DIGEST: {finality_digest}")
    print("ERROR COUNT: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
