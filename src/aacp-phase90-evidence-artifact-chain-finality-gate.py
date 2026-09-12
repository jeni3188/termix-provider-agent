#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "provider-output" / "aacp-observer"

PHASE = 90
PREVIOUS_PHASE = 89

EXPECTED_PHASE89_SOURCE_DIGEST = (
    "d4f0efc352c204cd7074ff1050082cf90a6816baa3fa5ee0a29eda0cf9b453f0"
)

PHASE89_SOURCE = (
    ROOT / "src" / "aacp-phase89-evidence-artifact-integrity-continuity-gate.py"
)

PHASE89_OUTPUT = (
    OUT / "phase89-evidence-artifact-integrity-continuity-gate.json"
)

PHASE89_CHECKPOINT = (
    OUT / "phase89-evidence-artifact-integrity-continuity-gate-checkpoint.json"
)

SAFETY_FLAGS = (
    "executionAuthorized",
    "networkAccess",
    "walletPresent",
    "signingEnabled",
    "broadcastEnabled",
    "submissionEnabled",
)


def fail(message):
    print(f"ERROR: {message}")
    print("STATE: REJECTED_READ_ONLY")
    print("READY: False")
    print("VALID: False")
    print("CHECKPOINT: REJECTED")
    sys.exit(1)


def check(condition, message):
    if not condition:
        fail(message)


def load_json(path):
    check(path.exists(), f"Missing artifact: {path.name}")

    try:
        return json.loads(path.read_text())
    except Exception as exc:
        fail(f"Invalid JSON: {path.name}: {exc}")


def sha256_file(path):
    check(path.exists(), f"Missing source: {path}")

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def canonical_digest(data):
    payload = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()

    return hashlib.sha256(payload).hexdigest()


def main():
    output = load_json(PHASE89_OUTPUT)
    checkpoint = load_json(PHASE89_CHECKPOINT)

    source_digest = sha256_file(PHASE89_SOURCE)

    check(
        source_digest == EXPECTED_PHASE89_SOURCE_DIGEST,
        "Phase89 source digest mismatch",
    )

    check(
        str(output.get("phase")) == str(PREVIOUS_PHASE),
        "Phase89 output phase mismatch",
    )

    check(
        str(checkpoint.get("phase")) == str(PREVIOUS_PHASE),
        "Phase89 checkpoint phase mismatch",
    )

    check(
        output.get("previous_phase") == 88,
        "Phase89 output previous_phase mismatch",
    )

    check(
        checkpoint.get("previous_phase") == 88,
        "Phase89 checkpoint previous_phase mismatch",
    )

    check(
        output.get("state") == "VERIFIED_READ_ONLY",
        "Phase89 output state mismatch",
    )

    check(
        checkpoint.get("state") == "VERIFIED_READ_ONLY",
        "Phase89 checkpoint state mismatch",
    )

    check(
        output.get("ready") is True,
        "Phase89 output ready mismatch",
    )

    check(
        checkpoint.get("ready") is True,
        "Phase89 checkpoint ready mismatch",
    )

    check(
        output.get("valid") is True,
        "Phase89 output valid mismatch",
    )

    check(
        checkpoint.get("valid") is True,
        "Phase89 checkpoint valid mismatch",
    )

    check(
        output.get("checkpoint") == "VERIFIED",
        "Phase89 output checkpoint mismatch",
    )

    check(
        checkpoint.get("checkpoint") == "VERIFIED",
        "Phase89 checkpoint checkpoint mismatch",
    )

    check(
        output.get("error_count") == 0,
        "Phase89 output error_count mismatch",
    )

    check(
        checkpoint.get("error_count") == 0,
        "Phase89 checkpoint error_count mismatch",
    )

    for flag in SAFETY_FLAGS:
        check(
            output.get(flag) is False,
            f"Phase89 output safety flag enabled: {flag}",
        )

        check(
            checkpoint.get(flag) is False,
            f"Phase89 checkpoint safety flag enabled: {flag}",
        )

    continuity = output.get("continuity_digest")

    check(
        isinstance(continuity, str) and len(continuity) == 64,
        "Phase89 continuity digest invalid",
    )

    check(
        checkpoint.get("continuity_digest") == continuity,
        "Phase89 continuity digest mismatch",
    )

    output_digest = canonical_digest(output)
    checkpoint_digest = canonical_digest(checkpoint)

    evidence = {
        "phase": PHASE,
        "previous_phase": PREVIOUS_PHASE,
        "previous_source_digest": source_digest,
        "phase89_continuity_digest": continuity,
        "phase89_output_canonical_digest": output_digest,
        "phase89_checkpoint_canonical_digest": checkpoint_digest,
        "state": "VERIFIED_READ_ONLY",
        "ready": True,
        "valid": True,
        "checkpoint": "VERIFIED",
        "error_count": 0,
        "executionAuthorized": False,
        "networkAccess": False,
        "walletPresent": False,
        "signingEnabled": False,
        "broadcastEnabled": False,
        "submissionEnabled": False,
    }

    finality_digest = canonical_digest(evidence)

    evidence["finality_digest"] = finality_digest

    OUT.mkdir(parents=True, exist_ok=True)

    output_path = (
        OUT / "phase90-evidence-artifact-chain-finality-gate.json"
    )

    checkpoint_path = (
        OUT / "phase90-evidence-artifact-chain-finality-gate-checkpoint.json"
    )

    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    )

    checkpoint_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    )

    print("STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("PREVIOUS PHASE: 89")
    print(f"PHASE89 SOURCE DIGEST: {source_digest}")
    print(f"PHASE89 CONTINUITY DIGEST: {continuity}")
    print(f"PHASE89 OUTPUT CANONICAL DIGEST: {output_digest}")
    print(f"PHASE89 CHECKPOINT CANONICAL DIGEST: {checkpoint_digest}")
    print(f"FINALITY DIGEST: {finality_digest}")
    print("EXECUTION AUTHORIZED: False")
    print("NETWORK ACCESS: False")
    print("WALLET PRESENT: False")
    print("SIGNING ENABLED: False")
    print("BROADCAST ENABLED: False")
    print("SUBMISSION ENABLED: False")
    print("ERROR COUNT: 0")


if __name__ == "__main__":
    main()
