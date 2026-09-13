#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "src/aacp-phase98-terminal-manifest-gate.py"
OUT = ROOT / "provider-output" / "aacp-observer"
OUTPUT = OUT / "phase98-terminal-manifest-gate.json"
CHECKPOINT = OUT / "phase98-terminal-manifest-gate-checkpoint.json"

EXPECTED = {
    "state": "VERIFIED_READ_ONLY",
    "ready": True,
    "valid": True,
    "checkpoint": "VERIFIED",
    "previous_phase": 97,
    "executionAuthorized": False,
    "networkAccess": False,
    "walletPresent": False,
    "signingEnabled": False,
    "broadcastEnabled": False,
    "submissionEnabled": False,
    "error_count": 0,
}


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


def assert_true(condition, label):
    if not condition:
        raise AssertionError(label)
    print(f"PASS: {label}")


def main():
    result = run_gate()
    assert_true(result.returncode == 0, "R1 gate exits successfully")

    output = load(OUTPUT)
    checkpoint = load(CHECKPOINT)

    for key, value in EXPECTED.items():
        assert_true(output.get(key) == value, f"R2 {key}={value}")

    assert_true(
        output == checkpoint,
        "R3 output and checkpoint are identical",
    )

    assert_true(
        len(output.get("terminal_manifest_digest", "")) == 64,
        "R4 terminal manifest digest is SHA-256 length",
    )

    assert_true(
        output["phase97_source_digest"]
        == "77b270b467e3bef47e8dde9d82d785afb1a2934601c8d0764fda16145f1d54ae",
        "R5 Phase97 source anchor",
    )

    assert_true(
        output["phase97_full_chain_integrity_digest"]
        == "57f85081af9b8e592a961ec66c6bf387fc7098cf2a00296b1e167f217e5f4d74",
        "R6 Phase97 full-chain anchor",
    )

    phase97_output = (
        ROOT
        / "provider-output"
        / "aacp-observer"
        / "phase97-full-chain-integrity-gate.json"
    )
    phase97_checkpoint = (
        ROOT
        / "provider-output"
        / "aacp-observer"
        / "phase97-full-chain-integrity-gate-checkpoint.json"
    )

    original_phase97_output = phase97_output.read_text(encoding="utf-8")
    original_phase97_checkpoint = phase97_checkpoint.read_text(encoding="utf-8")

    try:
        mutated = json.loads(original_phase97_output)
        mutated["full_chain_integrity_digest"] = "0" * 64

        phase97_output.write_text(
            json.dumps(mutated, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        failed = run_gate()
        assert_true(
            failed.returncode != 0,
            "R7 Phase97 integrity mutation is rejected",
        )
    finally:
        phase97_output.write_text(
            original_phase97_output,
            encoding="utf-8",
        )
        phase97_checkpoint.write_text(
            original_phase97_checkpoint,
            encoding="utf-8",
        )

    result = run_gate()
    assert_true(
        result.returncode == 0,
        "R8 production state restored after mutation test",
    )

    restored = load(OUTPUT)
    restored_checkpoint = load(CHECKPOINT)

    assert_true(
        restored == restored_checkpoint,
        "R9 final output/checkpoint equality",
    )

    print("REGRESSION: 9/9 PASS")


if __name__ == "__main__":
    main()
