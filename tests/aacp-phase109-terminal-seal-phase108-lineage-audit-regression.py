#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "src/aacp-phase109-terminal-seal-phase108-lineage-audit.py"
OUTDIR = ROOT / "provider-output/aacp-observer"
OUTPUT = OUTDIR / "phase109-terminal-seal-phase108-lineage-audit.json"
CHECKPOINT = OUTDIR / "phase109-terminal-seal-phase108-lineage-audit-checkpoint.json"
P108_OUTPUT = OUTDIR / "phase108-terminal-seal-phase107-lineage-audit.json"
P108_CHECKPOINT = OUTDIR / "phase108-terminal-seal-phase107-lineage-audit-checkpoint.json"
SAFETY = ("executionAuthorized", "networkAccess", "walletPresent",
          "signingEnabled", "broadcastEnabled", "submissionEnabled")

def check(ok, label):
    if not ok:
        raise AssertionError(label)
    print("PASS:", label)

def run_gate(expect_pass):
    p = subprocess.run([sys.executable, str(GATE)], cwd=ROOT,
                       capture_output=True, text=True, timeout=30)
    if (p.returncode == 0) != expect_pass:
        raise AssertionError(f"unexpected exit={p.returncode}\n{p.stdout}\n{p.stderr}")
    return p

def main():
    compile(GATE.read_text(), str(GATE), "exec")
    check(True, "Phase109 source compiles")
    p108 = P108_OUTPUT.read_bytes()
    c108 = P108_CHECKPOINT.read_bytes()
    check(p108 == c108, "Phase108 output/checkpoint initially identical")

    p = run_gate(True)
    check("PHASE109_GATE=PASS" in p.stdout, "Phase109 gate passes")
    raw = OUTPUT.read_bytes()
    check(raw == CHECKPOINT.read_bytes(), "Phase109 output/checkpoint identical")
    obj = json.loads(raw)
    check(obj.get("phase") == 109 and obj.get("previous_phase") == 108,
          "Phase109 phase metadata")
    check(obj.get("state") == "VERIFIED_READ_ONLY" and
          obj.get("ready") is True and obj.get("valid") is True,
          "Phase109 read-only status")
    check(obj.get("checkpoint") == "VERIFIED" and obj.get("error_count") == 0,
          "Phase109 checkpoint/error metadata")
    check(all(obj.get(k) is False for k in SAFETY), "all safety fields false")
    check(all(obj.get(k) is True for k in (
        "phase100_to_108_lineage_verified",
        "phase100_to_108_cross_artifact_consistency_verified",
        "phase100_to_108_output_checkpoint_identity_verified",
    )), "Phase100-108 attestations")
    check(obj.get("phase108_source_sha256") ==
          hashlib.sha256((ROOT / "src/aacp-phase108-terminal-seal-phase107-lineage-audit.py").read_bytes()).hexdigest(),
          "Phase108 source hash recorded")
    check(obj.get("phase108_output_sha256") == hashlib.sha256(p108).hexdigest() and
          obj.get("phase108_checkpoint_sha256") == hashlib.sha256(c108).hexdigest(),
          "Phase108 artifact hashes recorded")

    try:
        P108_OUTPUT.write_bytes(p108 + b"\n")
        p = run_gate(False)
        check("PHASE109_GATE=FAIL" in p.stderr, "tampered Phase108 output rejected")
    finally:
        P108_OUTPUT.write_bytes(p108)

    check(P108_OUTPUT.read_bytes() == p108 and
          P108_CHECKPOINT.read_bytes() == c108,
          "Phase108 artifacts restored byte-for-byte")
    run_gate(True)
    check(OUTPUT.read_bytes() == CHECKPOINT.read_bytes(),
          "final Phase109 output/checkpoint identity")
    print("PHASE109_REGRESSION=PASS")

if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, subprocess.SubprocessError,
            json.JSONDecodeError) as exc:
        print(f"PHASE109_REGRESSION=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
