#!/usr/bin/env python3

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

P79 = BASE / "phase79-deterministic-replay.json"
P79_CP = BASE / "phase79-deterministic-replay-checkpoint.json"

P80 = BASE / "phase80-checkpoint-continuity.json"
P80_CP = BASE / "phase80-checkpoint-continuity-checkpoint.json"

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "TAMPER_EVIDENT_CHECKPOINT_CONTINUITY_VERIFY"
)


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load(path):
    if not path.exists():
        raise RuntimeError(f"missing:{path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    errors = []

    try:
        p79 = load(P79)
        p79_cp = load(P79_CP)

        p79_state = p79.get("state")
        p79_ver = p79.get("verification", {})

        p79_cp_state = p79_cp.get("state")
        p79_result_digest = digest(p79)

        p79_digest = digest(p79)
        p79_checkpoint_digest = digest(p79_cp)

        # Phase79 itself must remain valid and read-only.
        if p79_state != "VERIFIED_READ_ONLY":
            errors.append("phase79:state")

        if p79_ver.get("valid") is not True:
            errors.append("phase79:valid")

        if p79_ver.get("replayStable") is not True:
            errors.append("phase79:replayStable")

        if p79_ver.get("replayCount") != 2:
            errors.append("phase79:replayCount")

        # Phase79 checkpoint must remain verified.
        if p79_cp_state != "VERIFIED_READ_ONLY":
            errors.append("phase79:checkpointState")

        if p79_cp.get("executionAuthorized") is not False:
            errors.append("phase79:executionAuthorized")

        if p79_cp.get("replayStable") is not True:
            errors.append("phase79:checkpointReplayStable")

        if p79_cp.get("replayCount") != 2:
            errors.append("phase79:checkpointReplayCount")

        # The checkpoint must own the exact Phase79 result digest.
        if p79_cp.get("resultDigest") != p79_result_digest:
            errors.append("phase79:checkpointResultDigest")

        # Phase79 checkpoint must reference the same chain digest
        # that Phase79 reconstructed and reported.
        reconstructed = p79_ver.get("reconstructedChainDigest")
        first = p79_ver.get("firstChainDigest")
        second = p79_ver.get("secondChainDigest")
        checkpoint_chain = p79_cp.get("chainDigest")

        if not reconstructed:
            errors.append("phase79:reconstructedChainDigest")

        if first != second:
            errors.append("phase79:replayDigestMismatch")

        if first != reconstructed:
            errors.append("phase79:firstVsReconstructed")

        if second != reconstructed:
            errors.append("phase79:secondVsReconstructed")

        if checkpoint_chain != reconstructed:
            errors.append("phase79:checkpointChainDigest")

        # Build the Phase80 continuity commitment.
        continuity = {
            "phase79OutputDigest": p79_digest,
            "phase79CheckpointDigest": p79_checkpoint_digest,
            "phase79ChainDigest": reconstructed,
            "phase79ReplayDigest": first,
            "phase79ReplayCount": p79_ver.get("replayCount"),
        }

        continuity_digest = digest(continuity)

    except Exception as exc:
        errors.append(f"exception:{exc}")
        p79_digest = None
        p79_checkpoint_digest = None
        reconstructed = None
        first = None
        continuity_digest = None

    result = {
        "version": 1,
        "type": TYPE,
        "generatedAt": datetime.now(timezone.utc).astimezone().isoformat(),
        "mode": "READ_ONLY",
        "state": (
            "VERIFIED_READ_ONLY"
            if not errors
            else "REJECTED_READ_ONLY"
        ),
        "sourceState": "VERIFIED_READ_ONLY",
        "executionAuthorized": False,
        "readiness": {
            "ready": not errors,
            "observations": 5,
            "requiredObservations": 5,
        },
        "safety": {
            "broadcastPerformed": False,
            "signingPerformed": False,
            "submissionPerformed": False,
        },
        "sideEffects": {
            "networkAccess": False,
            "walletAccess": False,
        },
        "verification": {
            "valid": not errors,
            "checkpoint": (
                "VERIFIED"
                if not errors
                else "REJECTED"
            ),
            "phase79OutputDigest": p79_digest,
            "phase79CheckpointDigest": p79_checkpoint_digest,
            "phase79ChainDigest": reconstructed,
            "phase79ReplayDigest": first,
            "continuityDigest": continuity_digest,
        },
        "errorCount": len(errors),
        "errors": errors,
    }

    checkpoint = {
        "version": 1,
        "type": TYPE,
        "state": result["state"],
        "executionAuthorized": False,
        "observationCount": result["readiness"]["observations"],
        "phase79OutputDigest": p79_digest,
        "phase79CheckpointDigest": p79_checkpoint_digest,
        "phase79ChainDigest": reconstructed,
        "phase79ReplayDigest": first,
        "continuityDigest": continuity_digest,
        "resultDigest": digest(result),
    }

    BASE.mkdir(parents=True, exist_ok=True)

    P80.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    P80_CP.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"STATE: {result['state']}")
    print(f"READY: {result['readiness']['ready']}")
    print(f"VALID: {result['verification']['valid']}")
    print(
        "CHECKPOINT: "
        f"{result['verification']['checkpoint']}"
    )
    print(
        "PHASE79 CHAIN DIGEST: "
        f"{result['verification']['phase79ChainDigest']}"
    )
    print(
        "CONTINUITY DIGEST: "
        f"{result['verification']['continuityDigest']}"
    )
    print(f"ERROR COUNT: {len(errors)}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
