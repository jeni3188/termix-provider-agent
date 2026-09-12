#!/usr/bin/env python3

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/aacp-phase88-evidence-artifact-integrity-gate.py"


def must(condition, message):
    if not condition:
        raise AssertionError(message)


def run_with_temp_artifacts(output_mutator=None, checkpoint_mutator=None):
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        out = tmp / "provider-output" / "aacp-observer"
        out.mkdir(parents=True)

        real_out = ROOT / "provider-output" / "aacp-observer"

        output_src = real_out / "phase87-evidence-chain-continuity-gate.json"
        checkpoint_src = (
            real_out
            / "phase87-evidence-chain-continuity-gate-checkpoint.json"
        )

        output = json.loads(output_src.read_text())
        checkpoint = json.loads(checkpoint_src.read_text())

        if output_mutator:
            output_mutator(output)

        if checkpoint_mutator:
            checkpoint_mutator(checkpoint)

        (out / output_src.name).write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n"
        )

        (out / checkpoint_src.name).write_text(
            json.dumps(checkpoint, indent=2, sort_keys=True) + "\n"
        )

        temp_source = tmp / "gate.py"
        source = SOURCE.read_text()

        source = source.replace(
            'ROOT = Path(__file__).resolve().parents[1]',
            f'ROOT = Path({str(tmp)!r})',
            1,
        )

        temp_source.write_text(source)

        return subprocess.run(
            ["python3", str(temp_source)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )


def main():
    r1 = run_with_temp_artifacts()
    must(r1.returncode == 0, "baseline failed")
    print("R1 baseline: PASS")

    r2 = run_with_temp_artifacts(
        output_mutator=lambda x: x.__setitem__(
            "continuity_digest",
            "tampered",
        )
    )
    must(r2.returncode != 0, "continuity digest mutation accepted")
    print("R2 continuity digest mutation: PASS")

    r3 = run_with_temp_artifacts(
        output_mutator=lambda x: x.__setitem__(
            "executionAuthorized",
            True,
        )
    )
    must(r3.returncode != 0, "execution authorization mutation accepted")
    print("R3 execution authorization mutation: PASS")

    r4 = run_with_temp_artifacts(
        output_mutator=lambda x: x.__setitem__(
            "networkAccess",
            True,
        )
    )
    must(r4.returncode != 0, "network mutation accepted")
    print("R4 network mutation: PASS")

    r5 = run_with_temp_artifacts(
        output_mutator=lambda x: x.__setitem__(
            "walletPresent",
            True,
        )
    )
    must(r5.returncode != 0, "wallet mutation accepted")
    print("R5 wallet mutation: PASS")

    r6 = run_with_temp_artifacts(
        checkpoint_mutator=lambda x: x.__setitem__(
            "checkpoint",
            "REJECTED",
        )
    )
    must(r6.returncode != 0, "checkpoint mutation accepted")
    print("R6 checkpoint mutation: PASS")

    r7 = run_with_temp_artifacts(
        checkpoint_mutator=lambda x: x.__setitem__(
            "valid",
            False,
        )
    )
    must(r7.returncode != 0, "validity mutation accepted")
    print("R7 validity mutation: PASS")

    r8 = run_with_temp_artifacts()
    must(r8.returncode == 0, "restore baseline failed")
    print("R8 restore baseline: PASS")

    r9 = run_with_temp_artifacts(
        output_mutator=lambda x: x.__setitem__(
            "phase",
            "999",
        )
    )
    must(r9.returncode != 0, "phase mutation accepted")
    print("R9 phase mutation: PASS")

    print("REGRESSION: 9/9 PASS")


if __name__ == "__main__":
    main()
