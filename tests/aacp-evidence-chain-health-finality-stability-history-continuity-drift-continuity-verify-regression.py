#!/usr/bin/env python3

import copy
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-drift-continuity-verify.py"
)

OUT_DIR = ROOT / "provider-output" / "aacp-observer"

PHASE55_OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-continuity-drift-verify.json"
)

CHECKPOINT = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-drift-continuity-checkpoint.json"
)

OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-continuity-drift-continuity-verify.json"
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
    original_phase55 = load(PHASE55_OUTPUT)

    try:
        print("[01] checkpoint establishment")
        establish()

        print("[02] normal continuity verification")
        expect_success("normal")

        print("[03] deterministic continuity digest")
        first = load(OUTPUT)
        digest1 = first["verification"]["continuityDigest"]

        expect_success("deterministic second run")

        second = load(OUTPUT)
        digest2 = second["verification"]["continuityDigest"]

        assert digest1 == digest2
        assert len(digest1) == 64

        print("[04] Phase55 generatedAt-only change ignored")
        phase55 = copy.deepcopy(original_phase55)
        phase55["generatedAt"] = "2099-01-01T00:00:00+00:00"
        save(PHASE55_OUTPUT, phase55)
        expect_success("generatedAt-only")
        save(PHASE55_OUTPUT, original_phase55)

        print("[05] Phase55 driftDigest tamper blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["verification"]["driftDigest"] = "0" * 64
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("driftDigest tamper")
        save(PHASE55_OUTPUT, original_phase55)

        print("[06] Phase55 readiness tamper blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["readiness"]["ready"] = False
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("readiness tamper")
        save(PHASE55_OUTPUT, original_phase55)

        print("[07] Phase55 validity tamper blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["verification"]["valid"] = False
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("validity tamper")
        save(PHASE55_OUTPUT, original_phase55)

        print("[08] execution authorization violation blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["executionAuthorized"] = True
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("execution authorization")
        save(PHASE55_OUTPUT, original_phase55)

        print("[09] wallet safety violation blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["safety"]["walletUsed"] = True
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("wallet safety")
        save(PHASE55_OUTPUT, original_phase55)

        print("[10] signing safety violation blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["safety"]["signingPerformed"] = True
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("signing safety")
        save(PHASE55_OUTPUT, original_phase55)

        print("[11] broadcast safety violation blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["safety"]["broadcastPerformed"] = True
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("broadcast safety")
        save(PHASE55_OUTPUT, original_phase55)

        print("[12] submission safety violation blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["safety"]["submissionPerformed"] = True
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("submission safety")
        save(PHASE55_OUTPUT, original_phase55)

        print("[13] Phase55 errorCount violation blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["errorCount"] = 1
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("errorCount")
        save(PHASE55_OUTPUT, original_phase55)

        print("[14] Phase55 state violation blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["state"] = "BLOCKED"
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("state")
        save(PHASE55_OUTPUT, original_phase55)

        print("[15] Phase55 checkpoint violation blocked")
        phase55 = copy.deepcopy(original_phase55)
        phase55["verification"]["checkpoint"] = "INVALID"
        save(PHASE55_OUTPUT, phase55)
        expect_blocked("checkpoint")
        save(PHASE55_OUTPUT, original_phase55)

        print("[16] missing Phase55 blocked")
        PHASE55_OUTPUT.unlink()
        expect_blocked("missing phase55")
        save(PHASE55_OUTPUT, original_phase55)

        print("[17] corrupt Phase55 blocked")
        PHASE55_OUTPUT.write_text("{broken", encoding="utf-8")
        expect_blocked("corrupt phase55")
        save(PHASE55_OUTPUT, original_phase55)

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

        print("[21] checkpoint continuity digest tampering blocked")
        checkpoint = load(CHECKPOINT)
        checkpoint["continuityDigest"] = "2" * 64
        save(CHECKPOINT, checkpoint)
        expect_blocked("checkpoint continuity digest")

        establish()

        print("[22] restored continuity verification")
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

        print()
        print("PHASE56 REGRESSION: 22/22 PASSED")
        return 0

    finally:
        save(PHASE55_OUTPUT, original_phase55)


if __name__ == "__main__":
    raise SystemExit(main())
