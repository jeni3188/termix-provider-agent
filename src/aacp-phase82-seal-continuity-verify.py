#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

P79 = BASE / "phase79-deterministic-replay.json"
P79_CP = BASE / "phase79-deterministic-replay-checkpoint.json"
P80 = BASE / "phase80-checkpoint-continuity.json"
P80_CP = BASE / "phase80-checkpoint-continuity-checkpoint.json"
P81 = BASE / "phase81-checkpoint-seal.json"
P81_CP = BASE / "phase81-checkpoint-seal-checkpoint.json"

OUT = BASE / "phase82-seal-continuity.json"
CP = BASE / "phase82-seal-continuity-checkpoint.json"

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "TAMPER_EVIDENT_CHECKPOINT_SEAL_CONTINUITY_VERIFY"
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
        p81 = load(P81)
        p81_cp = load(P81_CP)

        p79_ver = p79.get("verification", {})
        p80_ver = p80.get("verification", {})
        p81_ver = p81.get("verification", {})

        # ------------------------------------------------------------------
        # Phase80 integrity
        # ------------------------------------------------------------------

        if p80.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase80:state")

        if p80_ver.get("valid") is not True:
            errors.append("phase80:valid")

        if p80_ver.get("checkpoint") != "VERIFIED":
            errors.append("phase80:checkpoint")

        if p80.get("executionAuthorized") is not False:
            errors.append("phase80:executionAuthorized")

        if p80_cp.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase80:checkpointState")

        if p80_cp.get("executionAuthorized") is not False:
            errors.append("phase80:checkpointExecutionAuthorized")

        p80_digest = digest(p80)
        p80_cp_digest = digest(p80_cp)

        if p80_cp.get("resultDigest") != p80_digest:
            errors.append("phase80:checkpointResultDigest")

        # ------------------------------------------------------------------
        # Phase79 independent continuity reconstruction
        # ------------------------------------------------------------------

        p79_digest = digest(p79)
        p79_cp_digest = digest(p79_cp)

        reconstructed_chain = p79_ver.get("reconstructedChainDigest")
        replay_digest = p79_ver.get("firstChainDigest")
        replay_count = p79_ver.get("replayCount")

        continuity = {
            "phase79OutputDigest": p79_digest,
            "phase79CheckpointDigest": p79_cp_digest,
            "phase79ChainDigest": reconstructed_chain,
            "phase79ReplayDigest": replay_digest,
            "phase79ReplayCount": replay_count,
        }

        reconstructed_continuity = digest(continuity)

        # ------------------------------------------------------------------
        # Phase80 must agree with independent Phase79 reconstruction
        # ------------------------------------------------------------------

        if p80_ver.get("phase79OutputDigest") != p79_digest:
            errors.append("phase80:phase79OutputDigest")

        if p80_ver.get("phase79CheckpointDigest") != p79_cp_digest:
            errors.append("phase80:phase79CheckpointDigest")

        if p80_ver.get("phase79ChainDigest") != reconstructed_chain:
            errors.append("phase80:phase79ChainDigest")

        if p80_ver.get("phase79ReplayDigest") != replay_digest:
            errors.append("phase80:phase79ReplayDigest")

        if p80_ver.get("continuityDigest") != reconstructed_continuity:
            errors.append("phase80:continuityDigest")

        if p80_cp.get("continuityDigest") != reconstructed_continuity:
            errors.append("phase80:checkpointContinuityDigest")

        # ------------------------------------------------------------------
        # Phase81 integrity
        # ------------------------------------------------------------------

        if p81.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase81:state")

        if p81_ver.get("valid") is not True:
            errors.append("phase81:valid")

        if p81_ver.get("checkpoint") != "VERIFIED":
            errors.append("phase81:checkpoint")

        if p81.get("executionAuthorized") is not False:
            errors.append("phase81:executionAuthorized")

        if p81_cp.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase81:checkpointState")

        if p81_cp.get("executionAuthorized") is not False:
            errors.append("phase81:checkpointExecutionAuthorized")

        p81_digest = digest(p81)

        if p81_cp.get("resultDigest") != p81_digest:
            errors.append("phase81:checkpointResultDigest")

        # ------------------------------------------------------------------
        # Phase81 must agree with Phase80 and independent Phase79 reconstruction
        # ------------------------------------------------------------------

        if p81_ver.get("phase80ResultDigest") != p80_digest:
            errors.append("phase81:phase80ResultDigest")

        if p81_ver.get("phase80CheckpointResultDigest") != p80_cp.get(
            "resultDigest"
        ):
            errors.append("phase81:phase80CheckpointResultDigest")

        if p81_ver.get("phase79OutputDigest") != p79_digest:
            errors.append("phase81:phase79OutputDigest")

        if p81_ver.get("phase79CheckpointDigest") != p79_cp_digest:
            errors.append("phase81:phase79CheckpointDigest")

        if p81_ver.get("phase79ChainDigest") != reconstructed_chain:
            errors.append("phase81:phase79ChainDigest")

        if p81_ver.get("phase79ReplayDigest") != replay_digest:
            errors.append("phase81:phase79ReplayDigest")

        if p81_ver.get("reconstructedContinuityDigest") != (
            reconstructed_continuity
        ):
            errors.append("phase81:reconstructedContinuityDigest")

        if p81_cp.get("phase80ResultDigest") != p80_digest:
            errors.append("phase81:checkpointPhase80ResultDigest")

        if p81_cp.get("phase80CheckpointResultDigest") != p80_cp.get(
            "resultDigest"
        ):
            errors.append("phase81:checkpointPhase80CheckpointResultDigest")

        if p81_cp.get("reconstructedContinuityDigest") != (
            reconstructed_continuity
        ):
            errors.append("phase81:checkpointContinuityDigest")

        # ------------------------------------------------------------------
        # Safety / fail-closed
        # ------------------------------------------------------------------

        for name, obj in (
            ("phase80", p80),
            ("phase81", p81),
        ):
            if obj.get("executionAuthorized") is not False:
                errors.append(f"{name}:executionAuthorized")

            safety = obj.get("safety", {})

            for key in (
                "broadcastPerformed",
                "signingPerformed",
                "submissionPerformed",
            ):
                if safety.get(key) is not False:
                    errors.append(f"{name}:safety:{key}")

            # Preserve the native Phase80/81 sideEffects schema.
            # The field may be a structured evidence object rather than
            # a boolean. Its presence alone is not a side effect.
            if "sideEffects" not in obj:
                errors.append(f"{name}:sideEffectsMissing")

        valid = len(errors) == 0

        result = {
            "type": TYPE,
            "state": "VERIFIED_READ_ONLY" if valid else "REJECTED",
            "ready": valid,
            "valid": valid,
            "checkpoint": "VERIFIED" if valid else "REJECTED",
            "verification": {
                "phase79OutputDigest": p79_digest,
                "phase79CheckpointDigest": p79_cp_digest,
                "phase79ChainDigest": reconstructed_chain,
                "phase79ReplayDigest": replay_digest,
                "phase79ReplayCount": replay_count,
                "phase80OutputDigest": p80_digest,
                "phase80CheckpointDigest": p80_cp_digest,
                "phase80ResultDigest": p80_digest,
                "phase81OutputDigest": p81_digest,
                "reconstructedContinuityDigest": reconstructed_continuity,
                "errorCount": len(errors),
                "errors": errors,
            },
            "safety": {
                "walletAccess": False,
                "signing": False,
                "broadcast": False,
                "submission": False,
                "networkAccess": False,
                "sideEffects": False,
            },
        }

        result_digest = digest(result)

        checkpoint = {
            "type": TYPE,
            "state": result["state"],
            "executionAuthorized": False,
            "resultDigest": result_digest,
            "phase80ResultDigest": p80_digest,
            "phase80CheckpointResultDigest": p80_cp.get("resultDigest"),
            "phase81ResultDigest": p81_digest,
            "reconstructedContinuityDigest": reconstructed_continuity,
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
        print("PHASE80 RESULT DIGEST:", p80_digest)
        print("PHASE81 RESULT DIGEST:", p81_digest)
        print(
            "RECONSTRUCTED CONTINUITY DIGEST:",
            reconstructed_continuity,
        )
        print("ERROR COUNT:", len(errors))

        if errors:
            print("ERRORS:")
            for error in errors:
                print("-", error)

        return 0 if valid else 1

    except Exception as exc:
        print("STATE: REJECTED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: REJECTED")
        print("ERROR COUNT: 1")
        print("ERRORS:")
        print("-", f"fatal:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
