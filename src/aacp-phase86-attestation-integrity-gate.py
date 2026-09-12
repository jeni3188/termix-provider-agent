#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "provider-output" / "aacp-observer"

P85 = OUT / "phase85-attestation-stability.json"
P85_CP = OUT / "phase85-attestation-stability-checkpoint.json"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def verify(p85, p85_cp):
    errors = []

    if p85.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase85 state invalid")

    if p85.get("ready") is not True:
        errors.append("phase85 ready invalid")

    if p85.get("valid") is not True:
        errors.append("phase85 valid invalid")

    if p85.get("checkpoint") != "VERIFIED":
        errors.append("phase85 checkpoint invalid")

    safety = p85.get("safety", {})
    expected_safety = {
        "broadcast": False,
        "networkAccess": False,
        "sideEffects": False,
        "signing": False,
        "submission": False,
        "walletAccess": False,
    }

    if safety != expected_safety:
        errors.append("phase85 safety invalid")

    verification = p85.get("verification", {})

    if verification.get("replayStable") is not True:
        errors.append("replay stability invalid")

    if verification.get("replayCount") != 2:
        errors.append("replay count invalid")

    p85_output_digest = digest(p85)
    p85_checkpoint_digest = digest(p85_cp)

    if p85_cp.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase85 checkpoint state invalid")

    if p85_cp.get("executionAuthorized") is not False:
        errors.append("execution authorization invalid")

    if p85_cp.get("replayCount") != 2:
        errors.append("checkpoint replay count invalid")

    if p85_cp.get("phase84OutputDigest") != verification.get("phase84OutputDigest"):
        errors.append("phase84 output continuity invalid")

    if p85_cp.get("phase84CheckpointDigest") != verification.get(
        "phase84CheckpointDigest"
    ):
        errors.append("phase84 checkpoint continuity invalid")

    if p85_cp.get("firstAttestationDigest") != verification.get(
        "firstAttestationDigest"
    ):
        errors.append("first attestation continuity invalid")

    if p85_cp.get("secondAttestationDigest") != verification.get(
        "secondAttestationDigest"
    ):
        errors.append("second attestation continuity invalid")

    if p85_cp.get("firstAttestationDigest") != p85_cp.get(
        "secondAttestationDigest"
    ):
        errors.append("attestation replay mismatch")

    material = {
        "phase85OutputDigest": p85_output_digest,
        "phase85CheckpointDigest": p85_checkpoint_digest,
        "phase84OutputDigest": verification.get("phase84OutputDigest"),
        "phase84CheckpointDigest": verification.get("phase84CheckpointDigest"),
        "firstAttestationDigest": verification.get("firstAttestationDigest"),
        "secondAttestationDigest": verification.get("secondAttestationDigest"),
        "replayCount": verification.get("replayCount"),
    }

    integrity_digest = digest(material)
    valid = not errors

    result = {
        "state": "VERIFIED_READ_ONLY" if valid else "REJECTED",
        "ready": valid,
        "valid": valid,
        "checkpoint": "VERIFIED" if valid else "REJECTED",
        "type": "AACP_ATTESTATION_INTEGRITY_GATE",
        "verification": {
            "errorCount": len(errors),
            "errors": errors,
            "phase85OutputDigest": p85_output_digest,
            "phase85CheckpointDigest": p85_checkpoint_digest,
            "phase84OutputDigest": verification.get("phase84OutputDigest"),
            "phase84CheckpointDigest": verification.get("phase84CheckpointDigest"),
            "firstAttestationDigest": verification.get("firstAttestationDigest"),
            "secondAttestationDigest": verification.get("secondAttestationDigest"),
            "replayStable": verification.get("replayStable"),
            "replayCount": verification.get("replayCount"),
            "integrityDigest": integrity_digest,
        },
        "safety": expected_safety,
    }

    checkpoint = {
        "state": result["state"],
        "type": "AACP_ATTESTATION_INTEGRITY_GATE_CHECKPOINT",
        "executionAuthorized": False,
        "integrityDigest": integrity_digest,
        "phase85OutputDigest": p85_output_digest,
        "phase85CheckpointDigest": p85_checkpoint_digest,
        "resultDigest": digest(result),
    }

    return result, checkpoint


def main():
    p85 = json.loads(P85.read_text())
    p85_cp = json.loads(P85_CP.read_text())

    result, checkpoint = verify(p85, p85_cp)

    (OUT / "phase86-attestation-integrity-gate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    (OUT / "phase86-attestation-integrity-gate-checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n"
    )

    print("STATE:", result["state"])
    print("READY:", result["ready"])
    print("VALID:", result["valid"])
    print("CHECKPOINT:", result["checkpoint"])
    print(
        "INTEGRITY DIGEST:",
        result["verification"]["integrityDigest"],
    )
    print("ERROR COUNT:", result["verification"]["errorCount"])

    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
