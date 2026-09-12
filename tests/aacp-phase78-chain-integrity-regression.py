#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "aacp-phase78-chain-integrity-verify.py"
BASE = ROOT / "provider-output" / "aacp-observer"

P65 = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify.json"
)

P65_CP = BASE / (
    "aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify-checkpoint.json"
)

P74 = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "phase74-determinism-integrity-history.json"
)

P74_CP = BASE / (
    "aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "phase74-determinism-integrity-history-checkpoint.json"
)

P75 = BASE / "phase75-cross-phase-consistency.json"
P75_CP = BASE / "phase75-cross-phase-consistency-checkpoint.json"

P76 = BASE / "phase76-evidence-reconstruction.json"
P76_CP = BASE / "phase76-evidence-reconstruction-checkpoint.json"

P77 = BASE / "phase77-provenance.json"
P77_CP = BASE / "phase77-provenance-checkpoint.json"


def run():
    result = subprocess.run(
        ["python3", str(SRC)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def assert_baseline(label):
    code, out, err = run()
    if code != 0:
        raise AssertionError(f"{label}: process exit {code}\n{out}\n{err}")

    required = [
        "STATE: VERIFIED_READ_ONLY",
        "SOURCE STATE: VERIFIED_READ_ONLY",
        "READY: True",
        "VALID: True",
        "CHECKPOINT: VERIFIED",
        "OBSERVATIONS: 3",
        "ERROR COUNT: 0",
    ]

    for marker in required:
        if marker not in out:
            raise AssertionError(
                f"{label}: missing {marker!r}\n{out}\n{err}"
            )


def mutate(path, mutation):
    original = path.read_text(encoding="utf-8")
    try:
        data = json.loads(original)
        mutation(data)
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        code, out, err = run()

        # Negative tests intentionally tamper evidence. The verifier may
        # return a non-zero process exit when rejecting the tampered chain.
        # That is expected; validate the semantic rejection instead.
        if "VALID: False" not in out:
            raise AssertionError(
                f"{path.name}: mutation was not rejected\n{out}\n{err}"
            )

        if "ERROR COUNT: 0" in out:
            raise AssertionError(
                f"{path.name}: mutation produced zero errors\n{out}\n{err}"
            )
    finally:
        path.write_text(original, encoding="utf-8")


def main():
    tests = [
        (
            "R1 baseline",
            None,
            lambda d: None,
        ),
        (
            "R2 Phase65 output",
            P65,
            lambda d: d.__setitem__("state", "TAMPERED"),
        ),
        (
            "R3 Phase65 checkpoint",
            P65_CP,
            lambda d: d.__setitem__("observationCount", 999),
        ),
        (
            "R4 Phase74 output",
            P74,
            lambda d: d.__setitem__("state", "TAMPERED"),
        ),
        (
            "R5 Phase74 checkpoint",
            P74_CP,
            lambda d: d.__setitem__("observationCount", 999),
        ),
        (
            "R6 Phase75 output",
            P75,
            lambda d: d.setdefault("verification", {}).__setitem__(
                "crossPhaseDigest", "tampered"
            ),
        ),
        (
            "R7 Phase75 checkpoint",
            P75_CP,
            lambda d: d.__setitem__("phase65CheckpointDigest", "tampered"),
        ),
        (
            "R8 Phase76 output",
            P76,
            lambda d: d.__setitem__("state", "TAMPERED"),
        ),
        (
            "R9 Phase76 checkpoint",
            P76_CP,
            lambda d: d.__setitem__(
                "reconstructedCrossPhaseDigest", "tampered"
            ),
        ),
        (
            "R10 Phase77 provenance",
            P77,
            lambda d: d.setdefault("verification", {}).__setitem__(
                "provenanceDigest", "tampered"
            ),
        ),
    ]

    passed = 0

    for label, path, mutation in tests:
        if path is None:
            assert_baseline(label)
        else:
            mutate(path, mutation)

        print(f"{label}: PASS")
        passed += 1

    assert_baseline("RESTORE BASELINE")
    print(f"REGRESSION: {passed}/{len(tests)} PASS")
    print("RESTORE BASELINE: PASS")


if __name__ == "__main__":
    main()
