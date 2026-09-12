#!/usr/bin/env python3

import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(
    ROOT, "src", "aacp-phase87-evidence-chain-continuity-gate.py"
)


def run(path):
    return subprocess.run(
        [sys.executable, path],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def must(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    original = open(SOURCE, "rb").read()

    # R1 baseline
    r1 = run(SOURCE)
    must(r1.returncode == 0, "baseline failed")
    must("VALID: True" in r1.stdout, "baseline validity missing")
    print("R1 baseline: PASS")

    # R2 previous digest mutation
    mutated = original.replace(
        b"cfd0cd2c9f68c738d26c53b2d401f9264fc339708006ed4d70646d05a8136816",
        b"0000000000000000000000000000000000000000000000000000000000000000",
    )
    must(mutated != original, "R2 mutation did not apply")

    with open(SOURCE, "wb") as f:
        f.write(mutated)

    r2 = run(SOURCE)
    must(r2.returncode != 0, "digest mutation was accepted")
    must("digest mismatch" in r2.stdout.lower(), "digest mutation not detected")
    print("R2 Phase86 digest mutation: PASS")

    # R3 execution authorization mutation
    restored = original.replace(
        b"EXECUTION_AUTHORIZED = False",
        b"EXECUTION_AUTHORIZED = True",
    )

    with open(SOURCE, "wb") as f:
        f.write(restored)

    r3 = run(SOURCE)
    must(r3.returncode != 0, "execution authorization mutation accepted")
    print("R3 execution authorization mutation: PASS")

    # R4 network mutation
    restored = original.replace(
        b"NETWORK_ACCESS = False",
        b"NETWORK_ACCESS = True",
    )

    with open(SOURCE, "wb") as f:
        f.write(restored)

    r4 = run(SOURCE)
    must(r4.returncode != 0, "network mutation accepted")
    print("R4 network mutation: PASS")

    # R5 wallet mutation
    restored = original.replace(
        b"WALLET_PRESENT = False",
        b"WALLET_PRESENT = True",
    )

    with open(SOURCE, "wb") as f:
        f.write(restored)

    r5 = run(SOURCE)
    must(r5.returncode != 0, "wallet mutation accepted")
    print("R5 wallet mutation: PASS")

    # R6 checkpoint mutation
    restored = original.replace(
        b'if phase86.get("CHECKPOINT") != "VERIFIED":',
        b'if phase86.get("CHECKPOINT") != "BROKEN":',
    )

    with open(SOURCE, "wb") as f:
        f.write(restored)

    r6 = run(SOURCE)
    must(r6.returncode != 0, "checkpoint mutation accepted")
    print("R6 checkpoint mutation: PASS")

    # R7 restore baseline
    with open(SOURCE, "wb") as f:
        f.write(original)

    r7 = run(SOURCE)
    must(r7.returncode == 0, "restore baseline failed")
    must("VALID: True" in r7.stdout, "restored baseline invalid")
    print("R7 restore baseline: PASS")

    print("REGRESSION: 7/7 PASS")


if __name__ == "__main__":
    main()
