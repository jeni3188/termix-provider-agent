#!/usr/bin/env python3

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-drift-verify.py"
)

OUT_DIR = ROOT / "provider-output" / "aacp-observer"

PHASE53_OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-verify.json"
)

PHASE53_HISTORY = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history.json"
)

PHASE54_OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-continuity-verify.json"
)

CHECKPOINT = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-drift-checkpoint.json"
)

OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-continuity-drift-verify.json"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_DRIFT_VERIFY"
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
        f"{label}: expected success, got {result.returncode}\n"
        + result.stdout
        + result.stderr
    )
    return result.stdout


def expect_blocked(label):
    result = run()
    assert result.returncode != 0, (
        f"{label}: expected failure\n"
        + result.stdout
        + result.stderr
    )
    assert "STATE: BLOCKED" in result.stdout, (
        f"{label}: missing BLOCKED state\n{result.stdout}"
    )


def restore(files, backup):
    for path, obj in backup.items():
        save(path, obj)


def establish():
    CHECKPOINT.unlink(missing_ok=True)
    OUTPUT.unlink(missing_ok=True)

    result = run()
    assert result.returncode == 0
    assert "CHECKPOINT_ESTABLISHED" in result.stdout

    result = run()
    assert result.returncode == 0
    assert "VERIFIED_READ_ONLY" in result.stdout

    return load(CHECKPOINT)


def main():
    original = {
        PHASE53_OUTPUT: load(PHASE53_OUTPUT),
        PHASE53_HISTORY: load(PHASE53_HISTORY),
        PHASE54_OUTPUT: load(PHASE54_OUTPUT),
    }

    try:
        print("[01] checkpoint establishment")
        checkpoint = establish()

        print("[02] normal continuity verification")
        expect_success("normal")

        print("[03] deterministic drift digest")
        out1 = load(OUTPUT)
        out2 = load(OUTPUT)
        assert out1["verification"]["driftDigest"] == \
            out2["verification"]["driftDigest"]

        print("[04] Phase54 generatedAt-only change ignored")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["generatedAt"] = "2099-01-01T00:00:00+00:00"
        save(PHASE54_OUTPUT, phase54)
        expect_success("phase54 generatedAt-only")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[05] Phase54 continuityDigest drift blocked")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["verification"]["continuityDigest"] = "0" * 64
        save(PHASE54_OUTPUT, phase54)
        expect_blocked("phase54 continuity digest drift")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[06] Phase54 readiness drift blocked")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["readiness"]["ready"] = False
        save(PHASE54_OUTPUT, phase54)
        expect_blocked("phase54 readiness drift")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[07] Phase54 validity drift blocked")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["verification"]["valid"] = False
        save(PHASE54_OUTPUT, phase54)
        expect_blocked("phase54 validity drift")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[08] execution authorization violation blocked")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["executionAuthorized"] = True
        save(PHASE54_OUTPUT, phase54)
        expect_blocked("execution authorization")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[09] wallet safety violation blocked")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["safety"]["walletUsed"] = True
        save(PHASE54_OUTPUT, phase54)
        expect_blocked("wallet safety")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[10] signing safety violation blocked")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["safety"]["signingPerformed"] = True
        save(PHASE54_OUTPUT, phase54)
        expect_blocked("signing safety")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[11] broadcast safety violation blocked")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["safety"]["broadcastPerformed"] = True
        save(PHASE54_OUTPUT, phase54)
        expect_blocked("broadcast safety")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[12] submission safety violation blocked")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["safety"]["submissionPerformed"] = True
        save(PHASE54_OUTPUT, phase54)
        expect_blocked("submission safety")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[13] Phase54 errorCount blocked")
        phase54 = copy.deepcopy(original[PHASE54_OUTPUT])
        phase54["errorCount"] = 1
        save(PHASE54_OUTPUT, phase54)
        expect_blocked("phase54 error count")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[14] Phase53 historyDigest drift blocked")
        phase53 = copy.deepcopy(original[PHASE53_OUTPUT])
        phase53["verification"]["historyDigest"] = "1" * 64
        save(PHASE53_OUTPUT, phase53)
        expect_blocked("phase53 history digest")
        save(PHASE53_OUTPUT, original[PHASE53_OUTPUT])

        print("[15] Phase53 stabilityDigest drift blocked")
        phase53 = copy.deepcopy(original[PHASE53_OUTPUT])
        phase53["verification"]["stabilityDigest"] = "2" * 64
        save(PHASE53_OUTPUT, phase53)
        expect_blocked("phase53 stability digest")
        save(PHASE53_OUTPUT, original[PHASE53_OUTPUT])

        print("[16] history observation tamper blocked")
        history = copy.deepcopy(original[PHASE53_HISTORY])
        history["observations"][0]["observation"] = 99
        save(PHASE53_HISTORY, history)
        expect_blocked("history observation tamper")
        save(PHASE53_HISTORY, original[PHASE53_HISTORY])

        print("[17] history observation digest tamper blocked")
        history = copy.deepcopy(original[PHASE53_HISTORY])
        history["observations"][0]["stabilityDigest"] = "3" * 64
        save(PHASE53_HISTORY, history)
        expect_blocked("history stability digest")
        save(PHASE53_HISTORY, original[PHASE53_HISTORY])

        print("[18] history count tamper blocked")
        history = copy.deepcopy(original[PHASE53_HISTORY])
        history["observations"] = history["observations"][:2]
        save(PHASE53_HISTORY, history)
        expect_blocked("history count")
        save(PHASE53_HISTORY, original[PHASE53_HISTORY])

        print("[19] checkpoint digest tampering blocked")
        checkpoint = load(CHECKPOINT)
        checkpoint["checkpointDigest"] = "4" * 64
        save(CHECKPOINT, checkpoint)
        expect_blocked("checkpoint digest")
        save(CHECKPOINT, establish())

        print("[20] checkpoint projection tampering blocked")
        checkpoint = load(CHECKPOINT)
        checkpoint["checkpointProjection"]["mode"] = "WRITE"
        save(CHECKPOINT, checkpoint)
        expect_blocked("checkpoint projection")
        save(CHECKPOINT, establish())

        print("[21] checkpoint type tampering blocked")
        checkpoint = load(CHECKPOINT)
        checkpoint["type"] = "INVALID"
        save(CHECKPOINT, checkpoint)
        expect_blocked("checkpoint type")
        save(CHECKPOINT, establish())

        print("[22] missing Phase53 blocked")
        PHASE53_OUTPUT.unlink()
        expect_blocked("missing phase53")
        save(PHASE53_OUTPUT, original[PHASE53_OUTPUT])

        print("[23] corrupt Phase54 blocked")
        PHASE54_OUTPUT.write_text("{broken", encoding="utf-8")
        expect_blocked("corrupt phase54")
        save(PHASE54_OUTPUT, original[PHASE54_OUTPUT])

        print("[24] missing history blocked")
        PHASE53_HISTORY.unlink()
        expect_blocked("missing history")
        save(PHASE53_HISTORY, original[PHASE53_HISTORY])

        print("[25] restored continuity verification")
        CHECKPOINT.unlink(missing_ok=True)
        OUTPUT.unlink(missing_ok=True)
        establish()
        expect_success("restored continuity")

        print()
        print("PHASE55 REGRESSION: 25/25 PASSED")
        return 0

    finally:
        restore(original, original)


if __name__ == "__main__":
    raise SystemExit(main())
