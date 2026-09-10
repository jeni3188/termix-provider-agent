#!/usr/bin/env python3

import copy
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / "src" / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-"
    "drift-continuity-stability-verify.py"
)

OUT_DIR = ROOT / "provider-output" / "aacp-observer"

PHASE56_OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-verify.json"
)

CHECKPOINT = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-checkpoint.json"
)

OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-verify.json"
)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def run():
    return subprocess.run(
        [sys.executable, str(SRC)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def expect_success(label):
    result = run()
    assert result.returncode == 0, (
        f"{label}: expected success\n"
        + result.stdout
        + result.stderr
    )


def expect_blocked(label):
    result = run()
    assert result.returncode != 0, (
        f"{label}: expected blocked\n"
        + result.stdout
        + result.stderr
    )
    assert "STATE: BLOCKED" in result.stdout, (
        f"{label}: missing BLOCKED\n{result.stdout}"
    )


def establish():
    CHECKPOINT.unlink(missing_ok=True)
    OUTPUT.unlink(missing_ok=True)

    result = run()
    assert result.returncode == 0
    assert "CHECKPOINT_ESTABLISHED" in result.stdout

    result = run()
    assert result.returncode == 0
    assert "VERIFIED_READ_ONLY" in result.stdout


def main():
    original_phase56 = load(PHASE56_OUTPUT)

    try:
        print("[01] checkpoint establishment")
        establish()

        print("[02] normal stability verification")
        expect_success("normal")

        print("[03] deterministic stability digest")
        first = load(OUTPUT)
        digest1 = first["verification"]["stabilityDigest"]

        expect_success("deterministic second run")

        second = load(OUTPUT)
        digest2 = second["verification"]["stabilityDigest"]

        assert digest1 == digest2
        assert len(digest1) == 64

        print("[04] Phase56 generatedAt-only change ignored")
        phase56 = copy.deepcopy(original_phase56)
        phase56["generatedAt"] = "2099-01-01T00:00:00+00:00"
        save(PHASE56_OUTPUT, phase56)

        expect_success("generatedAt-only")

        save(PHASE56_OUTPUT, original_phase56)

        print("[05] Phase56 continuityDigest tamper blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["verification"]["continuityDigest"] = "0" * 64
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("continuityDigest tamper")

        save(PHASE56_OUTPUT, original_phase56)

        print("[06] Phase56 readiness tamper blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["readiness"]["ready"] = False
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("readiness tamper")

        save(PHASE56_OUTPUT, original_phase56)

        print("[07] Phase56 validity tamper blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["verification"]["valid"] = False
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("validity tamper")

        save(PHASE56_OUTPUT, original_phase56)

        print("[08] execution authorization violation blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["executionAuthorized"] = True
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("execution authorization")

        save(PHASE56_OUTPUT, original_phase56)

        print("[09] wallet safety violation blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["safety"]["walletUsed"] = True
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("wallet safety")

        save(PHASE56_OUTPUT, original_phase56)

        print("[10] signing safety violation blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["safety"]["signingPerformed"] = True
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("signing safety")

        save(PHASE56_OUTPUT, original_phase56)

        print("[11] broadcast safety violation blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["safety"]["broadcastPerformed"] = True
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("broadcast safety")

        save(PHASE56_OUTPUT, original_phase56)

        print("[12] submission safety violation blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["safety"]["submissionPerformed"] = True
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("submission safety")

        save(PHASE56_OUTPUT, original_phase56)

        print("[13] Phase56 errorCount violation blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["errorCount"] = 1
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("errorCount")

        save(PHASE56_OUTPUT, original_phase56)

        print("[14] Phase56 state violation blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["state"] = "BLOCKED"
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("state")

        save(PHASE56_OUTPUT, original_phase56)

        print("[15] Phase56 checkpoint violation blocked")
        phase56 = copy.deepcopy(original_phase56)
        phase56["verification"]["checkpoint"] = "INVALID"
        save(PHASE56_OUTPUT, phase56)

        expect_blocked("checkpoint")

        save(PHASE56_OUTPUT, original_phase56)

        print("[16] missing Phase56 blocked")
        PHASE56_OUTPUT.unlink()

        expect_blocked("missing phase56")

        save(PHASE56_OUTPUT, original_phase56)

        print("[17] corrupt Phase56 blocked")
        PHASE56_OUTPUT.write_text("{broken", encoding="utf-8")

        expect_blocked("corrupt phase56")

        save(PHASE56_OUTPUT, original_phase56)

        print("[18] checkpoint digest tampering blocked")
        checkpoint = load(CHECKPOINT)
        checkpoint["checkpointDigest"] = "1" * 64
        save(CHECKPOINT, checkpoint)

        expect_blocked("checkpoint digest")

        establish()

        print("[19] checkpoint projection tampering blocked")
        checkpoint = load(CHECKPOINT)
        checkpoint["checkpointProjection"]["mode"] = "WRITE"
        save(CHECKPOINT, checkpoint)

        expect_blocked("checkpoint projection")

        establish()

        print("[20] checkpoint type tampering blocked")
        checkpoint = load(CHECKPOINT)
        checkpoint["type"] = "INVALID"
        save(CHECKPOINT, checkpoint)

        expect_blocked("checkpoint type")

        establish()

        print("[21] checkpoint stability digest tampering blocked")
        checkpoint = load(CHECKPOINT)
        checkpoint["stabilityDigest"] = "2" * 64
        save(CHECKPOINT, checkpoint)

        expect_blocked("checkpoint stability digest")

        establish()

        print("[22] restored stability verification")
        expect_success("restored")

        final = load(OUTPUT)

        assert final["state"] == "VERIFIED_READ_ONLY"
        assert final["sourceState"] == "VERIFIED_READ_ONLY"
        assert final["executionAuthorized"] is False
        assert final["readiness"]["ready"] is True
        assert final["verification"]["valid"] is True
        assert final["verification"]["checkpoint"] == "VERIFIED"
        assert final["verification"]["verifiedLayers"] == 1
        assert final["errorCount"] == 0
        assert len(final["verification"]["stabilityDigest"]) == 64

        print()
        print("PHASE57 REGRESSION: 22/22 PASSED")
        return 0

    finally:
        save(PHASE56_OUTPUT, original_phase56)


if __name__ == "__main__":
    raise SystemExit(main())
