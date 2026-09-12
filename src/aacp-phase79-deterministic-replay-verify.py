#!/usr/bin/env python3

import contextlib
import hashlib
import importlib.util
import io
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

P79 = BASE / "phase79-deterministic-replay.json"
P79_CP = BASE / "phase79-deterministic-replay-checkpoint.json"

PHASE78 = ROOT / "src" / "aacp-phase78-chain-integrity-verify.py"

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "DETERMINISTIC_REPLAY_STABILITY_VERIFY"
)


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_phase78():
    spec = importlib.util.spec_from_file_location(
        "aacp_phase78_chain_integrity_verify",
        PHASE78,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("phase78:import-spec-failed")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_phase78(module):
    stream = io.StringIO()

    with contextlib.redirect_stdout(stream):
        rc = module.main()

    output = stream.getvalue()

    chain_digest = None
    valid = None

    for line in output.splitlines():
        if line.startswith("CHAIN DIGEST: "):
            chain_digest = line.split(": ", 1)[1].strip()
        elif line.startswith("VALID: "):
            valid = line.split(": ", 1)[1].strip() == "True"

    return {
        "returnCode": rc,
        "valid": valid,
        "chainDigest": chain_digest,
        "stdoutDigest": digest(output),
    }


def main():
    errors = []

    try:
        module = load_phase78()

        replay1 = run_phase78(module)
        replay2 = run_phase78(module)

        if replay1["returnCode"] != 0:
            errors.append("replay1:returnCode")

        if replay2["returnCode"] != 0:
            errors.append("replay2:returnCode")

        if replay1["valid"] is not True:
            errors.append("replay1:valid")

        if replay2["valid"] is not True:
            errors.append("replay2:valid")

        if not replay1["chainDigest"]:
            errors.append("replay1:chainDigest")

        if not replay2["chainDigest"]:
            errors.append("replay2:chainDigest")

        if (
            replay1["chainDigest"]
            and replay2["chainDigest"]
            and replay1["chainDigest"] != replay2["chainDigest"]
        ):
            errors.append("replay:chainDigestMismatch")

        # Reconstruct the Phase78 canonical chain independently.
        (
            p65,
            p65_cp,
            p74,
            p74_cp,
            p75,
            p75_cp,
            p76,
            p76_cp,
            p77,
            p77_cp,
        ) = module.load_chain()

        p75_cross = p75.get("verification", {}).get(
            "crossPhaseDigest"
        )

        p77_ver = p77.get("verification", {})

        chain = {
            "phase65OutputDigest": module.digest(p65),
            "phase65CheckpointDigest": module.digest(p65_cp),
            "phase74OutputDigest": module.digest(p74),
            "phase74CheckpointDigest": module.digest(p74_cp),
            "phase75OutputDigest": module.digest(p75),
            "phase75CheckpointDigest": module.digest(p75_cp),
            "phase76OutputDigest": module.digest(p76),
            "phase76CheckpointDigest": module.digest(p76_cp),
            "phase77OutputDigest": module.digest(p77),
            "phase77CheckpointDigest": module.digest(p77_cp),
            "phase75CrossPhaseDigest": p75_cross,
            "phase76ReconstructedDigest": p76_cp.get(
                "reconstructedCrossPhaseDigest"
            ),
            "phase77ProvenanceDigest": p77_ver.get(
                "provenanceDigest"
            ),
        }

        reconstructed_digest = module.digest(chain)

        if (
            replay1["chainDigest"]
            and replay1["chainDigest"] != reconstructed_digest
        ):
            errors.append("replay1:reconstructionMismatch")

        if (
            replay2["chainDigest"]
            and replay2["chainDigest"] != reconstructed_digest
        ):
            errors.append("replay2:reconstructionMismatch")

    except Exception as exc:
        errors.append(f"exception:{exc}")

        replay1 = {}
        replay2 = {}
        reconstructed_digest = None

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
            "observations": 3,
            "requiredObservations": 3,
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
            "replayStable": not errors,
            "replayCount": 2,
            "firstChainDigest": replay1.get("chainDigest"),
            "secondChainDigest": replay2.get("chainDigest"),
            "reconstructedChainDigest": reconstructed_digest,
        },
        "errorCount": len(errors),
        "errors": errors,
    }

    checkpoint = {
        "version": 1,
        "type": TYPE,
        "state": result["state"],
        "executionAuthorized": False,
        "replayStable": result["verification"]["replayStable"],
        "replayCount": result["verification"]["replayCount"],
        "chainDigest": reconstructed_digest,
        "firstChainDigest": result["verification"]["firstChainDigest"],
        "secondChainDigest": result["verification"]["secondChainDigest"],
        "resultDigest": digest(result),
    }

    BASE.mkdir(parents=True, exist_ok=True)

    P79.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    P79_CP.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"STATE: {result['state']}")
    print(f"READY: {result['readiness']['ready']}")
    print(f"VALID: {result['verification']['valid']}")
    print(
        f"REPLAY STABLE: "
        f"{result['verification']['replayStable']}"
    )
    print(
        f"REPLAY COUNT: "
        f"{result['verification']['replayCount']}"
    )
    print(
        f"CHAIN DIGEST: "
        f"{result['verification']['reconstructedChainDigest']}"
    )
    print(f"ERROR COUNT: {len(errors)}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
