#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "provider-output" / "aacp-observer"

PHASE = 91
PREVIOUS_PHASE = 90

EXPECTED_PHASE90_SOURCE_DIGEST = (
    "4620589389747124b1d0bd22c45133be9ea5f503625f732d008349e4fdd8f7a2"
)

PHASE90_SOURCE = (
    ROOT / "src" /
    "aacp-phase90-evidence-artifact-chain-finality-gate.py"
)

PHASE90_OUTPUT = (
    OUT / "phase90-evidence-artifact-chain-finality-gate.json"
)

PHASE90_CHECKPOINT = (
    OUT / "phase90-evidence-artifact-chain-finality-gate-checkpoint.json"
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
    output = load_json(PHASE90_OUTPUT)
    checkpoint = load_json(PHASE90_CHECKPOINT)

    source_digest = sha256_file(PHASE90_SOURCE)

    check(
        source_digest == EXPECTED_PHASE90_SOURCE_DIGEST,
        "Phase90 source digest mismatch",
    )

    # Phase identity
    check(
        str(output.get("phase")) == str(PREVIOUS_PHASE),
        "Phase90 output phase mismatch",
    )

    check(
        str(checkpoint.get("phase")) == str(PREVIOUS_PHASE),
        "Phase90 checkpoint phase mismatch",
    )

    check(
        output.get("previous_phase") == 89,
        "Phase90 output previous_phase mismatch",
    )

    check(
        checkpoint.get("previous_phase") == 89,
        "Phase90 checkpoint previous_phase mismatch",
    )

    # State integrity
    check(
        output.get("state") == "VERIFIED_READ_ONLY",
        "Phase90 output state mismatch",
    )

    check(
        checkpoint.get("state") == "VERIFIED_READ_ONLY",
        "Phase90 checkpoint state mismatch",
    )

    check(output.get("ready") is True, "Phase90 output ready mismatch")
    check(checkpoint.get("ready") is True, "Phase90 checkpoint ready mismatch")

    check(output.get("valid") is True, "Phase90 output valid mismatch")
    check(checkpoint.get("valid") is True, "Phase90 checkpoint valid mismatch")

    check(
        output.get("checkpoint") == "VERIFIED",
        "Phase90 output checkpoint mismatch",
    )

    check(
        checkpoint.get("checkpoint") == "VERIFIED",
        "Phase90 checkpoint checkpoint mismatch",
    )

    check(output.get("error_count") == 0, "Phase90 output error_count mismatch")
    check(
        checkpoint.get("error_count") == 0,
        "Phase90 checkpoint error_count mismatch",
    )

    # Safety invariants
    for flag in SAFETY_FLAGS:
        check(
            output.get(flag) is False,
            f"Phase90 output safety flag enabled: {flag}",
        )

        check(
            checkpoint.get(flag) is False,
            f"Phase90 checkpoint safety flag enabled: {flag}",
        )

    # Phase90 continuity/finality integrity
    continuity = output.get("phase89_continuity_digest")
    check(
        isinstance(continuity, str) and len(continuity) == 64,
        "Phase90 phase89_continuity_digest invalid",
    )

    check(
        checkpoint.get("phase89_continuity_digest") == continuity,
        "Phase90 continuity digest mismatch",
    )

    finality = output.get("finality_digest")
    check(
        isinstance(finality, str) and len(finality) == 64,
        "Phase90 finality digest invalid",
    )

    check(
        checkpoint.get("finality_digest") == finality,
        "Phase90 finality digest mismatch",
    )

    previous_source = output.get("previous_source_digest")
    check(
        isinstance(previous_source, str) and len(previous_source) == 64,
        "Phase90 previous_source_digest invalid",
    )

    check(
        checkpoint.get("previous_source_digest") == previous_source,
        "Phase90 previous_source_digest mismatch",
    )

    # Canonical artifact digests
    output_digest = canonical_digest(output)
    checkpoint_digest = canonical_digest(checkpoint)

    evidence = {
        "phase": PHASE,
        "previous_phase": PREVIOUS_PHASE,
        "previous_source_digest": source_digest,
        "phase90_finality_digest": finality,
        "phase90_phase89_continuity_digest": continuity,
        "phase90_output_canonical_digest": output_digest,
        "phase90_checkpoint_canonical_digest": checkpoint_digest,
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

    consistency_digest = canonical_digest(evidence)
    evidence["consistency_digest"] = consistency_digest

    OUT.mkdir(parents=True, exist_ok=True)

    output_path = (
        OUT /
        "phase91-evidence-artifact-chain-consistency-gate.json"
    )

    checkpoint_path = (
        OUT /
        "phase91-evidence-artifact-chain-consistency-gate-checkpoint.json"
    )

    payload = json.dumps(
        evidence,
        indent=2,
        sort_keys=True,
    ) + "\n"

    output_path.write_text(payload)
    checkpoint_path.write_text(payload)

    print("STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("PREVIOUS PHASE: 90")
    print(f"PHASE90 SOURCE DIGEST: {source_digest}")
    print(f"PHASE90 FINALITY DIGEST: {finality}")
    print(f"PHASE90 PHASE89 CONTINUITY DIGEST: {continuity}")
    print(f"PHASE90 OUTPUT CANONICAL DIGEST: {output_digest}")
    print(f"PHASE90 CHECKPOINT CANONICAL DIGEST: {checkpoint_digest}")
    print(f"CONSISTENCY DIGEST: {consistency_digest}")
    print("EXECUTION AUTHORIZED: False")
    print("NETWORK ACCESS: False")
    print("WALLET PRESENT: False")
    print("SIGNING ENABLED: False")
    print("BROADCAST ENABLED: False")
    print("SUBMISSION ENABLED: False")
    print("ERROR COUNT: 0")


if __name__ == "__main__":
    main()
