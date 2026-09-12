#!/usr/bin/env python3

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / "src" / "aacp-phase86-attestation-integrity-gate.py"
OUT = BASE / "provider-output" / "aacp-observer"

P85 = OUT / "phase85-attestation-stability.json"
P85_CP = OUT / "phase85-attestation-stability-checkpoint.json"


def run_case(p85, p85_cp, expected):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fake_out = root / "provider-output" / "aacp-observer"
        fake_out.mkdir(parents=True)

        shutil.copy(SRC, root / "phase86.py")
        (fake_out / "phase85-attestation-stability.json").write_text(
            json.dumps(p85, indent=2) + "\n"
        )
        (fake_out / "phase85-attestation-stability-checkpoint.json").write_text(
            json.dumps(p85_cp, indent=2) + "\n"
        )

        # Redirect source BASE calculation to temporary workspace.
        source = (root / "phase86.py").read_text()
        source = source.replace(
            'BASE = Path(__file__).resolve().parents[1]',
            f'BASE = Path("{root}")',
        )
        (root / "phase86.py").write_text(source)

        proc = subprocess.run(
            ["python3", str(root / "phase86.py")],
            capture_output=True,
            text=True,
        )

        passed = (proc.returncode == 0) == expected
        if not passed:
            print(proc.stdout)
            print(proc.stderr)
            raise AssertionError("unexpected Phase86 verifier result")


def main():
    baseline = json.loads(P85.read_text())
    baseline_cp = json.loads(P85_CP.read_text())

    run_case(
        json.loads(json.dumps(baseline)),
        json.loads(json.dumps(baseline_cp)),
        True,
    )
    print("R1 baseline: PASS")

    mutated = json.loads(json.dumps(baseline))
    mutated["valid"] = False
    run_case(mutated, json.loads(json.dumps(baseline_cp)), False)
    print("R2 Phase85 validity mutation: PASS")

    mutated = json.loads(json.dumps(baseline_cp))
    mutated["executionAuthorized"] = True
    run_case(json.loads(json.dumps(baseline)), mutated, False)
    print("R3 execution authorization mutation: PASS")

    mutated = json.loads(json.dumps(baseline))
    mutated["safety"]["networkAccess"] = True
    run_case(mutated, json.loads(json.dumps(baseline_cp)), False)
    print("R4 safety mutation: PASS")

    mutated = json.loads(json.dumps(baseline_cp))
    mutated["firstAttestationDigest"] = "0" * 64
    run_case(json.loads(json.dumps(baseline)), mutated, False)
    print("R5 attestation continuity mutation: PASS")

    run_case(
        json.loads(json.dumps(baseline)),
        json.loads(json.dumps(baseline_cp)),
        True,
    )
    print("R6 restore baseline: PASS")

    print("REGRESSION: 6/6 PASS")


if __name__ == "__main__":
    main()
