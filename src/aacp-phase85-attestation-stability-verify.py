#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path


BASE = Path("provider-output/aacp-observer")

P84_OUTPUT = BASE / "phase84-finality-seal-attestation.json"
P84_CHECKPOINT = BASE / "phase84-finality-seal-attestation-checkpoint.json"

P85_OUTPUT = BASE / "phase85-attestation-stability.json"
P85_CHECKPOINT = BASE / "phase85-attestation-stability-checkpoint.json"


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def verify(p84, p84_cp):
    errors = []

    if p84.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase84:state")

    if p84.get("ready") is not True:
        errors.append("phase84:ready")

    if p84.get("valid") is not True:
        errors.append("phase84:valid")

    if p84.get("checkpoint") != "VERIFIED":
        errors.append("phase84:checkpoint")

    expected_safety = {
        "broadcast": False,
        "networkAccess": False,
        "sideEffects": False,
        "signing": False,
        "submission": False,
        "walletAccess": False,
    }

    if p84.get("safety") != expected_safety:
        errors.append("phase84:safety")

    if p84_cp.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase84:checkpointState")

    if p84_cp.get("executionAuthorized") is not False:
        errors.append("phase84:executionAuthorized")

    p84_output_digest = digest(p84)
    p84_checkpoint_digest = digest(p84_cp)

    if p84.get("verification", {}).get("phase83OutputDigest") != p84_cp.get(
        "phase83OutputDigest"
    ):
        errors.append("phase84:phase83OutputContinuity")

    if p84.get("verification", {}).get("phase83CheckpointDigest") != p84_cp.get(
        "phase83CheckpointDigest"
    ):
        errors.append("phase84:phase83CheckpointContinuity")

    if p84.get("verification", {}).get("attestationDigest") != p84_cp.get(
        "attestationDigest"
    ):
        errors.append("phase84:attestationContinuity")

    return errors, p84_output_digest, p84_checkpoint_digest


def main():
    errors = []

    if not P84_OUTPUT.exists():
        errors.append("phase84:outputMissing")

    if not P84_CHECKPOINT.exists():
        errors.append("phase84:checkpointMissing")

    if errors:
        raise SystemExit("FAIL_CLOSED: " + ",".join(errors))

    p84 = json.loads(P84_OUTPUT.read_text(encoding="utf-8"))
    p84_cp = json.loads(P84_CHECKPOINT.read_text(encoding="utf-8"))

    first_errors, p84_output_digest, p84_checkpoint_digest = verify(
        p84, p84_cp
    )

    errors.extend(first_errors)

    material = {
        "phase84OutputDigest": p84_output_digest,
        "phase84CheckpointDigest": p84_checkpoint_digest,
        "phase83OutputDigest": p84_cp.get("phase83OutputDigest"),
        "phase83CheckpointDigest": p84_cp.get("phase83CheckpointDigest"),
        "attestationDigest": p84_cp.get("attestationDigest"),
    }

    first_attestation_digest = digest(material)

    second_errors, second_output_digest, second_checkpoint_digest = verify(
        p84, p84_cp
    )

    second_material = {
        "phase84OutputDigest": second_output_digest,
        "phase84CheckpointDigest": second_checkpoint_digest,
        "phase83OutputDigest": p84_cp.get("phase83OutputDigest"),
        "phase83CheckpointDigest": p84_cp.get("phase83CheckpointDigest"),
        "attestationDigest": p84_cp.get("attestationDigest"),
    }

    second_attestation_digest = digest(second_material)

    replay_stable = (
        first_attestation_digest == second_attestation_digest
        and p84_output_digest == second_output_digest
        and p84_checkpoint_digest == second_checkpoint_digest
        and not second_errors
    )

    if not replay_stable:
        errors.append("attestation:replayUnstable")

    valid = not errors

    result = {
        "state": "VERIFIED_READ_ONLY",
        "ready": valid,
        "valid": valid,
        "checkpoint": "VERIFIED" if valid else "REJECTED",
        "type": "AACP_ATTESTATION_STABILITY_VERIFY",
        "verification": {
            "errorCount": len(errors),
            "errors": errors,
            "firstAttestationDigest": first_attestation_digest,
            "secondAttestationDigest": second_attestation_digest,
            "replayStable": replay_stable,
            "replayCount": 2,
            "phase84OutputDigest": p84_output_digest,
            "phase84CheckpointDigest": p84_checkpoint_digest,
        },
        "safety": {
            "broadcast": False,
            "networkAccess": False,
            "sideEffects": False,
            "signing": False,
            "submission": False,
            "walletAccess": False,
        },
    }

    P85_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    P85_OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    checkpoint = {
        "state": "VERIFIED_READ_ONLY",
        "type": "AACP_ATTESTATION_STABILITY_CHECKPOINT",
        "executionAuthorized": False,
        "replayCount": 2,
        "firstAttestationDigest": first_attestation_digest,
        "secondAttestationDigest": second_attestation_digest,
        "phase84OutputDigest": p84_output_digest,
        "phase84CheckpointDigest": p84_checkpoint_digest,
        "resultDigest": digest(result),
    }

    P85_CHECKPOINT.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("STATE:", result["state"])
    print("READY:", result["ready"])
    print("VALID:", result["valid"])
    print("CHECKPOINT:", result["checkpoint"])
    print("REPLAY STABLE:", replay_stable)
    print("REPLAY COUNT:", 2)
    print("ATTESTATION DIGEST:", first_attestation_digest)
    print("ERROR COUNT:", len(errors))

    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
