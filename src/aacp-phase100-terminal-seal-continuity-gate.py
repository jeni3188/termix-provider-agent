#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent

PHASE99_SOURCE = (
    ROOT / "src" / "aacp-phase99-terminal-seal-verification-gate.py"
)

PHASE99_OUTPUT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase99-terminal-seal-verification-gate.json"
)

PHASE99_CHECKPOINT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase99-terminal-seal-verification-gate-checkpoint.json"
)

OUTPUT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase100-terminal-seal-continuity-gate.json"
)

CHECKPOINT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase100-terminal-seal-continuity-gate-checkpoint.json"
)

EXPECTED_PHASE99_SOURCE = (
    "7d9f9bc01aa4294e020217ecc0599a67844a316158a0e87a122942f2c3ac05bb"
)

EXPECTED_PHASE99_OUTPUT = (
    "e9e7e7c6bd57c2e5bb4747fc448231ecc4cdecce3922ba1c7bb915e82569c902"
)

EXPECTED_PHASE99_CHECKPOINT = EXPECTED_PHASE99_OUTPUT


class GateError(Exception):
    pass


def fail(message):
    raise GateError(message)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def source_digest(path):
    return sha256_bytes(path.read_bytes())


def load_json(path):
    if not path.exists():
        fail(f"missing artifact: {path}")

    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON artifact {path}: {exc}")


def require(condition, message):
    if not condition:
        fail(message)


def main():
    try:
        require(
            PHASE99_SOURCE.exists(),
            "Phase99 source missing",
        )

        require(
            PHASE99_OUTPUT.exists(),
            "Phase99 output missing",
        )

        require(
            PHASE99_CHECKPOINT.exists(),
            "Phase99 checkpoint missing",
        )

        phase99_source_digest = source_digest(PHASE99_SOURCE)

        phase99_output_bytes = PHASE99_OUTPUT.read_bytes()
        phase99_checkpoint_bytes = PHASE99_CHECKPOINT.read_bytes()

        phase99_output_sha256 = sha256_bytes(phase99_output_bytes)
        phase99_checkpoint_sha256 = sha256_bytes(
            phase99_checkpoint_bytes
        )

        require(
            phase99_source_digest == EXPECTED_PHASE99_SOURCE,
            "Phase99 source digest mismatch",
        )

        require(
            phase99_output_sha256 == EXPECTED_PHASE99_OUTPUT,
            "Phase99 output SHA256 mismatch",
        )

        require(
            phase99_checkpoint_sha256 == EXPECTED_PHASE99_CHECKPOINT,
            "Phase99 checkpoint SHA256 mismatch",
        )

        require(
            phase99_output_bytes == phase99_checkpoint_bytes,
            "Phase99 output/checkpoint byte mismatch",
        )

        output = load_json(PHASE99_OUTPUT)
        checkpoint = load_json(PHASE99_CHECKPOINT)

        require(
            output == checkpoint,
            "Phase99 output/checkpoint semantic mismatch",
        )

        require(
            output.get("state") == "VERIFIED_READ_ONLY",
            "Phase99 state is not VERIFIED_READ_ONLY",
        )

        require(
            output.get("ready") is True,
            "Phase99 ready flag is not True",
        )

        require(
            output.get("valid") is True,
            "Phase99 valid flag is not True",
        )

        require(
            output.get("checkpoint") == "VERIFIED",
            "Phase99 checkpoint is not VERIFIED",
        )

        require(
            output.get("previous_phase") == 98,
            "Phase99 previous_phase anchor mismatch",
        )

        require(
            output.get("executionAuthorized") is False,
            "executionAuthorized invariant violated",
        )

        require(
            output.get("networkAccess") is False,
            "networkAccess invariant violated",
        )

        require(
            output.get("walletPresent") is False,
            "walletPresent invariant violated",
        )

        require(
            output.get("signingEnabled") is False,
            "signingEnabled invariant violated",
        )

        require(
            output.get("broadcastEnabled") is False,
            "broadcastEnabled invariant violated",
        )

        require(
            output.get("submissionEnabled") is False,
            "submissionEnabled invariant violated",
        )

        require(
            output.get("error_count") == 0,
            "Phase99 error_count is not zero",
        )

        result = {
            "state": "VERIFIED_READ_ONLY",
            "ready": True,
            "valid": True,
            "checkpoint": "VERIFIED",
            "previous_phase": 99,
            "phase99_source_sha256": phase99_source_digest,
            "phase99_output_sha256": phase99_output_sha256,
            "phase99_checkpoint_sha256": phase99_checkpoint_sha256,
            "phase99_output_checkpoint_identical": True,
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
        print("PREVIOUS PHASE: 99")
        print(f"PHASE99 SOURCE SHA256: {phase99_source_digest}")
        print(f"PHASE99 OUTPUT SHA256: {phase99_output_sha256}")
        print(f"PHASE99 CHECKPOINT SHA256: {phase99_checkpoint_sha256}")
        print("PHASE99 OUTPUT/CHECKPOINT: BYTE_IDENTICAL")
        print("EXECUTION AUTHORIZED: False")
        print("NETWORK ACCESS: False")
        print("WALLET PRESENT: False")
        print("SIGNING ENABLED: False")
        print("BROADCAST ENABLED: False")
        print("SUBMISSION ENABLED: False")
        print("ERROR COUNT: 0")

        return 0

    except (GateError, OSError) as exc:
        print("STATE: FAILED_READ_ONLY")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: FAILED")
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
