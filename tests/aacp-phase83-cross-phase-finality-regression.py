#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

P82 = BASE / "phase82-seal-continuity.json"
P82_CP = BASE / "phase82-seal-continuity-checkpoint.json"

OUT = BASE / "phase83-cross-phase-finality.json"
CP = BASE / "phase83-cross-phase-finality-checkpoint.json"

SOURCE = ROOT / "src" / "aacp-phase83-cross-phase-finality-verify.py"


def run():
    completed = subprocess.run(
        ["python3", str(SOURCE)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def load(path):
    return json.loads(path.read_text())


original_p82 = P82.read_text()
original_p82_cp = P82_CP.read_text()

checks = []


def check(name, condition):
    checks.append((name, bool(condition)))
    print(f"{name}: {'PASS' if condition else 'FAIL'}")


try:
    code, stdout, stderr = run()
    baseline = load(OUT)
    baseline_cp = load(CP)

    check(
        "R1 baseline",
        code == 0
        and baseline["state"] == "VERIFIED_READ_ONLY"
        and baseline["ready"] is True
        and baseline["valid"] is True
        and baseline["checkpoint"] == "VERIFIED"
        and baseline["verification"]["errorCount"] == 0,
    )

    mutated = load(P82)
    mutated["valid"] = False
    P82.write_text(
        json.dumps(mutated, indent=2, sort_keys=True) + "\n"
    )

    _, _, _ = run()
    rejected = load(OUT)

    check(
        "R2 Phase82 validity mutation",
        rejected["valid"] is False
        and rejected["checkpoint"] == "REJECTED"
        and rejected["verification"]["errorCount"] > 0,
    )

    P82.write_text(original_p82)

    mutated_cp = load(P82_CP)
    mutated_cp["resultDigest"] = "0" * 64
    P82_CP.write_text(
        json.dumps(mutated_cp, indent=2, sort_keys=True) + "\n"
    )

    _, _, _ = run()
    rejected = load(OUT)

    check(
        "R3 Phase82 checkpoint digest mutation",
        rejected["valid"] is False
        and "phase82:checkpointResultDigest"
        in rejected["verification"]["errors"],
    )

    P82_CP.write_text(original_p82_cp)

    mutated = load(P82)
    mutated["safety"]["walletAccess"] = True
    P82.write_text(
        json.dumps(mutated, indent=2, sort_keys=True) + "\n"
    )

    _, _, _ = run()
    rejected = load(OUT)

    check(
        "R4 Phase82 safety mutation",
        rejected["valid"] is False
        and any(
            error.startswith("phase82:safety")
            for error in rejected["verification"]["errors"]
        ),
    )

finally:
    P82.write_text(original_p82)
    P82_CP.write_text(original_p82_cp)

    run()

    restored = load(OUT)
    restored_cp = load(CP)

    check(
        "R5 restore baseline",
        restored["state"] == "VERIFIED_READ_ONLY"
        and restored["ready"] is True
        and restored["valid"] is True
        and restored["checkpoint"] == "VERIFIED"
        and restored["verification"]["errorCount"] == 0
        and restored_cp["executionAuthorized"] is False,
    )


passed = sum(1 for _, ok in checks if ok)

print(f"REGRESSION: {passed}/{len(checks)} PASS")

if passed != len(checks):
    raise SystemExit(1)
