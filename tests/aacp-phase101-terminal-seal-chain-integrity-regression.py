#!/usr/bin/env python3
"""Regression tests for Phase101 terminal seal chain integrity."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "src" / "aacp-phase101-terminal-seal-chain-integrity-gate.py"

PHASE100_OUTPUT = (
    ROOT / "provider-output" / "aacp-observer"
    / "phase100-terminal-seal-continuity-gate.json"
)
PHASE100_CHECKPOINT = (
    ROOT / "provider-output" / "aacp-observer"
    / "phase100-terminal-seal-continuity-gate-checkpoint.json"
)
PHASE101_OUTPUT = (
    ROOT / "provider-output" / "aacp-observer"
    / "phase101-terminal-seal-chain-integrity-gate.json"
)
PHASE101_CHECKPOINT = (
    ROOT / "provider-output" / "aacp-observer"
    / "phase101-terminal-seal-chain-integrity-gate-checkpoint.json"
)

checks = 0
failures = 0


def check(condition, label):
    global checks, failures
    checks += 1
    if condition:
        print(f"PASS: {label}")
    else:
        failures += 1
        print(f"FAIL: {label}")


def run_gate():
    return subprocess.run(
        [sys.executable, str(GATE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def load(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main():
    original_output = PHASE100_OUTPUT.read_bytes()
    original_checkpoint = PHASE100_CHECKPOINT.read_bytes()

    try:
        check(
            original_output == original_checkpoint,
            "R1 Phase100 artifacts initially byte-identical",
        )

        proc = run_gate()
        check(proc.returncode == 0, "R2 production gate succeeds")
        check(
            "STATE: VERIFIED_READ_ONLY" in proc.stdout,
            "R3 state verified",
        )

        result = load(PHASE101_OUTPUT)
        checkpoint = load(PHASE101_CHECKPOINT)
        check(
            result.get("state") == "VERIFIED_READ_ONLY"
            and result.get("ready") is True
            and result.get("valid") is True
            and result.get("checkpoint") == "VERIFIED",
            "R4 readiness/validity/checkpoint verified",
        )
        check(result.get("previous_phase") == 100, "R5 previous phase anchor verified")

        check(
            result.get("phase100_source_sha256")
            == "9d09c9a83f19168e99c755666321850151f95e93df0b939fad4bf4ba8dbdc068"
            and result.get("phase100_output_sha256")
            == "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71"
            and result.get("phase100_checkpoint_sha256")
            == "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71",
            "R6 Phase100 source/artifact anchors verified",
        )

        safety_fields = (
            "executionAuthorized",
            "networkAccess",
            "walletPresent",
            "signingEnabled",
            "broadcastEnabled",
            "submissionEnabled",
        )
        check(
            all(result.get(field) is False for field in safety_fields)
            and result.get("error_count") == 0,
            "R7 all safety invariants verified",
        )
        check(
            PHASE101_OUTPUT.read_bytes() == PHASE101_CHECKPOINT.read_bytes()
            and result == checkpoint,
            "R8 Phase101 output/checkpoint identical",
        )
        check(
            all(
                isinstance(result.get(field), str)
                and len(result[field]) == 64
                and all(c in "0123456789abcdef" for c in result[field])
                for field in (
                    "phase100_source_sha256",
                    "phase100_output_sha256",
                    "phase100_checkpoint_sha256",
                )
            ),
            "R9 digest fields are SHA-256 format",
        )

        mutated = json.loads(original_output.decode("utf-8"))
        mutated["phase100_integrity_mutation"] = "tampered"
        PHASE100_OUTPUT.write_text(
            json.dumps(mutated, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

        rejected = run_gate()
        check(
            rejected.returncode != 0
            and "REJECTED_READ_ONLY" in rejected.stderr,
            "R10 Phase100 artifact mutation rejected",
        )

    finally:
        PHASE100_OUTPUT.write_bytes(original_output)
        PHASE100_CHECKPOINT.write_bytes(original_checkpoint)

    restored = run_gate()
    check(restored.returncode == 0, "R11 production gate succeeds after restoration")
    check(
        PHASE100_OUTPUT.read_bytes() == original_output
        and PHASE100_CHECKPOINT.read_bytes() == original_checkpoint,
        "R12 Phase100 artifacts restored byte-for-byte",
    )
    check(
        PHASE101_OUTPUT.read_bytes() == PHASE101_CHECKPOINT.read_bytes(),
        "R13 final Phase101 output/checkpoint equality restored",
    )

    print(f"RESULT: {checks - failures}/{checks} PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
