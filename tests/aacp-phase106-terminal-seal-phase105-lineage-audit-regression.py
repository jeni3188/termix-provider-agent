#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "src/aacp-phase106-terminal-seal-phase105-lineage-audit.py"
OUTDIR = ROOT / "provider-output/aacp-observer"
OUTPUT = OUTDIR / "phase106-terminal-seal-phase105-lineage-audit.json"
CHECKPOINT = OUTDIR / "phase106-terminal-seal-phase105-lineage-audit-checkpoint.json"
P105_OUTPUT = OUTDIR / "phase105-terminal-seal-phase104-lineage-audit.json"
P105_CHECKPOINT = OUTDIR / "phase105-terminal-seal-phase104-lineage-audit-checkpoint.json"
P105_SOURCE = ROOT / "src/aacp-phase105-terminal-seal-phase104-lineage-audit.py"
P105_TEST = ROOT / "tests/aacp-phase105-terminal-seal-phase104-lineage-audit-regression.py"

SAFETY_FIELDS = (
    "executionAuthorized", "networkAccess", "walletPresent",
    "signingEnabled", "broadcastEnabled", "submissionEnabled",
)

checks = 0
failures = 0


def check(condition, label):
    global checks, failures
    checks += 1
    print(f'{"PASS" if condition else "FAIL"}: R{checks} {label}')
    if not condition:
        failures += 1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_gate():
    return subprocess.run(
        [sys.executable, str(GATE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def main():
    original = P105_OUTPUT.read_bytes()
    original_checkpoint = P105_CHECKPOINT.read_bytes()

    check(original == original_checkpoint,
          "Phase105 artifacts byte-identical")

    run = run_gate()
    check(run.returncode == 0, "Phase106 production gate succeeds")
    if run.returncode != 0:
        print(run.stdout)
        print(run.stderr, file=sys.stderr)
        return 1

    result_bytes = OUTPUT.read_bytes()
    checkpoint_bytes = CHECKPOINT.read_bytes()
    result = json.loads(result_bytes)

    check(
        result.get("phase") == 106 and result.get("previous_phase") == 105,
        "Phase106 and previous-phase anchors",
    )
    check(
        result.get("state") == "VERIFIED_READ_ONLY"
        and result.get("checkpoint") == "VERIFIED",
        "Read-only verified state",
    )
    check(
        result.get("ready") is True and result.get("valid") is True
        and result.get("error_count") == 0,
        "Ready, valid, zero errors",
    )
    check(
        result.get("phase100_to_105_lineage_verified") is True
        and result.get("phase100_to_105_cross_artifact_consistency_verified") is True
        and result.get("phase100_to_105_output_checkpoint_identity_verified") is True,
        "Phase100-105 lineage and consistency attestations",
    )
    check(
        all(result.get(field) is False for field in SAFETY_FIELDS),
        "All safety invariants false",
    )
    check(
        result_bytes == checkpoint_bytes,
        "Phase106 output/checkpoint byte-identical",
    )

    hash_ok = True
    names = {
        100: "phase100-terminal-seal-continuity-gate",
        101: "phase101-terminal-seal-chain-integrity-gate",
        102: "phase102-terminal-seal-lineage-verification-gate",
        103: "phase103-terminal-seal-lineage-continuity-audit",
        104: "phase104-terminal-seal-cross-artifact-consistency-audit",
        105: "phase105-terminal-seal-phase104-lineage-audit",
    }
    for phase, base in names.items():
        paths = {
            "source": ROOT / "src" / f"aacp-phase{phase}-{base.split('-', 1)[1]}.py",
            "output": OUTDIR / f"{base}.json",
            "checkpoint": OUTDIR / f"{base}-checkpoint.json",
        }
        for kind, path in paths.items():
            key = f"phase{phase}_{kind}_sha256"
            if not path.is_file() or result.get(key) != sha(path):
                hash_ok = False
    check(hash_ok, "Phase100-105 source/output/checkpoint hashes match actual files")

    check(
        result.get("phase105_source_sha256") == sha(P105_SOURCE)
        and result.get("phase105_regression_sha256") == sha(P105_TEST),
        "Phase105 source and regression hash anchors",
    )

    try:
        P105_OUTPUT.write_bytes(original + b"\n")
        tampered = run_gate()
        check(tampered.returncode != 0,
              "Modified Phase105 output rejected")
    finally:
        P105_OUTPUT.write_bytes(original)

    check(
        P105_OUTPUT.read_bytes() == original
        and P105_CHECKPOINT.read_bytes() == original_checkpoint,
        "Phase105 artifacts restored byte-for-byte",
    )

    restored = run_gate()
    check(restored.returncode == 0,
          "Production gate succeeds after restoration")
    if restored.returncode != 0:
        print(restored.stdout)
        print(restored.stderr, file=sys.stderr)

    check(
        OUTPUT.read_bytes() == CHECKPOINT.read_bytes(),
        "Final Phase106 output/checkpoint byte-identical",
    )

    print(f"RESULT: {checks - failures}/{checks} PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
