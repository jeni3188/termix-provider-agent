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

P81 = BASE / "phase81-checkpoint-seal.json"
P81_CP = BASE / "phase81-checkpoint-seal-checkpoint.json"

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "TAMPER_EVIDENT_CHECKPOINT_SEAL_VERIFY"
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
        p80 = load(P80)
        p80_cp = load(P80_CP)

        p79_ver = p79.get("verification", {})
        p80_ver = p80.get("verification", {})

        # Phase80 must remain verified read-only.
        if p80.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase80:state")

        if p80_ver.get("valid") is not True:
            errors.append("phase80:valid")

        if p80_ver.get("checkpoint") != "VERIFIED":
            errors.append("phase80:checkpoint")

        if p80.get("executionAuthorized") is not False:
            errors.append("phase80:executionAuthorized")

        # Phase80 checkpoint must remain verified/read-only.
        if p80_cp.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase80:checkpointState")

        if p80_cp.get("executionAuthorized") is not False:
            errors.append("phase80:checkpointExecutionAuthorized")

        # Independent Phase80 result digest verification.
        p80_result_digest = digest(p80)

        if p80_cp.get("resultDigest") != p80_result_digest:
            errors.append("phase80:checkpointResultDigest")

        # Reconstruct the Phase80 continuity commitment independently
        # from the original Phase79 evidence.
        p79_digest = digest(p79)
        p79_cp_digest = digest(p79_cp)

        reconstructed = p79_ver.get("reconstructedChainDigest")
        replay = p79_ver.get("firstChainDigest")
        replay_count = p79_ver.get("replayCount")

        continuity = {
            "phase79OutputDigest": p79_digest,
            "phase79CheckpointDigest": p79_cp_digest,
            "phase79ChainDigest": reconstructed,
            "phase79ReplayDigest": replay,
            "phase79ReplayCount": replay_count,
        }

        reconstructed_continuity = digest(continuity)

        # Phase80 output and checkpoint must agree with reconstruction.
        if p80_ver.get("phase79OutputDigest") != p79_digest:
            errors.append("phase80:phase79OutputDigest")

        if p80_ver.get("phase79CheckpointDigest") != p79_cp_digest:
            errors.append("phase80:phase79CheckpointDigest")

        if p80_ver.get("phase79ChainDigest") != reconstructed:
            errors.append("phase80:phase79ChainDigest")

        if p80_ver.get("phase79ReplayDigest") != replay:
            errors.append("phase80:phase79ReplayDigest")

        if p80_ver.get("continuityDigest") != reconstructed_continuity:
            errors.append("phase80:continuityDigest")

        if p80_cp.get("phase79OutputDigest") != p79_digest:
            errors.append("phase80cp:phase79OutputDigest")

        if p80_cp.get("phase79CheckpointDigest") != p79_cp_digest:
            errors.append("phase80cp:phase79CheckpointDigest")

        if p80_cp.get("phase79ChainDigest") != reconstructed:
            errors.append("phase80cp:phase79ChainDigest")

        if p80_cp.get("phase79ReplayDigest") != replay:
            errors.append("phase80cp:phase79ReplayDigest")

        if p80_cp.get("continuityDigest") != reconstructed_continuity:
            errors.append("phase80cp:continuityDigest")

        # Safety invariants.
        if p80.get("safety", {}).get("broadcastPerformed") is not False:
            errors.append("phase80:broadcastPerformed")

        if p80.get("safety", {}).get("signingPerformed") is not False:
            errors.append("phase80:signingPerformed")

        if p80.get("safety", {}).get("submissionPerformed") is not False:
            errors.append("phase80:submissionPerformed")

        if p80.get("sideEffects", {}).get("networkAccess") is not False:
            errors.append("phase80:networkAccess")

        if p80.get("sideEffects", {}).get("walletAccess") is not False:
            errors.append("phase80:walletAccess")

    except Exception as exc:
        errors.append(f"exception:{exc}")
        p80_result_digest = None
        p79_digest = None
        p79_cp_digest = None
        reconstructed = None
        replay = None
        reconstructed_continuity = None

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
            "observations": 6,
            "requiredObservations": 6,
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
            "phase79CheckpointDigest": p79_cp_digest,
            "phase79ChainDigest": reconstructed,
            "phase79ReplayDigest": replay,
            "phase80ResultDigest": p80_result_digest,
            "reconstructedContinuityDigest": reconstructed_continuity,
            "phase80CheckpointResultDigest": (
                p80_cp.get("resultDigest")
                if "p80_cp" in locals()
                else None
            ),
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
        "phase79CheckpointDigest": p79_cp_digest,
        "phase79ChainDigest": reconstructed,
        "phase79ReplayDigest": replay,
        "phase80ResultDigest": p80_result_digest,
        "reconstructedContinuityDigest": reconstructed_continuity,
        "phase80CheckpointResultDigest": (
            p80_cp.get("resultDigest")
            if "p80_cp" in locals()
            else None
        ),
        "resultDigest": digest(result),
    }

    BASE.mkdir(parents=True, exist_ok=True)

    P81.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    P81_CP.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"STATE: {result['state']}")
    print(f"READY: {result['readiness']['ready']}")
    print(f"VALID: {result['verification']['valid']}")
    print(f"CHECKPOINT: {result['verification']['checkpoint']}")
    print(
        "PHASE80 RESULT DIGEST: "
        f"{result['verification']['phase80ResultDigest']}"
    )
    print(
        "RECONSTRUCTED CONTINUITY DIGEST: "
        f"{result['verification']['reconstructedContinuityDigest']}"
    )
    print(f"ERROR COUNT: {len(errors)}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
