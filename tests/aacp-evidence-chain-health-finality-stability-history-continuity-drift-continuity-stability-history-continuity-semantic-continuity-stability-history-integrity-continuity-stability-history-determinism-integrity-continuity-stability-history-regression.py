#!/usr/bin/env python3

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / (
    "src/aacp-evidence-chain-health-finality-stability-history-continuity-"
    "drift-continuity-stability-history-continuity-semantic-continuity-"
    "stability-history-integrity-continuity-stability-history-determinism-integrity-continuity-stability-history-verify.py"
)

BASE = ROOT / "provider-output/aacp-observer"

PHASE73_OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "phase73-determinism-integrity-continuity-stability-history.json"
)

PHASE73_CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "phase73-determinism-integrity-continuity-stability-history-checkpoint.json"
)

PHASE65_OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify.json"
)

PHASE65_CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify-checkpoint.json"
)


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n"
    )


def run():
    return subprocess.run(
        ["python", str(SOURCE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def assert_failed(case, result):
    if result.returncode == 0:
        raise AssertionError(f"{case}: expected failure")

    value = load(PHASE73_OUTPUT)

    assert value["state"] == "VERIFIED_READ_ONLY", case
    assert value["sourceState"] == "INVALID", case
    assert value["executionAuthorized"] is False, case
    assert value["verification"]["valid"] is False, case
    assert value["verification"]["checkpoint"] == "FAILED", case
    assert value["readiness"]["ready"] is False, case
    assert value["errors"], case


with tempfile.TemporaryDirectory() as td:
    td = Path(td)

    original_phase65 = load(PHASE65_OUTPUT)
    original_checkpoint65 = load(PHASE65_CHECKPOINT)

    # 1. Clean baseline
    result = run()
    assert result.returncode == 0, result.stderr
    value = load(PHASE73_OUTPUT)
    assert value["verification"]["valid"] is True
    assert value["readiness"]["ready"] is True
    print("R1 baseline: PASS")

    # 2. Phase65 output type mutation
    value = dict(original_phase65)
    value["type"] = "TAMPERED"
    save(PHASE65_OUTPUT, value)
    assert_failed("R2", run())
    print("R2 phase65 type mutation: PASS")
    save(PHASE65_OUTPUT, original_phase65)

    # 3. Phase65 execution authorization mutation
    value = dict(original_phase65)
    value["executionAuthorized"] = True
    save(PHASE65_OUTPUT, value)
    assert_failed("R3", run())
    print("R3 execution authorization mutation: PASS")
    save(PHASE65_OUTPUT, original_phase65)

    # 4. Phase65 readiness mutation
    value = dict(original_phase65)
    value["readiness"] = dict(value["readiness"])
    value["readiness"]["observations"] = 2
    save(PHASE65_OUTPUT, value)
    assert_failed("R4", run())
    print("R4 observation-count mutation: PASS")
    save(PHASE65_OUTPUT, original_phase65)

    # 5. Phase65 integrity digest mutation
    value = dict(original_phase65)
    value["verification"] = dict(value["verification"])
    value["verification"]["integrityDigest"] = "0" * 64
    save(PHASE65_OUTPUT, value)
    assert_failed("R5", run())
    print("R5 integrity digest mutation: PASS")
    save(PHASE65_OUTPUT, original_phase65)

    # 6. Phase65 checkpoint type mutation
    value = dict(original_checkpoint65)
    value["type"] = "TAMPERED"
    save(PHASE65_CHECKPOINT, value)
    assert_failed("R6", run())
    print("R6 checkpoint type mutation: PASS")
    save(PHASE65_CHECKPOINT, original_checkpoint65)

    # 7. Phase65 checkpoint integrity mutation
    value = dict(original_checkpoint65)
    value["integrityDigest"] = "f" * 64
    save(PHASE65_CHECKPOINT, value)
    assert_failed("R7", run())
    print("R7 checkpoint integrity mutation: PASS")
    save(PHASE65_CHECKPOINT, original_checkpoint65)

    # 8. Phase65 checkpoint observation mutation
    value = dict(original_checkpoint65)
    value["observationCount"] = 2
    save(PHASE65_CHECKPOINT, value)
    assert_failed("R8", run())
    print("R8 checkpoint observation mutation: PASS")
    save(PHASE65_CHECKPOINT, original_checkpoint65)

    # 9. Phase65 history digest mutation
    value = dict(original_phase65)
    value["verification"] = dict(value["verification"])
    value["verification"]["historyDigest"] = "1" * 64
    save(PHASE65_OUTPUT, value)
    assert_failed("R9", run())
    print("R9 history digest mutation: PASS")
    save(PHASE65_OUTPUT, original_phase65)

    # 10. Phase65 checkpoint digest linkage mutation
    value = dict(original_checkpoint65)
    value["historyDigest"] = "2" * 64
    save(PHASE65_CHECKPOINT, value)
    assert_failed("R10", run())
    print("R10 checkpoint linkage mutation: PASS")
    save(PHASE65_CHECKPOINT, original_checkpoint65)

print("PHASE73 REGRESSION: 10/10 PASS")
