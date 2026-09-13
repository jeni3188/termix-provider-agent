#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

PHASE98_SOURCE = ROOT / "src/aacp-phase98-terminal-manifest-gate.py"

PHASE98_OUTPUT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase98-terminal-manifest-gate.json"
)

PHASE98_CHECKPOINT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase98-terminal-manifest-gate-checkpoint.json"
)

OUTPUT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase99-terminal-seal-verification-gate.json"
)

CHECKPOINT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase99-terminal-seal-verification-gate-checkpoint.json"
)


EXPECTED_PHASE98_SOURCE = (
    "701830813f61ee114fb12c929eb8096c47ccd4def3632fc46e0fe166f11bf865"
)

EXPECTED_PHASE98_OUTPUT = (
    "74f7bb1c9a09baa040ab25c4d6d814ae9ac94f387992e23457c07ae5bb328424"
)

EXPECTED_PHASE98_CHECKPOINT = EXPECTED_PHASE98_OUTPUT

EXPECTED_TERMINAL_MANIFEST = (
    "da4dbffeb9c1f7eb4dc1fdc8b1a86b8e7ea0b3916d38d82c7e89fd658221e6e1"
)


def fail(message):
    print(f"ERROR: {message}")
    print("STATE: REJECTED_READ_ONLY")
    print("READY: False")
    print("VALID: False")
    sys.exit(1)


def require(condition, message):
    if not condition:
        fail(message)


def canonical_digest(obj):
    payload = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def source_digest(path):
    if not path.exists():
        fail(f"missing source: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    if not path.exists():
        fail(f"missing artifact: {path}")

    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        fail(f"invalid JSON artifact {path}: {exc}")


def build_phase98_manifest_from_artifact(phase98):
    return {
        "phase": 98,
        "name": "terminal_manifest_gate",
        "previous_phase": 97,
        "phase97_source_digest": phase98[
            "phase97_source_digest"
        ],
        "phase97_full_chain_integrity_digest": phase98[
            "phase97_full_chain_integrity_digest"
        ],
        "phase97_output_canonical_digest": phase98[
            "phase97_output_canonical_digest"
        ],
        "phase97_checkpoint_canonical_digest": phase98[
            "phase97_checkpoint_canonical_digest"
        ],
        "executionAuthorized": False,
        "networkAccess": False,
        "walletPresent": False,
        "signingEnabled": False,
        "broadcastEnabled": False,
        "submissionEnabled": False,
        "error_count": 0,
    }


def main():
    phase98_source = source_digest(PHASE98_SOURCE)

    require(
        phase98_source == EXPECTED_PHASE98_SOURCE,
        "Phase98 source digest mismatch",
    )

    output = load_json(PHASE98_OUTPUT)
    checkpoint = load_json(PHASE98_CHECKPOINT)

    output_digest = hashlib.sha256(
        PHASE98_OUTPUT.read_bytes()
    ).hexdigest()

    checkpoint_digest = hashlib.sha256(
        PHASE98_CHECKPOINT.read_bytes()
    ).hexdigest()

    require(
        output_digest == EXPECTED_PHASE98_OUTPUT,
        "Phase98 output byte digest mismatch",
    )

    require(
        checkpoint_digest == EXPECTED_PHASE98_CHECKPOINT,
        "Phase98 checkpoint byte digest mismatch",
    )

    require(
        output == checkpoint,
        "Phase98 output/checkpoint mismatch",
    )

    require(
        output.get("state") == "VERIFIED_READ_ONLY",
        "Phase98 state mismatch",
    )

    require(
        output.get("ready") is True,
        "Phase98 ready flag mismatch",
    )

    require(
        output.get("valid") is True,
        "Phase98 valid flag mismatch",
    )

    require(
        output.get("checkpoint") == "VERIFIED",
        "Phase98 checkpoint status mismatch",
    )

    require(
        output.get("previous_phase") == 97,
        "Phase98 previous phase mismatch",
    )

    safety_fields = {
        "executionAuthorized": False,
        "networkAccess": False,
        "walletPresent": False,
        "signingEnabled": False,
        "broadcastEnabled": False,
        "submissionEnabled": False,
    }

    for field, expected in safety_fields.items():
        require(
            output.get(field) is expected,
            f"Phase98 safety invariant mismatch: {field}",
        )

    require(
        output.get("error_count") == 0,
        "Phase98 error count must be zero",
    )

    require(
        len(output.get("terminal_manifest_digest", "")) == 64,
        "Phase98 terminal manifest digest length mismatch",
    )

    require(
        output["terminal_manifest_digest"]
        == EXPECTED_TERMINAL_MANIFEST,
        "Phase98 terminal manifest digest mismatch",
    )

    reconstructed_manifest = (
        build_phase98_manifest_from_artifact(output)
    )

    reconstructed_digest = canonical_digest(
        reconstructed_manifest
    )

    require(
        reconstructed_digest
        == output["terminal_manifest_digest"],
        "Phase98 terminal manifest reproduction mismatch",
    )

    result = {
        "state": "VERIFIED_READ_ONLY",
        "ready": True,
        "valid": True,
        "checkpoint": "VERIFIED",
        "previous_phase": 98,
        "phase98_source_digest": phase98_source,
        "phase98_output_sha256": output_digest,
        "phase98_checkpoint_sha256": checkpoint_digest,
        "phase98_terminal_manifest_digest": output[
            "terminal_manifest_digest"
        ],
        "phase98_manifest_reproduction_digest": reconstructed_digest,
        "executionAuthorized": False,
        "networkAccess": False,
        "walletPresent": False,
        "signingEnabled": False,
        "broadcastEnabled": False,
        "submissionEnabled": False,
        "error_count": 0,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")

    with CHECKPOINT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print("STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("PREVIOUS PHASE: 98")
    print(f"PHASE98 SOURCE DIGEST: {phase98_source}")
    print(f"PHASE98 OUTPUT SHA256: {output_digest}")
    print(f"PHASE98 CHECKPOINT SHA256: {checkpoint_digest}")
    print(
        "PHASE98 TERMINAL MANIFEST DIGEST: "
        f"{output['terminal_manifest_digest']}"
    )
    print(
        "PHASE98 MANIFEST REPRODUCTION DIGEST: "
        f"{reconstructed_digest}"
    )
    print("EXECUTION AUTHORIZED: False")
    print("NETWORK ACCESS: False")
    print("WALLET PRESENT: False")
    print("SIGNING ENABLED: False")
    print("BROADCAST ENABLED: False")
    print("SUBMISSION ENABLED: False")
    print("ERROR COUNT: 0")


if __name__ == "__main__":
    main()
