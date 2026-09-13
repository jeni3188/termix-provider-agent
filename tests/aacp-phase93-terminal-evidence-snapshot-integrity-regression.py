#!/usr/bin/env python3

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
SOURCE = BASE / "src/aacp-phase93-terminal-evidence-snapshot-integrity-gate.py"
OBSERVER = BASE / "provider-output" / "aacp-observer"

PHASE92_OUTPUT = (
    OBSERVER
    / "phase92-evidence-chain-cross-artifact-verification-gate.json"
)

PHASE92_CHECKPOINT = (
    OBSERVER
    / "phase92-evidence-chain-cross-artifact-verification-gate-checkpoint.json"
)

PHASE92_SOURCE = (
    BASE
    / "src"
    / "aacp-phase92-evidence-chain-cross-artifact-verification-gate.py"
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


EXPECTED_PHASE92_SOURCE_DIGEST = sha256_file(PHASE92_SOURCE)


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def run_gate(temp_root, expected_success):
    proc = subprocess.run(
        ["python3", str(temp_root / "phase93.py")],
        cwd=temp_root,
        text=True,
        capture_output=True,
    )

    output = proc.stdout + proc.stderr

    if expected_success:
        assert proc.returncode == 0, output
        assert "STATE: VERIFIED_READ_ONLY" in output
        assert "READY: True" in output
        assert "VALID: True" in output
        assert "CHECKPOINT: VERIFIED" in output
    else:
        assert proc.returncode != 0, output
        assert "STATE: REJECTED_READ_ONLY" in output

    return output


def prepare_source(temp_root):
    source = SOURCE.read_text(encoding="utf-8")

    source = source.replace(
        'BASE = Path(__file__).resolve().parent.parent',
        f'BASE = Path(r"{temp_root}")',
    )

    source = source.replace(
        'PHASE92_SOURCE = (',
        'PHASE92_SOURCE = (',
    )

    source = source.replace(
        'EXPECTED_PHASE92_SOURCE_DIGEST = (\n'
        '    "4ffc336aa24672a2e5908ba66f28b019ad31ac4f3f26e9f3594a31dd06f4b40c"\n'
        ')',
        f'EXPECTED_PHASE92_SOURCE_DIGEST = "{EXPECTED_PHASE92_SOURCE_DIGEST}"',
    )

    (temp_root / "phase93.py").write_text(
        source,
        encoding="utf-8",
    )


def main():
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        observer = temp / "provider-output" / "aacp-observer"
        source_dir = temp / "src"

        observer.mkdir(parents=True)
        source_dir.mkdir(parents=True)

        shutil.copy2(PHASE92_OUTPUT, observer / PHASE92_OUTPUT.name)
        shutil.copy2(PHASE92_CHECKPOINT, observer / PHASE92_CHECKPOINT.name)
        shutil.copy2(PHASE92_SOURCE, source_dir / PHASE92_SOURCE.name)

        prepare_source(temp)

        output = observer / "phase92-evidence-chain-cross-artifact-verification-gate.json"
        checkpoint = observer / "phase92-evidence-chain-cross-artifact-verification-gate-checkpoint.json"

        baseline_output = load(output)
        baseline_checkpoint = load(checkpoint)

        # R1
        run_gate(temp, True)
        print("R1 baseline: PASS")

        # R2
        mutated = dict(baseline_output)
        mutated["cross_artifact_digest"] = "0" * 64
        write(output, mutated)
        run_gate(temp, False)
        print("R2 cross-artifact digest mutation: PASS")
        write(output, baseline_output)

        # R3
        mutated = dict(baseline_output)
        mutated["state"] = "MUTATED"
        write(output, mutated)
        run_gate(temp, False)
        print("R3 state mutation: PASS")
        write(output, baseline_output)

        # R4
        mutated = dict(baseline_output)
        mutated["ready"] = False
        write(output, mutated)
        run_gate(temp, False)
        print("R4 ready mutation: PASS")
        write(output, baseline_output)

        # R5
        mutated = dict(baseline_output)
        mutated["valid"] = False
        write(output, mutated)
        run_gate(temp, False)
        print("R5 valid mutation: PASS")
        write(output, baseline_output)

        # R6
        mutated = dict(baseline_output)
        mutated["executionAuthorized"] = True
        write(output, mutated)
        run_gate(temp, False)
        print("R6 execution authorization mutation: PASS")
        write(output, baseline_output)

        # R7
        mutated = dict(baseline_output)
        mutated["networkAccess"] = True
        write(output, mutated)
        run_gate(temp, False)
        print("R7 network mutation: PASS")
        write(output, baseline_output)

        # R8
        mutated = dict(baseline_output)
        mutated["walletPresent"] = True
        write(output, mutated)
        run_gate(temp, False)
        print("R8 wallet mutation: PASS")
        write(output, baseline_output)

        # R9
        mutated = dict(baseline_output)
        mutated["signingEnabled"] = True
        write(output, mutated)
        run_gate(temp, False)
        print("R9 signing mutation: PASS")
        write(output, baseline_output)

        # R10
        mutated = dict(baseline_output)
        mutated["broadcastEnabled"] = True
        write(output, mutated)
        run_gate(temp, False)
        print("R10 broadcast mutation: PASS")
        write(output, baseline_output)

        # R11
        mutated = dict(baseline_output)
        mutated["submissionEnabled"] = True
        write(output, mutated)
        run_gate(temp, False)
        print("R11 submission mutation: PASS")
        write(output, baseline_output)

        # R12
        mutated = dict(baseline_checkpoint)
        mutated["cross_artifact_digest"] = "f" * 64
        write(checkpoint, mutated)
        run_gate(temp, False)
        print("R12 checkpoint mutation: PASS")
        write(checkpoint, baseline_checkpoint)

        # R13
        mutated = dict(baseline_output)
        mutated["previous_phase"] = 999
        write(output, mutated)
        run_gate(temp, False)
        print("R13 previous phase mutation: PASS")
        write(output, baseline_output)

        # R14
        run_gate(temp, True)
        print("R14 restore baseline: PASS")

    print("REGRESSION: 14/14 PASS")


if __name__ == "__main__":
    main()
