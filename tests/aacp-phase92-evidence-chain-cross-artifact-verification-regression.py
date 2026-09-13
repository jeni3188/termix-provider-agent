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
    "aacp-phase92-evidence-chain-cross-artifact-verification-gate.py"
)

PHASE91_SOURCE = (
    ROOT / "src" /
    "aacp-phase91-evidence-artifact-chain-consistency-gate.py"
)


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase92_gate",
        SOURCE,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, data):
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n"
    )


def run_module(module):
    stdout = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout):
            module.main()
        code = 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1

    return code, stdout.getvalue()


def expect_pass(module):
    code, output = run_module(module)
    assert code == 0, output
    assert "STATE: VERIFIED_READ_ONLY" in output
    assert "READY: True" in output
    assert "VALID: True" in output
    assert "CHECKPOINT: VERIFIED" in output


def expect_fail(module):
    code, output = run_module(module)
    assert code != 0, output
    assert "STATE: REJECTED_READ_ONLY" in output
    assert "READY: False" in output
    assert "VALID: False" in output
    assert "CHECKPOINT: REJECTED" in output


def main():
    real_source_digest = sha256_file(SOURCE)

    module = load_module()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        out = tmp_root / "aacp-observer"
        out.mkdir(parents=True)

        names = (
            "phase89-evidence-artifact-integrity-continuity-gate.json",
            "phase89-evidence-artifact-integrity-continuity-gate-checkpoint.json",
            "phase90-evidence-artifact-chain-finality-gate.json",
            "phase90-evidence-artifact-chain-finality-gate-checkpoint.json",
            "phase91-evidence-artifact-chain-consistency-gate.json",
            "phase91-evidence-artifact-chain-consistency-gate-checkpoint.json",
        )

        for name in names:
            shutil.copy2(
                ROOT / "provider-output" / "aacp-observer" / name,
                out / name,
            )

        module.OUT = out

        module.PHASE89_OUTPUT = (
            out /
            "phase89-evidence-artifact-integrity-continuity-gate.json"
        )
        module.PHASE89_CHECKPOINT = (
            out /
            "phase89-evidence-artifact-integrity-continuity-gate-checkpoint.json"
        )

        module.PHASE90_OUTPUT = (
            out /
            "phase90-evidence-artifact-chain-finality-gate.json"
        )
        module.PHASE90_CHECKPOINT = (
            out /
            "phase90-evidence-artifact-chain-finality-gate-checkpoint.json"
        )

        module.PHASE91_OUTPUT = (
            out /
            "phase91-evidence-artifact-chain-consistency-gate.json"
        )
        module.PHASE91_CHECKPOINT = (
            out /
            "phase91-evidence-artifact-chain-consistency-gate-checkpoint.json"
        )

        module.PHASE91_SOURCE = PHASE91_SOURCE
        module.EXPECTED_PHASE91_SOURCE_DIGEST = sha256_file(PHASE91_SOURCE)

        phase89_output = module.PHASE89_OUTPUT
        phase89_checkpoint = module.PHASE89_CHECKPOINT
        phase90_output = module.PHASE90_OUTPUT
        phase90_checkpoint = module.PHASE90_CHECKPOINT
        phase91_output = module.PHASE91_OUTPUT
        phase91_checkpoint = module.PHASE91_CHECKPOINT

        baseline = {
            path: json.loads(path.read_text())
            for path in (
                phase89_output,
                phase89_checkpoint,
                phase90_output,
                phase90_checkpoint,
                phase91_output,
                phase91_checkpoint,
            )
        }

        # R1 baseline
        expect_pass(module)
        print("R1 baseline: PASS")

        # R2 Phase89 continuity mutation
        data = json.loads(phase89_output.read_text())
        data["continuity_digest"] = "0" * 64
        write_json(phase89_output, data)
        expect_fail(module)
        write_json(phase89_output, baseline[phase89_output])
        print("R2 Phase89 continuity mutation: PASS")

        # R3 Phase90 continuity reference mutation
        data = json.loads(phase90_output.read_text())
        data["phase89_continuity_digest"] = "1" * 64
        write_json(phase90_output, data)
        expect_fail(module)
        write_json(phase90_output, baseline[phase90_output])
        print("R3 Phase90 continuity mutation: PASS")

        # R4 Phase90 finality mutation
        data = json.loads(phase90_output.read_text())
        data["finality_digest"] = "2" * 64
        write_json(phase90_output, data)
        expect_fail(module)
        write_json(phase90_output, baseline[phase90_output])
        print("R4 Phase90 finality mutation: PASS")

        # R5 Phase91 finality reference mutation
        data = json.loads(phase91_output.read_text())
        data["phase90_finality_digest"] = "3" * 64
        write_json(phase91_output, data)
        expect_fail(module)
        write_json(phase91_output, baseline[phase91_output])
        print("R5 Phase91 finality reference mutation: PASS")

        # R6 Phase91 Phase90 canonical digest mutation
        data = json.loads(phase91_output.read_text())
        data["phase90_output_canonical_digest"] = "4" * 64
        write_json(phase91_output, data)
        expect_fail(module)
        write_json(phase91_output, baseline[phase91_output])
        print("R6 Phase91 canonical digest mutation: PASS")

        # R7 Phase91 source anchor mutation
        module.EXPECTED_PHASE91_SOURCE_DIGEST = "f" * 64
        expect_fail(module)
        module.EXPECTED_PHASE91_SOURCE_DIGEST = sha256_file(PHASE91_SOURCE)
        print("R7 source digest mutation: PASS")

        # R8 execution authorization
        data = json.loads(phase91_output.read_text())
        data["executionAuthorized"] = True
        write_json(phase91_output, data)
        expect_fail(module)
        write_json(phase91_output, baseline[phase91_output])
        print("R8 execution authorization mutation: PASS")

        # R9 network access
        data = json.loads(phase91_output.read_text())
        data["networkAccess"] = True
        write_json(phase91_output, data)
        expect_fail(module)
        write_json(phase91_output, baseline[phase91_output])
        print("R9 network mutation: PASS")

        # R10 wallet
        data = json.loads(phase91_output.read_text())
        data["walletPresent"] = True
        write_json(phase91_output, data)
        expect_fail(module)
        write_json(phase91_output, baseline[phase91_output])
        print("R10 wallet mutation: PASS")

        # R11 state
        data = json.loads(phase91_output.read_text())
        data["state"] = "EXECUTION_ENABLED"
        write_json(phase91_output, data)
        expect_fail(module)
        write_json(phase91_output, baseline[phase91_output])
        print("R11 state mutation: PASS")

        # R12 Phase91 checkpoint cross-artifact mutation
        data = json.loads(phase91_checkpoint.read_text())
        data["phase90_finality_digest"] = "5" * 64
        write_json(phase91_checkpoint, data)
        expect_fail(module)
        write_json(phase91_checkpoint, baseline[phase91_checkpoint])
        print("R12 checkpoint cross-artifact mutation: PASS")

        # R13 restore baseline
        for path, data in baseline.items():
            write_json(path, data)

        expect_pass(module)
        print("R13 restore baseline: PASS")

    print("REGRESSION: 13/13 PASS")


if __name__ == "__main__":
    main()
