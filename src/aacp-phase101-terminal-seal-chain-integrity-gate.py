#!/usr/bin/env python3
"""Phase101: verify Phase100 terminal seal continuity, fail-closed and read-only."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PHASE100_SOURCE = (
    ROOT / "src" / "aacp-phase100-terminal-seal-continuity-gate.py"
)
PHASE100_OUTPUT = (
    ROOT / "provider-output" / "aacp-observer"
    / "phase100-terminal-seal-continuity-gate.json"
)
PHASE100_CHECKPOINT = (
    ROOT / "provider-output" / "aacp-observer"
    / "phase100-terminal-seal-continuity-gate-checkpoint.json"
)

OUTPUT = (
    ROOT / "provider-output" / "aacp-observer"
    / "phase101-terminal-seal-chain-integrity-gate.json"
)
CHECKPOINT = (
    ROOT / "provider-output" / "aacp-observer"
    / "phase101-terminal-seal-chain-integrity-gate-checkpoint.json"
)

EXPECTED_PHASE100_SOURCE = (
    "9d09c9a83f19168e99c755666321850151f95e93df0b939fad4bf4ba8dbdc068"
)
EXPECTED_PHASE100_ARTIFACT = (
    "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71"
)

SAFETY_FIELDS = (
    "executionAuthorized",
    "networkAccess",
    "walletPresent",
    "signingEnabled",
    "broadcastEnabled",
    "submissionEnabled",
)


class GateError(Exception):
    """A required integrity or safety invariant failed."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes(path):
    try:
        return path.read_bytes()
    except OSError as exc:
        raise GateError(f"Cannot read required file: {path.name}: {exc}") from exc


def load_json_bytes(data, label):
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateError(f"Invalid JSON in {label}") from exc
    if not isinstance(value, dict):
        raise GateError(f"{label} must contain a JSON object")
    return value


def require(condition, message):
    if not condition:
        raise GateError(message)


def main():
    try:
        source_bytes = read_bytes(PHASE100_SOURCE)
        output_bytes = read_bytes(PHASE100_OUTPUT)
        checkpoint_bytes = read_bytes(PHASE100_CHECKPOINT)

        source_sha = sha256_bytes(source_bytes)
        output_sha = sha256_bytes(output_bytes)
        checkpoint_sha = sha256_bytes(checkpoint_bytes)

        require(
            source_sha == EXPECTED_PHASE100_SOURCE,
            "Phase100 source SHA-256 mismatch",
        )
        require(
            output_sha == EXPECTED_PHASE100_ARTIFACT,
            "Phase100 output SHA-256 mismatch",
        )
        require(
            checkpoint_sha == EXPECTED_PHASE100_ARTIFACT,
            "Phase100 checkpoint SHA-256 mismatch",
        )
        require(
            output_bytes == checkpoint_bytes,
            "Phase100 output/checkpoint are not byte-identical",
        )

        previous = load_json_bytes(output_bytes, "Phase100 output")
        checkpoint = load_json_bytes(checkpoint_bytes, "Phase100 checkpoint")

        require(previous == checkpoint, "Phase100 JSON objects differ")
        require(
            previous.get("state") == "VERIFIED_READ_ONLY",
            "Phase100 state is not VERIFIED_READ_ONLY",
        )
        require(previous.get("ready") is True, "Phase100 ready flag is not true")
        require(previous.get("valid") is True, "Phase100 valid flag is not true")
        require(
            previous.get("checkpoint") == "VERIFIED",
            "Phase100 checkpoint status is not VERIFIED",
        )
        require(
            previous.get("previous_phase") == 99,
            "Phase100 previous_phase anchor mismatch",
        )
        require(
            previous.get("phase99_output_checkpoint_identical") is True,
            "Phase100 Phase99 byte-identity assertion failed",
        )

        for field in SAFETY_FIELDS:
            require(previous.get(field) is False, f"{field} invariant violated")

        require(
            previous.get("error_count") == 0,
            "Phase100 error_count is not zero",
        )

        result = {
            "state": "VERIFIED_READ_ONLY",
            "ready": True,
            "valid": True,
            "checkpoint": "VERIFIED",
            "previous_phase": 100,
            "phase100_source_sha256": source_sha,
            "phase100_output_sha256": output_sha,
            "phase100_checkpoint_sha256": checkpoint_sha,
            "phase100_output_checkpoint_identical": True,
            "executionAuthorized": False,
            "networkAccess": False,
            "walletPresent": False,
            "signingEnabled": False,
            "broadcastEnabled": False,
            "submissionEnabled": False,
            "error_count": 0,
        }

        serialized = (
            json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n"
        ).encode("utf-8")

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(serialized)
        CHECKPOINT.write_bytes(serialized)

        print("STATE: VERIFIED_READ_ONLY")
        print("READY: True")
        print("VALID: True")
        print("CHECKPOINT: VERIFIED")
        print("PREVIOUS PHASE: 100")
        print(f"PHASE100 SOURCE SHA256: {source_sha}")
        print(f"PHASE100 OUTPUT SHA256: {output_sha}")
        print(f"PHASE100 CHECKPOINT SHA256: {checkpoint_sha}")
        print("PHASE100 OUTPUT/CHECKPOINT: BYTE_IDENTICAL")
        print("EXECUTION AUTHORIZED: False")
        print("NETWORK ACCESS: False")
        print("WALLET PRESENT: False")
        print("SIGNING ENABLED: False")
        print("BROADCAST ENABLED: False")
        print("SUBMISSION ENABLED: False")
        print("ERROR COUNT: 0")
        return 0

    except GateError as exc:
        print(f"STATE: REJECTED_READ_ONLY\nERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"STATE: REJECTED_READ_ONLY\nERROR: I/O failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
