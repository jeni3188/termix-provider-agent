#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

SOURCE = (
    ROOT
    / "src"
    / "aacp-phase99-terminal-seal-verification-gate.py"
)

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


def run_gate():
    return subprocess.run(
        [sys.executable, str(SOURCE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def load(path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def check(condition, label):
    if condition:
        print(f"PASS: {label}")
        return True

    print(f"FAIL: {label}")
    return False


def main():
    passed = 0
    total = 0

    def test(condition, label):
        nonlocal passed, total
        total += 1
        if check(condition, label):
            passed += 1

    original_output = PHASE98_OUTPUT.read_bytes()
    original_checkpoint = PHASE98_CHECKPOINT.read_bytes()

    try:
        r = run_gate()

        test(r.returncode == 0, "R1 production gate succeeds")

        output = load(PHASE99_OUTPUT)
        checkpoint = load(PHASE99_CHECKPOINT)

        test(
            output["state"] == "VERIFIED_READ_ONLY",
            "R2 state verified",
        )

        test(
            output["ready"] is True
            and output["valid"] is True
            and output["checkpoint"] == "VERIFIED",
            "R3 readiness/validity/checkpoint verified",
        )

        test(
            output["previous_phase"] == 98,
            "R4 previous phase anchor verified",
        )

        test(
            output["executionAuthorized"] is False
            and output["networkAccess"] is False
            and output["walletPresent"] is False
            and output["signingEnabled"] is False
            and output["broadcastEnabled"] is False
            and output["submissionEnabled"] is False
            and output["error_count"] == 0,
            "R5 all safety invariants verified",
        )

        test(
            output == checkpoint,
            "R6 output/checkpoint identical",
        )

        test(
            len(output["phase98_source_digest"]) == 64
            and len(output["phase98_output_sha256"]) == 64
            and len(output["phase98_checkpoint_sha256"]) == 64
            and len(output["phase98_terminal_manifest_digest"]) == 64
            and len(output["phase98_manifest_reproduction_digest"]) == 64,
            "R7 digest fields are valid SHA-256 lengths",
        )

        test(
            output["phase98_terminal_manifest_digest"]
            == output["phase98_manifest_reproduction_digest"],
            "R8 manifest reproduction matches Phase98 anchor",
        )

        mutated = json.loads(original_output.decode("utf-8"))
        mutated["terminal_manifest_digest"] = "0" * 64

        PHASE98_OUTPUT.write_text(
            json.dumps(mutated, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        r_mut = run_gate()

        test(
            r_mut.returncode != 0,
            "R9 terminal manifest mutation rejected",
        )

    finally:
        PHASE98_OUTPUT.write_bytes(original_output)
        PHASE98_CHECKPOINT.write_bytes(original_checkpoint)

        restored = run_gate()

        test(
            restored.returncode == 0,
            "R10 production gate succeeds after restoration",
        )

        if PHASE99_OUTPUT.exists() and PHASE99_CHECKPOINT.exists():
            restored_output = load(PHASE99_OUTPUT)
            restored_checkpoint = load(PHASE99_CHECKPOINT)

            test(
                restored_output == restored_checkpoint,
                "R11 final output/checkpoint equality restored",
            )

    print()
    print(f"RESULT: {passed}/{total} PASS")

    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
