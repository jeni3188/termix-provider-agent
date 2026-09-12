#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path

BASE = Path("provider-output/aacp-observer")

P80 = BASE / "phase80-checkpoint-continuity.json"
P80_CP = BASE / "phase80-checkpoint-continuity-checkpoint.json"
P81 = BASE / "phase81-checkpoint-seal.json"
P81_CP = BASE / "phase81-checkpoint-seal-checkpoint.json"


def run():
    return subprocess.run(
        ["python3", "src/aacp-phase82-seal-continuity-verify.py"],
        capture_output=True,
        text=True,
    )


def mutate(path, key, value):
    original = json.loads(path.read_text(encoding="utf-8"))
    mutated = dict(original)
    mutated[key] = value
    path.write_text(
        json.dumps(mutated, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return original


def mutate_nested(path, parent, key, value):
    original = json.loads(path.read_text(encoding="utf-8"))
    mutated = json.loads(json.dumps(original))
    mutated.setdefault(parent, {})[key] = value
    path.write_text(
        json.dumps(mutated, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return original


def restore(path, original):
    path.write_text(
        json.dumps(original, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def expect_fail(label):
    result = run()
    ok = result.returncode != 0
    print(f"{label}: {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    passed = 0
    total = 0

    result = run()
    total += 1
    ok = result.returncode == 0
    print(f"R1 baseline: {'PASS' if ok else 'FAIL'}")
    passed += ok

    original = mutate(P80, "executionAuthorized", True)
    total += 1
    passed += expect_fail("R2 Phase80 authorization mutation")
    restore(P80, original)

    original = mutate(P80_CP, "resultDigest", "tampered")
    total += 1
    passed += expect_fail("R3 Phase80 checkpoint digest mutation")
    restore(P80_CP, original)

    original = mutate(P81, "executionAuthorized", True)
    total += 1
    passed += expect_fail("R4 Phase81 authorization mutation")
    restore(P81, original)

    original = mutate(P81_CP, "resultDigest", "tampered")
    total += 1
    passed += expect_fail("R5 Phase81 checkpoint digest mutation")
    restore(P81_CP, original)

    original = mutate_nested(
        P81,
        "safety",
        "broadcastPerformed",
        True,
    )
    total += 1
    passed += expect_fail("R6 Phase81 safety mutation")
    restore(P81, original)

    result = run()
    total += 1
    ok = result.returncode == 0
    print(f"R7 restore baseline: {'PASS' if ok else 'FAIL'}")
    passed += ok

    print(f"REGRESSION: {passed}/{total} PASS")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
