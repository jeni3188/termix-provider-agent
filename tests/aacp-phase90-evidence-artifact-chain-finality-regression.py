#!/usr/bin/env python3

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT / "src" /
    "aacp-phase90-evidence-artifact-chain-finality-gate.py"
)

PHASE89_SOURCE = (
    ROOT / "src" /
    "aacp-phase89-evidence-artifact-integrity-continuity-gate.py"
)

PHASE89_OUTPUT = (
    ROOT / "provider-output" / "aacp-observer" /
    "phase89-evidence-artifact-integrity-continuity-gate.json"
)

PHASE89_CHECKPOINT = (
    ROOT / "provider-output" / "aacp-observer" /
    "phase89-evidence-artifact-integrity-continuity-gate-checkpoint.json"
)


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase90_gate",
        SOURCE,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_case(module):
    buf = io.StringIO()

    try:
        with contextlib.redirect_stdout(buf):
            module.main()
    except SystemExit as exc:
        return exc.code, buf.getvalue()

    return 0, buf.getvalue()


def expect_pass(module):
    code, output = run_case(module)

    assert code == 0, output
    assert "STATE: VERIFIED_READ_ONLY" in output
    assert "READY: True" in output
    assert "VALID: True" in output
    assert "CHECKPOINT: VERIFIED" in output
    assert "EXECUTION AUTHORIZED: False" in output
    assert "NETWORK ACCESS: False" in output
    assert "WALLET PRESENT: False" in output
    assert "SIGNING ENABLED: False" in output
    assert "BROADCAST ENABLED: False" in output
    assert "SUBMISSION ENABLED: False" in output
    assert "ERROR COUNT: 0" in output


def expect_reject(module):
    code, output = run_case(module)

    assert code != 0, output
    assert "STATE: REJECTED_READ_ONLY" in output
    assert "READY: False" in output
    assert "VALID: False" in output
    assert "CHECKPOINT: REJECTED" in output


def main():
    actual_phase89_source_digest = sha256_file(PHASE89_SOURCE)

    with tempfile.TemporaryDirectory(prefix="phase90-regression-") as td:
        tmp = Path(td)

        tmp_output = tmp / PHASE89_OUTPUT.name
        tmp_checkpoint = tmp / PHASE89_CHECKPOINT.name

        shutil.copy2(PHASE89_OUTPUT, tmp_output)
        shutil.copy2(PHASE89_CHECKPOINT, tmp_checkpoint)

        module = load_module()

        module.OUT = tmp
        module.PHASE89_OUTPUT = tmp_output
        module.PHASE89_CHECKPOINT = tmp_checkpoint
        module.PHASE89_SOURCE = PHASE89_SOURCE
        module.EXPECTED_PHASE89_SOURCE_DIGEST = actual_phase89_source_digest

        baseline_output = json.loads(tmp_output.read_text())
        baseline_checkpoint = json.loads(tmp_checkpoint.read_text())

        # R1 baseline
        expect_pass(module)
        print("R1 baseline: PASS")

        # R2 continuity mutation
        mutated = dict(baseline_output)
        mutated["continuity_digest"] = "0" * 64
        tmp_output.write_text(json.dumps(mutated))
        expect_reject(module)
        print("R2 continuity mutation: PASS")
        tmp_output.write_text(json.dumps(baseline_output))

        # R3 phase mutation
        mutated = dict(baseline_output)
        mutated["phase"] = 88
        tmp_output.write_text(json.dumps(mutated))
        expect_reject(module)
        print("R3 phase mutation: PASS")
        tmp_output.write_text(json.dumps(baseline_output))

        # R4 previous_phase mutation
        mutated = dict(baseline_output)
        mutated["previous_phase"] = 87
        tmp_output.write_text(json.dumps(mutated))
        expect_reject(module)
        print("R4 previous phase mutation: PASS")
        tmp_output.write_text(json.dumps(baseline_output))

        # R5 source digest mismatch
        original_expected = module.EXPECTED_PHASE89_SOURCE_DIGEST
        module.EXPECTED_PHASE89_SOURCE_DIGEST = "f" * 64
        expect_reject(module)
        print("R5 source digest mutation: PASS")
        module.EXPECTED_PHASE89_SOURCE_DIGEST = original_expected

        # R6 execution authorization mutation
        mutated = dict(baseline_output)
        mutated["executionAuthorized"] = True
        tmp_output.write_text(json.dumps(mutated))
        expect_reject(module)
        print("R6 execution authorization mutation: PASS")
        tmp_output.write_text(json.dumps(baseline_output))

        # R7 network mutation
        mutated = dict(baseline_output)
        mutated["networkAccess"] = True
        tmp_output.write_text(json.dumps(mutated))
        expect_reject(module)
        print("R7 network mutation: PASS")
        tmp_output.write_text(json.dumps(baseline_output))

        # R8 wallet mutation
        mutated = dict(baseline_output)
        mutated["walletPresent"] = True
        tmp_output.write_text(json.dumps(mutated))
        expect_reject(module)
        print("R8 wallet mutation: PASS")
        tmp_output.write_text(json.dumps(baseline_output))

        # R9 state mutation
        mutated = dict(baseline_output)
        mutated["state"] = "EXECUTION_ENABLED"
        tmp_output.write_text(json.dumps(mutated))
        expect_reject(module)
        print("R9 state mutation: PASS")
        tmp_output.write_text(json.dumps(baseline_output))

        # R10 checkpoint continuity mutation
        mutated = dict(baseline_checkpoint)
        mutated["continuity_digest"] = "1" * 64
        tmp_checkpoint.write_text(json.dumps(mutated))
        expect_reject(module)
        print("R10 checkpoint continuity mutation: PASS")
        tmp_checkpoint.write_text(json.dumps(baseline_checkpoint))

        # R11 checkpoint phase mutation
        mutated = dict(baseline_checkpoint)
        mutated["phase"] = 88
        tmp_checkpoint.write_text(json.dumps(mutated))
        expect_reject(module)
        print("R11 checkpoint phase mutation: PASS")
        tmp_checkpoint.write_text(json.dumps(baseline_checkpoint))

        # R12 restore baseline
        tmp_output.write_text(json.dumps(baseline_output))
        tmp_checkpoint.write_text(json.dumps(baseline_checkpoint))
        expect_pass(module)
        print("R12 restore baseline: PASS")

    print("REGRESSION: 12/12 PASS")


if __name__ == "__main__":
    main()
