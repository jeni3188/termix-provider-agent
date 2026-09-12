#!/usr/bin/env python3

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/aacp-phase85-attestation-stability-verify.py"

BASE = ROOT / "provider-output" / "aacp-observer"

P84_OUTPUT = BASE / "phase84-finality-seal-attestation.json"
P84_CHECKPOINT = BASE / "phase84-finality-seal-attestation-checkpoint.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_case(p84, p84_cp, expect_success):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        observer = root / "provider-output" / "aacp-observer"
        observer.mkdir(parents=True)

        (observer / "phase84-finality-seal-attestation.json").write_text(
            json.dumps(p84),
            encoding="utf-8",
        )

        (observer / "phase84-finality-seal-attestation-checkpoint.json").write_text(
            json.dumps(p84_cp),
            encoding="utf-8",
        )

        proc = subprocess.run(
            ["python3", str(SOURCE)],
            cwd=root,
            capture_output=True,
            text=True,
        )

        if expect_success:
            assert proc.returncode == 0, proc.stdout + proc.stderr
        else:
            assert proc.returncode != 0, proc.stdout + proc.stderr


def main():
    baseline = load(P84_OUTPUT)
    baseline_cp = load(P84_CHECKPOINT)

    # R1: genuine baseline must pass.
    run_case(
        json.loads(json.dumps(baseline)),
        json.loads(json.dumps(baseline_cp)),
        True,
    )
    print("R1 baseline: PASS")

    # R2: Phase84 validity mutation must fail closed.
    mutated = json.loads(json.dumps(baseline))
    mutated["valid"] = False

    run_case(
        mutated,
        json.loads(json.dumps(baseline_cp)),
        False,
    )
    print("R2 Phase84 validity mutation: PASS")

    # R3: checkpoint attestation digest mutation must fail closed.
    mutated_cp = json.loads(json.dumps(baseline_cp))
    mutated_cp["attestationDigest"] = "0" * 64

    run_case(
        json.loads(json.dumps(baseline)),
        mutated_cp,
        False,
    )
    print("R3 attestation digest mutation: PASS")

    # R4: safety mutation must fail closed.
    mutated = json.loads(json.dumps(baseline))
    mutated["safety"]["networkAccess"] = True

    run_case(
        mutated,
        json.loads(json.dumps(baseline_cp)),
        False,
    )
    print("R4 safety mutation: PASS")

    # R5: source attestation material mutation must fail closed.
    mutated = json.loads(json.dumps(baseline))
    mutated["verification"]["phase83OutputDigest"] = "0" * 64

    run_case(
        mutated,
        json.loads(json.dumps(baseline_cp)),
        False,
    )
    print("R5 source attestation material mutation: PASS")

    # R6: restored canonical baseline must pass again.
    run_case(
        json.loads(json.dumps(baseline)),
        json.loads(json.dumps(baseline_cp)),
        True,
    )
    print("R6 restore baseline: PASS")

    print("REGRESSION: 6/6 PASS")


if __name__ == "__main__":
    main()
