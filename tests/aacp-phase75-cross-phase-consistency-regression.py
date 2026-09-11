from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

P65 = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify.json"
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

SOURCE = ROOT / "src/aacp-phase75-cross-phase-consistency-verify.py"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run():
    return subprocess.run(
        ["python3", str(SOURCE)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def assert_valid():
    r = run()
    if r.returncode != 0:
        raise AssertionError(
            "baseline failed:\n" + r.stdout + "\n" + r.stderr
        )


def assert_invalid():
    r = run()
    if r.returncode == 0:
        raise AssertionError(
            "mutation unexpectedly passed:\n" + r.stdout
        )


def mutate(path, mutator):
    original = path.read_text(encoding="utf-8")
    try:
        value = load(path)
        mutator(value)
        save(path, value)
        assert_invalid()
    finally:
        path.write_text(original, encoding="utf-8")


def main():
    assert_valid()
    print("R1 baseline: PASS")

    mutate(P65, lambda x: x.__setitem__(
        "type", "MUTATED_PHASE65_TYPE"
    ))
    print("R2 Phase65 type mutation: PASS")

    mutate(P65, lambda x: x.__setitem__(
        "executionAuthorized", True
    ))
    print("R3 Phase65 execution authorization mutation: PASS")

    mutate(P65, lambda x: x["readiness"].__setitem__(
        "observations", 99
    ))
    print("R4 Phase65 observation mutation: PASS")

    mutate(P65, lambda x: x["verification"].__setitem__(
        "integrityDigest", "0" * 64
    ))
    print("R5 Phase65 integrity digest mutation: PASS")

    mutate(P74, lambda x: x.__setitem__(
        "type", "MUTATED_PHASE74_TYPE"
    ))
    print("R6 Phase74 type mutation: PASS")

    mutate(P74, lambda x: x.__setitem__(
        "executionAuthorized", True
    ))
    print("R7 Phase74 execution authorization mutation: PASS")

    mutate(P74, lambda x: x["readiness"].__setitem__(
        "observations", 99
    ))
    print("R8 Phase74 observation mutation: PASS")

    mutate(P74, lambda x: x["verification"].__setitem__(
        "continuityDigest", "0" * 64
    ))
    print("R9 Phase74 continuity digest mutation: PASS")

    mutate(P74_CP, lambda x: x.__setitem__(
        "phase65CheckpointDigest", "0" * 64
    ))
    print("R10 Phase74 checkpoint linkage mutation: PASS")

    assert_valid()
    print("RESTORE BASELINE: PASS")
    print("PHASE75 REGRESSION: 10/10 PASS")


if __name__ == "__main__":
    main()
