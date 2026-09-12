#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"
SRC = ROOT / "src" / "aacp-phase79-deterministic-replay-verify.py"

TARGETS = [
    BASE / "phase65-dummy-not-used.json",
]

P65 = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify.json"
)

P77 = BASE / "phase77-provenance.json"


def run():
    proc = subprocess.run(
        ["python3", str(SRC)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def digest_from_output(output):
    for line in output.splitlines():
        if line.startswith("CHAIN DIGEST: "):
            return line.split(": ", 1)[1].strip()
    return None


def mutate(path, mutation):
    original = path.read_text(encoding="utf-8")

    try:
        obj = json.loads(original)
        mutation(obj)
        path.write_text(
            json.dumps(obj, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        rc, output = run()

        if rc == 0:
            return False

        return "VALID: False" in output
    finally:
        path.write_text(original, encoding="utf-8")


def main():
    rc, output = run()

    if rc != 0 or "VALID: True" not in output:
        print("R1 baseline: FAIL")
        return 1

    digest1 = digest_from_output(output)

    rc, output2 = run()

    digest2 = digest_from_output(output2)

    if rc == 0 and digest1 and digest1 == digest2:
        print("R1 baseline replay stability: PASS")
    else:
        print("R1 baseline replay stability: FAIL")
        return 1

    if mutate(
        P65,
        lambda obj: obj.__setitem__("state", "TAMPERED"),
    ):
        print("R2 Phase65 mutation: PASS")
    else:
        print("R2 Phase65 mutation: FAIL")
        return 1

    if mutate(
        P77,
        lambda obj: obj.__setitem__("state", "TAMPERED"),
    ):
        print("R3 Phase77 mutation: PASS")
    else:
        print("R3 Phase77 mutation: FAIL")
        return 1

    rc, restored = run()

    if rc == 0 and "VALID: True" in restored:
        print("R4 restore baseline: PASS")
    else:
        print("R4 restore baseline: FAIL")
        return 1

    print("REGRESSION: 4/4 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
