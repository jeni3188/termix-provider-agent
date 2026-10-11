#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "src" / "aacp-phase102-terminal-seal-lineage-verification-gate.py"
OUTDIR = ROOT / "provider-output" / "aacp-observer"
P100_OUTPUT = OUTDIR / "phase100-terminal-seal-continuity-gate.json"
P100_CHECKPOINT = OUTDIR / "phase100-terminal-seal-continuity-gate-checkpoint.json"
P101_OUTPUT = OUTDIR / "phase101-terminal-seal-chain-integrity-gate.json"
P101_CHECKPOINT = OUTDIR / "phase101-terminal-seal-chain-integrity-gate-checkpoint.json"
OUTPUT = OUTDIR / "phase102-terminal-seal-lineage-verification-gate.json"
CHECKPOINT = OUTDIR / "phase102-terminal-seal-lineage-verification-gate-checkpoint.json"

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


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    check(P100_OUTPUT.read_bytes() == P100_CHECKPOINT.read_bytes(),
          "R1 Phase100 artifacts byte-identical")
    check(P101_OUTPUT.read_bytes() == P101_CHECKPOINT.read_bytes(),
          "R2 Phase101 artifacts byte-identical")

    result = run_gate()
    check(result.returncode == 0, "R3 production gate succeeds")
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        print(f"RESULT: {checks - failures}/{checks} PASS")
        return 1

    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    check(data.get("phase") == 102 and data.get("previous_phase") == 101,
          "R4 Phase102 and previous-phase anchors")
    check(data.get("state") == "VERIFIED_READ_ONLY" and data.get("checkpoint") == "VERIFIED",
          "R5 verified read-only state")
    check(data.get("ready") is True and data.get("valid") is True and data.get("error_count") == 0,
          "R6 readiness, validity, and zero errors")
    check(data.get("lineage_100_to_101_verified") is True,
          "R7 lineage verification attested")
    safety = (
        "executionAuthorized", "networkAccess", "walletPresent",
        "signingEnabled", "broadcastEnabled", "submissionEnabled",
    )
    check(all(data.get(field) is False for field in safety),
          "R8 all safety invariants false")
    check(OUTPUT.read_bytes() == CHECKPOINT.read_bytes() and data == checkpoint,
          "R9 Phase102 output/checkpoint byte-identical")
    check(
        data.get("phase100_source_sha256") == "9d09c9a83f19168e99c755666321850151f95e93df0b939fad4bf4ba8dbdc068"
        and data.get("phase100_output_sha256") == "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71"
        and data.get("phase101_source_sha256") == "fe711c887239036f7d9d67c5cf9ab8a405a0be8f86e98ae7a9db6730bb7c0c4b"
        and data.get("phase101_output_sha256") == "0cb44297a08d238210fb19a851426d7248c56e1c8cc4132e6038898827807f19",
        "R10 immutable source and artifact anchors")
    check(all(len(data.get(field, "")) == 64 for field in (
        "phase100_source_sha256", "phase100_output_sha256",
        "phase100_checkpoint_sha256", "phase101_source_sha256",
        "phase101_output_sha256", "phase101_checkpoint_sha256",
    )), "R11 lineage digests are SHA-256 length")

    original = P101_OUTPUT.read_bytes()
    try:
        P101_OUTPUT.write_bytes(original + b"\n")
        rejected = run_gate()
        check(rejected.returncode != 0,
              "R12 modified Phase101 artifact rejected")
    finally:
        P101_OUTPUT.write_bytes(original)

    check(P101_OUTPUT.read_bytes() == P101_CHECKPOINT.read_bytes(),
          "R13 Phase101 artifact restored byte-for-byte")
    restored = run_gate()
    check(restored.returncode == 0,
          "R14 production gate succeeds after restoration")
    check(OUTPUT.read_bytes() == CHECKPOINT.read_bytes(),
          "R15 final Phase102 output/checkpoint byte-identical")

    print(f"RESULT: {checks - failures}/{checks} PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
