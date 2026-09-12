#!/usr/bin/env python3

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

P80 = BASE / "phase80-checkpoint-continuity.json"
P80_CP = BASE / "phase80-checkpoint-continuity-checkpoint.json"
P81 = BASE / "phase81-checkpoint-seal.json"
P81_CP = BASE / "phase81-checkpoint-seal-checkpoint.json"

SCRIPT = ROOT / "src" / "aacp-phase81-checkpoint-seal-verify.py"


def run():
    return subprocess.run(
        ["python3", str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def mutate(path, mutate_fn):
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        mutate_fn(data)
        path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result = run()
        return result.returncode != 0
    finally:
        shutil.move(backup, path)


def main():
    BASE.mkdir(parents=True, exist_ok=True)

    baseline = run()
    if baseline.returncode != 0:
        print("R1 baseline: FAIL")
        print(baseline.stdout)
        print(baseline.stderr)
        return 1
    print("R1 baseline: PASS")

    if mutate(
        P80,
        lambda x: x["verification"].__setitem__(
            "phase79ReplayDigest",
            "tampered-phase80-output",
        ),
    ):
        print("R2 Phase80 output mutation: PASS")
    else:
        print("R2 Phase80 output mutation: FAIL")
        return 1

    if mutate(
        P80_CP,
        lambda x: x.__setitem__(
            "phase79ChainDigest",
            "tampered-phase80-checkpoint",
        ),
    ):
        print("R3 Phase80 checkpoint mutation: PASS")
    else:
        print("R3 Phase80 checkpoint mutation: FAIL")
        return 1

    if mutate(
        P80_CP,
        lambda x: x.__setitem__(
            "resultDigest",
            "tampered-result-digest",
        ),
    ):
        print("R4 Phase80 resultDigest mutation: PASS")
    else:
        print("R4 Phase80 resultDigest mutation: FAIL")
        return 1

    if mutate(
        P80,
        lambda x: x.__setitem__(
            "executionAuthorized",
            True,
        ),
    ):
        print("R5 execution authorization mutation: PASS")
    else:
        print("R5 execution authorization mutation: FAIL")
        return 1

    if mutate(
        P80,
        lambda x: x["safety"].__setitem__(
            "broadcastPerformed",
            True,
        ),
    ):
        print("R6 safety mutation: PASS")
    else:
        print("R6 safety mutation: FAIL")
        return 1

    restored = run()
    if restored.returncode == 0:
        print("R7 restore baseline: PASS")
    else:
        print("R7 restore baseline: FAIL")
        print(restored.stdout)
        print(restored.stderr)
        return 1

    print("REGRESSION: 7/7 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
