#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent

GATE = (
    ROOT / "src" / "aacp-phase100-terminal-seal-continuity-gate.py"
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

PHASE100_OUTPUT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase100-terminal-seal-continuity-gate.json"
)

PHASE100_CHECKPOINT = (
    ROOT
    / "provider-output"
    / "aacp-observer"
    / "phase100-terminal-seal-continuity-gate-checkpoint.json"
)


passed = 0
total = 0


def check(condition, label):
    global passed, total
    total += 1

    if condition:
        passed += 1
        print(f"PASS: {label}")
    else:
        print(f"FAIL: {label}")


def run_gate():
    return subprocess.run(
        [sys.executable, str(GATE)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def load(path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    original_output = PHASE99_OUTPUT.read_bytes()
    original_checkpoint = PHASE99_CHECKPOINT.read_bytes()

    try:
        result = run_gate()

        check(
            result.returncode == 0,
            "R1 production gate succeeds",
        )

        output = load(PHASE100_OUTPUT)
        checkpoint = load(PHASE100_CHECKPOINT)

        check(
            output["state"] == "VERIFIED_READ_ONLY",
            "R2 state verified",
        )

        check(
            output["ready"] is True
            and output["valid"] is True
            and output["checkpoint"] == "VERIFIED",
            "R3 readiness/validity/checkpoint verified",
        )

        check(
            output["previous_phase"] == 99,
            "R4 previous phase anchor verified",
        )

        check(
            output["phase99_output_checkpoint_identical"] is True,
            "R5 Phase99 byte-identity assertion verified",
        )

        check(
            output["executionAuthorized"] is False
            and output["networkAccess"] is False
            and output["walletPresent"] is False
            and output["signingEnabled"] is False
            and output["broadcastEnabled"] is False
            and output["submissionEnabled"] is False
            and output["error_count"] == 0,
            "R6 all safety invariants verified",
        )

        check(
            output == checkpoint,
            "R7 Phase100 output/checkpoint identical",
        )

        check(
            len(output["phase99_source_sha256"]) == 64
            and len(output["phase99_output_sha256"]) == 64
            and len(output["phase99_checkpoint_sha256"]) == 64,
            "R8 digest fields are SHA-256 length",
        )

        mutated = json.loads(original_output.decode("utf-8"))
        mutated["phase99_terminal_seal_digest_mutation"] = "0" * 64

        PHASE99_OUTPUT.write_text(
            json.dumps(mutated, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        mutation = run_gate()

        check(
            mutation.returncode != 0,
            "R9 Phase99 artifact mutation rejected",
        )

    finally:
        PHASE99_OUTPUT.write_bytes(original_output)
        PHASE99_CHECKPOINT.write_bytes(original_checkpoint)

    restored = run_gate()

    check(
        restored.returncode == 0,
        "R10 production gate succeeds after restoration",
    )

    restored_output = load(PHASE100_OUTPUT)
    restored_checkpoint = load(PHASE100_CHECKPOINT)

    check(
        restored_output == restored_checkpoint,
        "R11 final output/checkpoint equality restored",
    )

    print(f"RESULT: {passed}/{total} PASS")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
