#!/usr/bin/env python3

import json
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OBSERVER = BASE / "provider-output" / "aacp-observer"

GATE = BASE / "src" / "aacp-phase97-full-chain-integrity-gate.py"

OUTPUT = OBSERVER / "phase97-full-chain-integrity-gate.json"
CHECKPOINT = (
    OBSERVER / "phase97-full-chain-integrity-gate-checkpoint.json"
)

PHASE96_OUTPUT = OBSERVER / "phase96-post-finality-verification-gate.json"
PHASE96_CHECKPOINT = (
    OBSERVER / "phase96-post-finality-verification-gate-checkpoint.json"
)

BACKUP = OBSERVER / ".phase97-regression-backup"

def run_gate(expect_success=True):
    result = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=BASE,
        text=True,
        capture_output=True,
    )
    success = result.returncode == 0
    if success != expect_success:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise AssertionError(
            f"unexpected gate result: rc={result.returncode}"
        )
    return result


def mutate_json(path, key, value):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data[key] = value
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def restore():
    for name in (
        "phase96-output.json",
        "phase96-checkpoint.json",
        "phase97-output.json",
        "phase97-checkpoint.json",
    ):
        source = BACKUP / name
        if not source.exists():
            continue

        target = {
            "phase96-output.json": PHASE96_OUTPUT,
            "phase96-checkpoint.json": PHASE96_CHECKPOINT,
            "phase97-output.json": OUTPUT,
            "phase97-checkpoint.json": CHECKPOINT,
        }[name]

        shutil.copy2(source, target)


if BACKUP.exists():
    shutil.rmtree(BACKUP)

BACKUP.mkdir(parents=True)

for source, name in (
    (PHASE96_OUTPUT, "phase96-output.json"),
    (PHASE96_CHECKPOINT, "phase96-checkpoint.json"),
    (OUTPUT, "phase97-output.json"),
    (CHECKPOINT, "phase97-checkpoint.json"),
):
    if source.exists():
        shutil.copy2(source, BACKUP / name)

try:
    run_gate(True)
    print("R1 baseline: PASS")

    mutate_json(
        PHASE96_OUTPUT,
        "phase95_terminal_finality_digest",
        "0" * 64,
    )
    run_gate(False)
    print("R2 Phase95 finality mutation: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "post_finality_verification_digest",
        "0" * 64,
    )
    run_gate(False)
    print("R3 Phase96 post-finality mutation: PASS")
    restore()

    mutate_json(
        PHASE96_CHECKPOINT,
        "valid",
        False,
    )
    run_gate(False)
    print("R4 Phase96 checkpoint mutation: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "executionAuthorized",
        True,
    )
    run_gate(False)
    print("R5 execution authorization: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "networkAccess",
        True,
    )
    run_gate(False)
    print("R6 network access: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "walletPresent",
        True,
    )
    run_gate(False)
    print("R7 wallet presence: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "signingEnabled",
        True,
    )
    run_gate(False)
    print("R8 signing: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "broadcastEnabled",
        True,
    )
    run_gate(False)
    print("R9 broadcast: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "submissionEnabled",
        True,
    )
    run_gate(False)
    print("R10 submission: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "phase",
        999,
    )
    run_gate(False)
    print("R11 phase mutation: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "previous_phase",
        93,
    )
    run_gate(False)
    print("R12 previous phase mutation: PASS")
    restore()

    mutate_json(
        PHASE96_OUTPUT,
        "error_count",
        1,
    )
    run_gate(False)
    print("R13 error count mutation: PASS")
    restore()

    run_gate(True)
    print("R14 restore baseline: PASS")

finally:
    restore()
    if BACKUP.exists():
        shutil.rmtree(BACKUP)
    run_gate(True)

print("REGRESSION: 14/14 PASS")
