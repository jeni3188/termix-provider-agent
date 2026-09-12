#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

SRC = ROOT / "src" / "aacp-phase80-checkpoint-continuity-verify.py"

P79 = BASE / "phase79-deterministic-replay.json"
P79_CP = BASE / "phase79-deterministic-replay-checkpoint.json"


def run():
    return subprocess.run(
        ["python3", str(SRC)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def mutate(path, mutation):
    original = path.read_text(encoding="utf-8")

    try:
        obj = json.loads(original)
        mutation(obj)

        path.write_text(
            json.dumps(obj, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        proc = run()

        return (
            proc.returncode != 0
            and "VALID: False" in proc.stdout
        )
    finally:
        path.write_text(original, encoding="utf-8")


def main():
    # R1 baseline
    proc = run()

    if (
        proc.returncode == 0
        and "STATE: VERIFIED_READ_ONLY" in proc.stdout
        and "VALID: True" in proc.stdout
        and "CHECKPOINT: VERIFIED" in proc.stdout
    ):
        print("R1 baseline: PASS")
    else:
        print("R1 baseline: FAIL")
        print(proc.stdout)
        print(proc.stderr)
        return 1

    # R2 mutate Phase79 output.
    if mutate(
        P79,
        lambda obj: obj.__setitem__("state", "TAMPERED"),
    ):
        print("R2 Phase79 output mutation: PASS")
    else:
        print("R2 Phase79 output mutation: FAIL")
        return 1

    # R3 mutate Phase79 replay digest.
    if mutate(
        P79,
        lambda obj: obj["verification"].__setitem__(
            "reconstructedChainDigest",
            "tampered",
        ),
    ):
        print("R3 Phase79 replay digest mutation: PASS")
    else:
        print("R3 Phase79 replay digest mutation: FAIL")
        return 1

    # R4 mutate Phase79 checkpoint.
    if mutate(
        P79_CP,
        lambda obj: obj.__setitem__(
            "chainDigest",
            "tampered",
        ),
    ):
        print("R4 Phase79 checkpoint mutation: PASS")
    else:
        print("R4 Phase79 checkpoint mutation: FAIL")
        return 1

    # R5 mutate Phase79 checkpoint continuity field.
    if mutate(
        P79_CP,
        lambda obj: obj.__setitem__(
            "replayStable",
            False,
        ),
    ):
        print("R5 Phase79 checkpoint replay mutation: PASS")
    else:
        print("R5 Phase79 checkpoint replay mutation: FAIL")
        return 1

    # R6 Phase79 checkpoint result digest mutation.
    # mutate() executes the verifier and restores the original file.
    if mutate(
        P79_CP,
        lambda obj: obj.__setitem__("resultDigest", "tampered"),
    ):
        print("R6 Phase79 checkpoint result digest mutation: PASS")
    else:
        print("R6 Phase79 checkpoint result digest mutation: FAIL")
        return 1

    # R7 baseline restoration.
    proc = run()

    if proc.returncode == 0 and "VALID: True" in proc.stdout:
        print("R7 restore baseline: PASS")
    else:
        print("R7 restore baseline: FAIL")
        return 1

    print("REGRESSION: 7/7 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
