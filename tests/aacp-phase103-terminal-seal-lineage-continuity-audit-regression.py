#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "src/aacp-phase103-terminal-seal-lineage-continuity-audit.py"
OUTDIR = ROOT / "provider-output/aacp-observer"
P102_OUTPUT = OUTDIR / "phase102-terminal-seal-lineage-verification-gate.json"
P102_CHECKPOINT = OUTDIR / "phase102-terminal-seal-lineage-verification-gate-checkpoint.json"
OUTPUT = OUTDIR / "phase103-terminal-seal-lineage-continuity-audit.json"
CHECKPOINT = OUTDIR / "phase103-terminal-seal-lineage-continuity-audit-checkpoint.json"

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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    check(P102_OUTPUT.read_bytes() == P102_CHECKPOINT.read_bytes(),
          "R1 Phase102 artifacts byte-identical")

    result = run_gate()
    check(result.returncode == 0, "R2 production gate succeeds")
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        print(f"RESULT: {checks - failures}/{checks} PASS")
        return 1

    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))

    check(data.get("phase") == 103 and data.get("previous_phase") == 102,
          "R3 Phase103 and previous-phase anchors")
    check(data.get("state") == "VERIFIED_READ_ONLY"
          and data.get("checkpoint") == "VERIFIED",
          "R4 read-only verified state")
    check(data.get("ready") is True and data.get("valid") is True
          and data.get("error_count") == 0,
          "R5 ready, valid, zero errors")
    check(data.get("lineage_100_to_102_verified") is True,
          "R6 complete lineage attested")

    safety = (
        "executionAuthorized", "networkAccess", "walletPresent",
        "signingEnabled", "broadcastEnabled", "submissionEnabled",
    )
    check(all(data.get(field) is False for field in safety),
          "R7 all safety invariants false")

    check(OUTPUT.read_bytes() == CHECKPOINT.read_bytes()
          and data == checkpoint,
          "R8 Phase103 output/checkpoint byte-identical")

    expected = {
        "phase100_source_sha256": "9d09c9a83f19168e99c755666321850151f95e93df0b939fad4bf4ba8dbdc068",
        "phase100_output_sha256": "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71",
        "phase101_source_sha256": "fe711c887239036f7d9d67c5cf9ab8a405a0be8f86e98ae7a9db6730bb7c0c4b",
        "phase101_output_sha256": "0cb44297a08d238210fb19a851426d7248c56e1c8cc4132e6038898827807f19",
        "phase102_source_sha256": "c65b37cd80a5db0e044666cfe88038dfbe353e5477f67ad1fb588f39abc8bb28",
        "phase102_regression_sha256": "b035f6c744283e45bc264856547e5720aa25f4ebea2dd2eb7fb951a7b2538f96",
        "phase102_output_sha256": "982511f968a4599be5df89bd22b8e6c76a59190db68b3fe594ec093e06f510fe",
        "phase102_checkpoint_sha256": "982511f968a4599be5df89bd22b8e6c76a59190db68b3fe594ec093e06f510fe",
    }
    check(all(data.get(key) == value for key, value in expected.items()),
          "R9 locked Phase100-102 hash anchors")

    check(all(len(data.get(key, "")) == 64 for key in expected),
          "R10 lineage digest fields are SHA-256 length")

    original = P102_OUTPUT.read_bytes()
    try:
        P102_OUTPUT.write_bytes(original + b"\n")
        rejected = run_gate()
        check(rejected.returncode != 0,
              "R11 modified Phase102 artifact rejected")
    finally:
        P102_OUTPUT.write_bytes(original)

    check(P102_OUTPUT.read_bytes() == P102_CHECKPOINT.read_bytes()
          and sha(P102_OUTPUT) == expected["phase102_output_sha256"],
          "R12 Phase102 artifact restored byte-for-byte")

    restored = run_gate()
    check(restored.returncode == 0,
          "R13 production gate succeeds after restoration")
    check(OUTPUT.read_bytes() == CHECKPOINT.read_bytes(),
          "R14 final Phase103 output/checkpoint byte-identical")

    print(f"RESULT: {checks - failures}/{checks} PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
