#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "aacp-phase110-terminal-seal-phase109-lineage-audit.py"
OUTDIR = ROOT / "provider-output" / "aacp-observer"
OUTPUT = OUTDIR / "phase110-terminal-seal-phase109-lineage-audit.json"
CHECKPOINT = OUTDIR / "phase110-terminal-seal-phase109-lineage-audit-checkpoint.json"

PHASE109_OUTPUT = OUTDIR / "phase109-terminal-seal-phase108-lineage-audit.json"
PHASE109_CHECKPOINT = OUTDIR / "phase109-terminal-seal-phase108-lineage-audit-checkpoint.json"
PHASE109_SOURCE = ROOT / "src" / "aacp-phase109-terminal-seal-phase108-lineage-audit.py"
PHASE109_TEST = ROOT / "tests" / "aacp-phase109-terminal-seal-phase108-lineage-audit-regression.py"

EXPECTED = {
    "phase109_source": "2e642fd02d050faf4bafbf7f4df48abf15df24502c75f9436246e61e60b60fc9",
    "phase109_output": "ab0a1fa9254214679fadde5426a4e4f66721a89f4ee4754003e017613358989e",
    "phase109_test": "9ea59a8f4c0ac4d7ea540c61d5a8f832d1de57aba24940ac3eac64f864212c32",
}
SAFETY_FIELDS = (
    "executionAuthorized",
    "networkAccess",
    "walletPresent",
    "signingEnabled",
    "broadcastEnabled",
    "submissionEnabled",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def run_gate(expect_success):
    result = subprocess.run(
        [sys.executable, str(SOURCE)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if expect_success and result.returncode != 0:
        raise AssertionError(f"Expected gate PASS, got {result.returncode}:\n{result.stdout}")
    if not expect_success and result.returncode == 0:
        raise AssertionError(f"Expected gate rejection, but it passed:\n{result.stdout}")
    return result.stdout


def verify_phase110_artifacts():
    output_bytes = OUTPUT.read_bytes()
    checkpoint_bytes = CHECKPOINT.read_bytes()
    assert output_bytes == checkpoint_bytes, "Phase110 output/checkpoint bytes differ"

    data = json.loads(output_bytes)
    assert data.get("phase") == 110, "Wrong phase number"
    assert data.get("previous_phase") == 109, "Wrong previous phase"
    assert data.get("gate") == "Terminal Seal Phase109 Lineage Audit", "Wrong gate label"
    assert data.get("state") == "VERIFIED_READ_ONLY", "Wrong state"
    assert data.get("ready") is True, "ready must be true"
    assert data.get("valid") is True, "valid must be true"
    assert data.get("checkpoint") == "VERIFIED", "checkpoint must be VERIFIED"
    assert data.get("error_count") == 0, "error_count must be zero"

    for field in SAFETY_FIELDS:
        assert data.get(field) is False, f"Safety field {field} must be false"

    assert data.get("phase100_to_109_lineage_verified") is True
    assert data.get("phase100_to_109_cross_artifact_consistency_verified") is True
    assert data.get("phase100_to_109_output_checkpoint_identity_verified") is True

    assert data.get("phase109_source_sha256") == EXPECTED["phase109_source"]
    assert data.get("phase109_output_sha256") == EXPECTED["phase109_output"]
    assert data.get("phase109_checkpoint_sha256") == EXPECTED["phase109_output"]
    assert data.get("phase109_regression_sha256") == EXPECTED["phase109_test"]
    return data


def main():
    for path in (SOURCE, PHASE109_SOURCE, PHASE109_TEST, PHASE109_OUTPUT, PHASE109_CHECKPOINT):
        assert path.is_file(), f"Required file missing: {path}"

    assert sha256(PHASE109_SOURCE.read_bytes()) == EXPECTED["phase109_source"]
    assert sha256(PHASE109_OUTPUT.read_bytes()) == EXPECTED["phase109_output"]
    assert sha256(PHASE109_TEST.read_bytes()) == EXPECTED["phase109_test"]
    assert PHASE109_OUTPUT.read_bytes() == PHASE109_CHECKPOINT.read_bytes()

    first_output = run_gate(expect_success=True)
    assert "PHASE110_GATE=PASS" in first_output
    first_data = verify_phase110_artifacts()

    original = PHASE109_OUTPUT.read_bytes()
    try:
        PHASE109_OUTPUT.write_bytes(original + b"\nPHASE110_REGRESSION_TAMPER\n")
        rejected_output = run_gate(expect_success=False)
        assert "PHASE110_GATE=FAIL" in rejected_output
    finally:
        PHASE109_OUTPUT.write_bytes(original)

    assert PHASE109_OUTPUT.read_bytes() == original, "Phase109 output was not restored"
    assert PHASE109_CHECKPOINT.read_bytes() == original, "Phase109 checkpoint changed"

    final_output = run_gate(expect_success=True)
    assert "PHASE110_GATE=PASS" in final_output
    final_data = verify_phase110_artifacts()
    assert final_data == first_data, "Phase110 metadata changed after restoration"

    print("PHASE110_REGRESSION=PASS")
    print("baseline_gate=PASS")
    print("tampered_phase109_artifact=rejected")
    print("phase109_artifacts=restored_byte_identically")
    print("post_restore_gate=PASS")
    print("phase110_output_checkpoint=BYTE_IDENTICAL")
    print("safety_fields=ALL_FALSE")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"PHASE110_REGRESSION=FAIL: {exc}")
        sys.exit(1)
