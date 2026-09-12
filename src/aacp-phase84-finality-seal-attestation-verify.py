#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path


BASE = Path("provider-output/aacp-observer")

P83_OUTPUT = BASE / "phase83-cross-phase-finality.json"
P83_CHECKPOINT = BASE / "phase83-cross-phase-finality-checkpoint.json"

P84_OUTPUT = BASE / "phase84-finality-seal-attestation.json"
P84_CHECKPOINT = BASE / "phase84-finality-seal-attestation-checkpoint.json"


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def main():
    errors = []

    if not P83_OUTPUT.exists():
        errors.append("phase83:outputMissing")

    if not P83_CHECKPOINT.exists():
        errors.append("phase83:checkpointMissing")

    if errors:
        result = {
            "state": "VERIFIED_READ_ONLY",
            "ready": False,
            "valid": False,
            "checkpoint": "REJECTED",
            "type": "AACP_FINALITY_SEAL_ATTESTATION_VERIFY",
            "verification": {
                "errorCount": len(errors),
                "errors": errors,
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
        P84_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        P84_OUTPUT.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        raise SystemExit(1)

    p83 = json.loads(P83_OUTPUT.read_text(encoding="utf-8"))
    p83_cp = json.loads(P83_CHECKPOINT.read_text(encoding="utf-8"))

    p83_ver = p83.get("verification", {})

    if p83.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase83:state")

    if p83.get("ready") is not True:
        errors.append("phase83:ready")

    if p83.get("valid") is not True:
        errors.append("phase83:valid")

    if p83.get("checkpoint") != "VERIFIED":
        errors.append("phase83:checkpoint")

    if p83.get("safety") != {
        "broadcast": False,
        "networkAccess": False,
        "sideEffects": False,
        "signing": False,
        "submission": False,
        "walletAccess": False,
    }:
        errors.append("phase83:safety")

    if p83_cp.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase83:checkpointState")

    if p83_cp.get("executionAuthorized") is not False:
        errors.append("phase83:executionAuthorized")

    p83_output_digest = digest(p83)
    p83_checkpoint_digest = digest(p83_cp)

    if p83_cp.get("phase82OutputDigest") is None:
        errors.append("phase83:phase82OutputDigest")

    if p83_cp.get("phase82CheckpointDigest") is None:
        errors.append("phase83:phase82CheckpointDigest")

    if p83_cp.get("finalityMaterialDigest") is None:
        errors.append("phase83:finalityMaterialDigest")

    if p83_cp.get("resultDigest") != p83_output_digest:
        errors.append("phase83:checkpointResultDigest")

    if p83_ver.get("phase82OutputDigest") != p83_cp.get("phase82OutputDigest"):
        errors.append("phase83:phase82OutputContinuity")

    if p83_ver.get("phase82CheckpointDigest") != p83_cp.get("phase82CheckpointDigest"):
        errors.append("phase83:phase82CheckpointContinuity")

    if p83_ver.get("finalityMaterialDigest") != p83_cp.get("finalityMaterialDigest"):
        errors.append("phase83:finalityMaterialContinuity")

    attestation_material = {
        "phase83OutputDigest": p83_output_digest,
        "phase83CheckpointDigest": p83_checkpoint_digest,
        "phase82OutputDigest": p83_cp.get("phase82OutputDigest"),
        "phase82CheckpointDigest": p83_cp.get("phase82CheckpointDigest"),
        "finalityMaterialDigest": p83_cp.get("finalityMaterialDigest"),
    }

    attestation_digest = digest(attestation_material)

    valid = not errors

    result = {
        "state": "VERIFIED_READ_ONLY",
        "ready": valid,
        "valid": valid,
        "checkpoint": "VERIFIED" if valid else "REJECTED",
        "type": "AACP_FINALITY_SEAL_ATTESTATION_VERIFY",
        "verification": {
            "errorCount": len(errors),
            "errors": errors,
            "phase83OutputDigest": p83_output_digest,
            "phase83CheckpointDigest": p83_checkpoint_digest,
            "phase82OutputDigest": p83_cp.get("phase82OutputDigest"),
            "phase82CheckpointDigest": p83_cp.get("phase82CheckpointDigest"),
            "finalityMaterialDigest": p83_cp.get("finalityMaterialDigest"),
            "attestationDigest": attestation_digest,
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

    checkpoint = {
        "state": "VERIFIED_READ_ONLY",
        "type": "AACP_FINALITY_SEAL_ATTESTATION_CHECKPOINT",
        "executionAuthorized": False,
        "phase83OutputDigest": p83_output_digest,
        "phase83CheckpointDigest": p83_checkpoint_digest,
        "phase82OutputDigest": p83_cp.get("phase82OutputDigest"),
        "phase82CheckpointDigest": p83_cp.get("phase82CheckpointDigest"),
        "finalityMaterialDigest": p83_cp.get("finalityMaterialDigest"),
        "attestationDigest": attestation_digest,
    }

    result_digest = digest(result)
    checkpoint["resultDigest"] = result_digest

    P84_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    P84_OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    P84_CHECKPOINT.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("STATE:", result["state"])
    print("READY:", result["ready"])
    print("VALID:", result["valid"])
    print("CHECKPOINT:", result["checkpoint"])
    print("PHASE83 OUTPUT DIGEST:", p83_output_digest)
    print("PHASE83 CHECKPOINT DIGEST:", p83_checkpoint_digest)
    print("ATTESTATION DIGEST:", attestation_digest)
    print("ERROR COUNT:", len(errors))

    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
