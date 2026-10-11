#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "src/aacp-phase104-terminal-seal-cross-artifact-consistency-audit.py"
OUTDIR = ROOT / "provider-output/aacp-observer"

OUTPUT = OUTDIR / "phase104-terminal-seal-cross-artifact-consistency-audit.json"
CHECKPOINT = OUTDIR / "phase104-terminal-seal-cross-artifact-consistency-audit-checkpoint.json"

P103_OUTPUT = OUTDIR / "phase103-terminal-seal-lineage-continuity-audit.json"
P103_CHECKPOINT = OUTDIR / "phase103-terminal-seal-lineage-continuity-audit-checkpoint.json"

PHASE_PATHS = {
    100: {
        "source": ROOT / "src/aacp-phase100-terminal-seal-continuity-gate.py",
        "output": OUTDIR / "phase100-terminal-seal-continuity-gate.json",
        "checkpoint": OUTDIR / "phase100-terminal-seal-continuity-gate-checkpoint.json",
    },
    101: {
        "source": ROOT / "src/aacp-phase101-terminal-seal-chain-integrity-gate.py",
        "output": OUTDIR / "phase101-terminal-seal-chain-integrity-gate.json",
        "checkpoint": OUTDIR / "phase101-terminal-seal-chain-integrity-gate-checkpoint.json",
    },
    102: {
        "source": ROOT / "src/aacp-phase102-terminal-seal-lineage-verification-gate.py",
        "output": OUTDIR / "phase102-terminal-seal-lineage-verification-gate.json",
        "checkpoint": OUTDIR / "phase102-terminal-seal-lineage-verification-gate-checkpoint.json",
    },
    103: {
        "source": ROOT / "src/aacp-phase103-terminal-seal-lineage-continuity-audit.py",
        "output": P103_OUTPUT,
        "checkpoint": P103_CHECKPOINT,
    },
}

SAFETY_FIELDS = (
    "executionAuthorized", "networkAccess", "walletPresent",
    "signingEnabled", "broadcastEnabled", "submissionEnabled",
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    check(P103_OUTPUT.read_bytes() == P103_CHECKPOINT.read_bytes(),
          "R1 Phase103 artifacts byte-identical")

    result = run_gate()
    check(result.returncode == 0, "R2 production gate succeeds")
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        print(f"RESULT: {checks - failures}/{checks} PASS")
        return 1

    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))

    check(data.get("phase") == 104 and data.get("previous_phase") == 103,
          "R3 Phase104 and previous-phase anchors")
    check(data.get("state") == "VERIFIED_READ_ONLY"
          and data.get("checkpoint") == "VERIFIED",
          "R4 read-only verified state")
    check(data.get("ready") is True and data.get("valid") is True
          and data.get("error_count") == 0,
          "R5 ready, valid, zero errors")
    check(data.get("phase100_to_103_cross_artifact_consistency_verified") is True
          and data.get("phase100_to_103_output_checkpoint_identity_verified") is True
          and data.get("phase100_to_103_lineage_verified") is True,
          "R6 cross-artifact consistency and lineage attested")
    check(all(data.get(field) is False for field in SAFETY_FIELDS),
          "R7 all safety invariants false")
    check(OUTPUT.read_bytes() == CHECKPOINT.read_bytes()
          and data == checkpoint,
          "R8 Phase104 output/checkpoint byte-identical")

    hash_fields_valid = True
    for phase, paths in PHASE_PATHS.items():
        for kind, path in paths.items():
            key = f"phase{phase}_{kind}_sha256"
            if data.get(key) != sha(path):
                hash_fields_valid = False
    check(hash_fields_valid,
          "R9 Phase100-103 source/output/checkpoint hashes match actual files")

    check(data.get("phase102_regression_sha256")
          == "b035f6c744283e45bc264856547e5720aa25f4ebea2dd2eb7fb951a7b2538f96"
          and data.get("phase103_regression_sha256")
          == "09091e9002d32babde85019e952ee6bcb1c820ef7fe420ffeb4776bc6769c7dd",
          "R10 Phase102-103 regression hash anchors")

    original = P103_OUTPUT.read_bytes()
    try:
        P103_OUTPUT.write_bytes(original + b"\n")
        rejected = run_gate()
        check(rejected.returncode != 0,
              "R11 modified Phase103 output rejected")
    finally:
        P103_OUTPUT.write_bytes(original)

    check(P103_OUTPUT.read_bytes() == P103_CHECKPOINT.read_bytes()
          and sha(P103_OUTPUT) == hashlib.sha256(original).hexdigest(),
          "R12 Phase103 output restored byte-for-byte")

    restored = run_gate()
    check(restored.returncode == 0,
          "R13 production gate succeeds after restoration")
    if restored.returncode != 0:
        print(restored.stdout, end="")
        print(restored.stderr, end="", file=sys.stderr)

    check(OUTPUT.read_bytes() == CHECKPOINT.read_bytes(),
          "R14 final Phase104 output/checkpoint byte-identical")

    print(f"RESULT: {checks - failures}/{checks} PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
