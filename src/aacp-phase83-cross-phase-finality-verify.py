#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

P82 = BASE / "phase82-seal-continuity.json"
P82_CP = BASE / "phase82-seal-continuity-checkpoint.json"

OUT = BASE / "phase83-cross-phase-finality.json"
CP = BASE / "phase83-cross-phase-finality-checkpoint.json"

TYPE = (
    "AACP_EVIDENCE_CHAIN_CROSS_PHASE_FINALITY_"
    "VERIFIED_READ_ONLY_CHECKPOINT_VERIFY"
)


def digest(value):
    raw = json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def load(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main():
    errors = []

    try:
        p82 = load(P82)
        p82_cp = load(P82_CP)

        p82_ver = p82.get("verification", {})
        p82_safety = p82.get("safety", {})

        if p82.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase82:state")

        if p82.get("ready") is not True:
            errors.append("phase82:ready")

        if p82.get("valid") is not True:
            errors.append("phase82:valid")

        if p82.get("checkpoint") != "VERIFIED":
            errors.append("phase82:checkpoint")

        if p82_cp.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase82:checkpointState")

        if p82_cp.get("executionAuthorized") is not False:
            errors.append("phase82:checkpointExecutionAuthorized")

        p82_digest = digest(p82)

        if p82_cp.get("resultDigest") != p82_digest:
            errors.append("phase82:checkpointResultDigest")

        expected_safety = {
            "broadcast": False,
            "networkAccess": False,
            "sideEffects": False,
            "signing": False,
            "submission": False,
            "walletAccess": False,
        }

        for key, expected in expected_safety.items():
            if p82_safety.get(key) is not expected:
                errors.append(f"phase82:safety:{key}")

        if p82_safety != expected_safety:
            errors.append("phase82:safetySchema")

        if "phase79ChainDigest" not in p82_ver:
            errors.append("phase82:phase79ChainDigestMissing")

        if "phase79CheckpointDigest" not in p82_ver:
            errors.append("phase82:phase79CheckpointDigestMissing")

        if "phase79OutputDigest" not in p82_ver:
            errors.append("phase82:phase79OutputDigestMissing")

        if "phase79ReplayDigest" not in p82_ver:
            errors.append("phase82:phase79ReplayDigestMissing")

        if "phase80CheckpointDigest" not in p82_ver:
            errors.append("phase82:phase80CheckpointDigestMissing")

        if "phase80OutputDigest" not in p82_ver:
            errors.append("phase82:phase80OutputDigestMissing")

        if "phase80ResultDigest" not in p82_ver:
            errors.append("phase82:phase80ResultDigestMissing")

        if "phase81OutputDigest" not in p82_ver:
            errors.append("phase82:phase81OutputDigestMissing")

        if "reconstructedContinuityDigest" not in p82_ver:
            errors.append("phase82:continuityDigestMissing")

        if p82_cp.get("phase80ResultDigest") != p82_ver.get(
            "phase80ResultDigest"
        ):
            errors.append("phase82:checkpointPhase80ResultDigest")

        if p82_cp.get("phase81ResultDigest") != p82_ver.get(
            "phase81OutputDigest"
        ):
            errors.append("phase82:checkpointPhase81ResultDigest")

        if p82_cp.get("reconstructedContinuityDigest") != p82_ver.get(
            "reconstructedContinuityDigest"
        ):
            errors.append("phase82:checkpointContinuityDigest")

        if p82_cp.get("phase80CheckpointResultDigest") != p82_ver.get(
            "phase80ResultDigest"
        ):
            errors.append("phase82:checkpointPhase80CheckpointResultDigest")

    except Exception as exc:
        errors.append(f"load:{type(exc).__name__}:{exc}")

        p82 = {}
        p82_cp = {}
        p82_ver = {}
        p82_safety = {}
        p82_digest = ""

    valid = not errors

    finality_material = {
        "phase82OutputDigest": p82_digest,
        "phase82CheckpointDigest": (
            digest(p82_cp) if p82_cp else ""
        ),
        "phase80ResultDigest": p82_ver.get(
            "phase80ResultDigest"
        ),
        "phase81OutputDigest": p82_ver.get(
            "phase81OutputDigest"
        ),
        "reconstructedContinuityDigest": p82_ver.get(
            "reconstructedContinuityDigest"
        ),
    }

    finality_digest = digest(finality_material)

    result = {
        "state": "VERIFIED_READ_ONLY" if valid else "REJECTED",
        "ready": valid,
        "valid": valid,
        "checkpoint": "VERIFIED" if valid else "REJECTED",
        "type": TYPE,
        "verification": {
            "errorCount": len(errors),
            "errors": errors,
            "phase82OutputDigest": p82_digest,
            "phase82CheckpointDigest": (
                digest(p82_cp) if p82_cp else ""
            ),
            "phase80ResultDigest": p82_ver.get(
                "phase80ResultDigest"
            ),
            "phase81OutputDigest": p82_ver.get(
                "phase81OutputDigest"
            ),
            "reconstructedContinuityDigest": p82_ver.get(
                "reconstructedContinuityDigest"
            ),
            "finalityMaterialDigest": finality_digest,
            "valid": valid,
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

    result_digest = digest(result)

    checkpoint = {
        "state": result["state"],
        "type": TYPE,
        "executionAuthorized": False,
        "phase82OutputDigest": p82_digest,
        "phase82CheckpointDigest": (
            digest(p82_cp) if p82_cp else ""
        ),
        "phase80ResultDigest": p82_ver.get(
            "phase80ResultDigest"
        ),
        "phase81OutputDigest": p82_ver.get(
            "phase81OutputDigest"
        ),
        "reconstructedContinuityDigest": p82_ver.get(
            "reconstructedContinuityDigest"
        ),
        "finalityMaterialDigest": finality_digest,
        "resultDigest": result_digest,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)

    OUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    CP.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STATE:", result["state"])
    print("READY:", result["ready"])
    print("VALID:", result["valid"])
    print("CHECKPOINT:", result["checkpoint"])
    print("PHASE82 OUTPUT DIGEST:", p82_digest)
    print(
        "PHASE82 CHECKPOINT DIGEST:",
        checkpoint["phase82CheckpointDigest"],
    )
    print(
        "FINALITY MATERIAL DIGEST:",
        finality_digest,
    )
    print("ERROR COUNT:", len(errors))

    if errors:
        for error in errors:
            print("-", error)


if __name__ == "__main__":
    main()
