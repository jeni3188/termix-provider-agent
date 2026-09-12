from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
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

SOURCE = ROOT / "src/aacp-phase77-provenance-verify.py"


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


def assert_baseline():
    result = run()
    if result.returncode != 0:
        raise AssertionError(
            "baseline failed:\n"
            + result.stdout
            + "\n"
            + result.stderr
        )


def assert_failed():
    result = run()
    if result.returncode == 0:
        raise AssertionError(
            "mutation unexpectedly passed:\n"
            + result.stdout
        )


def mutate(path, mutator):
    original = path.read_text(encoding="utf-8")
    try:
        value = load(path)
        mutator(value)
        save(path, value)
        assert_failed()
    finally:
        path.write_text(original, encoding="utf-8")


def main():
    assert_baseline()
    print("R1 baseline: PASS")

    mutate(
        P65,
        lambda x: x.__setitem__(
            "type",
            "MUTATED_PHASE65_TYPE",
        ),
    )
    print("R2 Phase65 provenance mutation: PASS")

    mutate(
        P65_CP,
        lambda x: x.__setitem__(
            "integrityDigest",
            "0" * 64,
        ),
    )
    print("R3 Phase65 checkpoint mutation: PASS")

    mutate(
        P74,
        lambda x: x.__setitem__(
            "type",
            "MUTATED_PHASE74_TYPE",
        ),
    )
    print("R4 Phase74 provenance mutation: PASS")

    mutate(
        P74_CP,
        lambda x: x.__setitem__(
            "integrityDigest",
            "0" * 64,
        ),
    )
    print("R5 Phase74 checkpoint mutation: PASS")

    mutate(
        P75,
        lambda x: x["verification"].__setitem__(
            "crossPhaseDigest",
            "0" * 64,
        ),
    )
    print("R6 Phase75 digest mutation: PASS")

    mutate(
        P75_CP,
        lambda x: x.__setitem__(
            "phase65CheckpointDigest",
            "0" * 64,
        ),
    )
    print("R7 Phase75 linkage mutation: PASS")

    mutate(
        P76,
        lambda x: x.__setitem__(
            "type",
            "MUTATED_PHASE76_TYPE",
        ),
    )
    print("R8 Phase76 provenance mutation: PASS")

    mutate(
        P76_CP,
        lambda x: x.__setitem__(
            "phase75OutputDigest",
            "0" * 64,
        ),
    )
    print("R9 Phase76 checkpoint linkage mutation: PASS")

    mutate(
        P76_CP,
        lambda x: x.__setitem__(
            "phase75CheckpointDigest",
            "0" * 64,
        ),
    )
    print("R10 Phase76 upstream checkpoint linkage mutation: PASS")

    assert_baseline()
    print("RESTORE BASELINE: PASS")
    print("PHASE77 REGRESSION: 10/10 PASS")


if __name__ == "__main__":
    main()
