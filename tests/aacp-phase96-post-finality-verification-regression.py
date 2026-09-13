#!/usr/bin/env python3

import json
import shutil
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OBSERVER = BASE / "provider-output" / "aacp-observer"

SOURCE = BASE / "src/aacp-phase96-post-finality-verification-gate.py"

PHASE95_SOURCE = (
    BASE
    / "src"
    / "aacp-phase95-evidence-chain-terminal-finality-gate.py"
)

OUTPUT = (
    OBSERVER
    / "phase95-evidence-chain-terminal-finality-gate.json"
)

CHECKPOINT = (
    OBSERVER
    / "phase95-evidence-chain-terminal-finality-gate-checkpoint.json"
)

PHASE96_OUTPUT = (
    OBSERVER
    / "phase96-post-finality-verification-gate.json"
)

PHASE96_CHECKPOINT = (
    OBSERVER
    / "phase96-post-finality-verification-gate-checkpoint.json"
)

TEMP_DIR = OBSERVER / ".phase96-regression-backup"


def run_phase96():
    return subprocess.run(
        ["python3", str(SOURCE)],
        cwd=BASE,
        capture_output=True,
        text=True,
    )


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(path, value):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")


def expect_pass(label):
    result = run_phase96()
    ok = result.returncode == 0
    print(f"{label}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print(result.stdout)
        print(result.stderr)
    return ok


def expect_fail(label):
    result = run_phase96()
    ok = result.returncode != 0
    print(f"{label}: {'PASS' if ok else 'FAIL'}")
    return ok


def mutate_json(path, key, value):
    data = load(path)
    original = data[key]
    data[key] = value
    save(path, data)
    return original


TEMP_DIR.mkdir(exist_ok=True)

shutil.copy2(OUTPUT, TEMP_DIR / OUTPUT.name)
shutil.copy2(CHECKPOINT, TEMP_DIR / CHECKPOINT.name)
shutil.copy2(PHASE95_SOURCE, TEMP_DIR / PHASE95_SOURCE.name)

passed = 0
total = 0

try:
    tests = []

    tests.append(("R1 baseline", lambda: expect_pass("R1 baseline")))

    def r2():
        original = mutate_json(
            OUTPUT,
            "terminal_finality_digest",
            "0" * 64,
        )
        try:
            return expect_fail("R2 terminal finality mutation")
        finally:
            data = load(OUTPUT)
            data["terminal_finality_digest"] = original
            save(OUTPUT, data)

    tests.append(("R2", r2))

    def r3():
        original = mutate_json(
            OUTPUT,
            "phase94_source_digest",
            "1" * 64,
        )
        try:
            return expect_fail("R3 Phase94 source anchor mutation")
        finally:
            data = load(OUTPUT)
            data["phase94_source_digest"] = original
            save(OUTPUT, data)

    tests.append(("R3", r3))

    def r4():
        original = mutate_json(
            CHECKPOINT,
            "terminal_finality_digest",
            "2" * 64,
        )
        try:
            return expect_fail("R4 checkpoint mutation")
        finally:
            data = load(CHECKPOINT)
            data["terminal_finality_digest"] = original
            save(CHECKPOINT, data)

    tests.append(("R4", r4))

    def r5():
        original = mutate_json(
            OUTPUT,
            "state",
            "REJECTED_READ_ONLY",
        )
        try:
            return expect_fail("R5 state mutation")
        finally:
            data = load(OUTPUT)
            data["state"] = original
            save(OUTPUT, data)

    tests.append(("R5", r5))

    def r6():
        original = mutate_json(OUTPUT, "ready", False)
        try:
            return expect_fail("R6 ready mutation")
        finally:
            data = load(OUTPUT)
            data["ready"] = original
            save(OUTPUT, data)

    tests.append(("R6", r6))

    def r7():
        original = mutate_json(OUTPUT, "valid", False)
        try:
            return expect_fail("R7 valid mutation")
        finally:
            data = load(OUTPUT)
            data["valid"] = original
            save(OUTPUT, data)

    tests.append(("R7", r7))

    def r8():
        original = mutate_json(OUTPUT, "executionAuthorized", True)
        try:
            return expect_fail("R8 execution authorization")
        finally:
            data = load(OUTPUT)
            data["executionAuthorized"] = original
            save(OUTPUT, data)

    tests.append(("R8", r8))

    def r9():
        original = mutate_json(OUTPUT, "networkAccess", True)
        try:
            return expect_fail("R9 network access")
        finally:
            data = load(OUTPUT)
            data["networkAccess"] = original
            save(OUTPUT, data)

    tests.append(("R9", r9))

    def r10():
        original = mutate_json(OUTPUT, "walletPresent", True)
        try:
            return expect_fail("R10 wallet presence")
        finally:
            data = load(OUTPUT)
            data["walletPresent"] = original
            save(OUTPUT, data)

    tests.append(("R10", r10))

    def r11():
        original = mutate_json(OUTPUT, "signingEnabled", True)
        try:
            return expect_fail("R11 signing")
        finally:
            data = load(OUTPUT)
            data["signingEnabled"] = original
            save(OUTPUT, data)

    tests.append(("R11", r11))

    def r12():
        original = mutate_json(OUTPUT, "broadcastEnabled", True)
        try:
            return expect_fail("R12 broadcast")
        finally:
            data = load(OUTPUT)
            data["broadcastEnabled"] = original
            save(OUTPUT, data)

    tests.append(("R12", r12))

    def r13():
        original = mutate_json(OUTPUT, "submissionEnabled", True)
        try:
            return expect_fail("R13 submission")
        finally:
            data = load(OUTPUT)
            data["submissionEnabled"] = original
            save(OUTPUT, data)

    tests.append(("R13", r13))

    def r14():
        original = mutate_json(OUTPUT, "phase", 999)
        try:
            return expect_fail("R14 phase mutation")
        finally:
            data = load(OUTPUT)
            data["phase"] = original
            save(OUTPUT, data)

    tests.append(("R14", r14))

    def r15():
        original = mutate_json(OUTPUT, "previous_phase", 999)
        try:
            return expect_fail("R15 previous phase mutation")
        finally:
            data = load(OUTPUT)
            data["previous_phase"] = original
            save(OUTPUT, data)

    tests.append(("R15", r15))

    def r16():
        original = mutate_json(
            CHECKPOINT,
            "checkpoint",
            "REJECTED",
        )
        try:
            return expect_fail("R16 checkpoint status mutation")
        finally:
            data = load(CHECKPOINT)
            data["checkpoint"] = original
            save(CHECKPOINT, data)

    tests.append(("R16", r16))

    def r17():
        original = mutate_json(
            OUTPUT,
            "error_count",
            1,
        )
        try:
            return expect_fail("R17 error count mutation")
        finally:
            data = load(OUTPUT)
            data["error_count"] = original
            save(OUTPUT, data)

    tests.append(("R17", r17))

    for _, test in tests:
        total += 1
        if test():
            passed += 1

finally:
    shutil.copy2(TEMP_DIR / OUTPUT.name, OUTPUT)
    shutil.copy2(TEMP_DIR / CHECKPOINT.name, CHECKPOINT)
    shutil.copy2(TEMP_DIR / PHASE95_SOURCE.name, PHASE95_SOURCE)

    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    subprocess.run(
        ["python3", str(SOURCE)],
        cwd=BASE,
        check=False,
    )

print(f"REGRESSION: {passed}/{total} PASS")

if passed != total:
    raise SystemExit(1)
