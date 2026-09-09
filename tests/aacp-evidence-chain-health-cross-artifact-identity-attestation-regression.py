#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "src/aacp-evidence-chain-health-cross-artifact-identity-attestation.py"
)

BASE = ROOT / "provider-output/aacp-observer"

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-cross-artifact-identity-attestation-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-cross-artifact-identity-attestation.json"
)

PHASE44 = BASE / (
    "latest-aacp-evidence-chain-health-artifact-identity-verify.json"
)

TARGET = BASE / (
    "latest-aacp-evidence-chain-health-audit-history-audit-history.json"
)

PASS = 0
FAIL = 0


def run():
    return subprocess.run(
        [sys.executable, str(SOURCE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    )


def assert_true(condition, name):
    global PASS, FAIL

    if condition:
        PASS += 1
        print(f"PASS: {name}")
    else:
        FAIL += 1
        print(f"FAIL: {name}")


def main():
    global PASS, FAIL

    original_target = TARGET.read_bytes()
    original_phase44 = PHASE44.read_bytes()
    original_checkpoint = CHECKPOINT.read_bytes()

    try:
        # 1
        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode == 0
            and data["state"] == "VERIFIED_READ_ONLY"
            and data["readiness"]["ready"] is True
            and data["verification"]["valid"] is True
            and data["verification"]["verifiedLayers"] == 14,
            "normal cross-artifact attestation",
        )

        # 2
        TARGET.unlink()
        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "missing artifact blocked",
        )

        TARGET.write_bytes(original_target)
        run()

        # 3
        TARGET.write_bytes(b"{broken")
        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "corrupt artifact JSON blocked",
        )

        TARGET.write_bytes(original_target)
        run()

        # 4
        obj = load(TARGET)
        old = obj["type"]
        obj["type"] = "WRONG_TYPE"
        save(TARGET, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "artifact type mismatch blocked",
        )

        obj["type"] = old
        save(TARGET, obj)
        run()

        # 5
        obj = load(TARGET)
        old = obj["mode"]
        obj["mode"] = "EXECUTION"
        save(TARGET, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "mode violation blocked",
        )

        obj["mode"] = old
        save(TARGET, obj)
        run()

        # 6
        raw = TARGET.read_bytes()
        TARGET.write_bytes(raw + b"\n")

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "artifact SHA-256 drift blocked",
        )

        TARGET.write_bytes(raw)
        run()

        # 7
        obj = load(TARGET)
        old = obj["executionAuthorized"]
        obj["executionAuthorized"] = True
        save(TARGET, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "execution authorization violation blocked",
        )

        obj["executionAuthorized"] = old
        save(TARGET, obj)
        run()

        # 8
        obj = load(TARGET)
        old = obj["safety"]["walletUsed"]
        obj["safety"]["walletUsed"] = True
        save(TARGET, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "wallet safety violation blocked",
        )

        obj["safety"]["walletUsed"] = old
        save(TARGET, obj)
        run()

        # 9
        obj = load(TARGET)
        old = obj["safety"]["signingPerformed"]
        obj["safety"]["signingPerformed"] = True
        save(TARGET, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "signing safety violation blocked",
        )

        obj["safety"]["signingPerformed"] = old
        save(TARGET, obj)
        run()

        # 10
        obj = load(TARGET)
        old = obj["safety"]["broadcastPerformed"]
        obj["safety"]["broadcastPerformed"] = True
        save(TARGET, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "broadcast safety violation blocked",
        )

        obj["safety"]["broadcastPerformed"] = old
        save(TARGET, obj)
        run()

        # 11
        obj = load(TARGET)
        old = obj["safety"]["submissionPerformed"]
        obj["safety"]["submissionPerformed"] = True
        save(TARGET, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "submission safety violation blocked",
        )

        obj["safety"]["submissionPerformed"] = old
        save(TARGET, obj)
        run()

        # 12
        obj = load(TARGET)
        old_count = obj["errorCount"]
        old_errors = obj["errors"]
        obj["errorCount"] = 1
        obj["errors"] = ["synthetic"]
        save(TARGET, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "error count violation blocked",
        )

        obj["errorCount"] = old_count
        obj["errors"] = old_errors
        save(TARGET, obj)
        run()

        # 13
        obj = load(PHASE44)
        old = obj["readiness"]["ready"]
        obj["readiness"]["ready"] = False
        save(PHASE44, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "Phase44 readiness violation blocked",
        )

        obj["readiness"]["ready"] = old
        save(PHASE44, obj)
        run()

        # 14
        obj = load(PHASE44)
        old = obj["verification"]["valid"]
        obj["verification"]["valid"] = False
        save(PHASE44, obj)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "Phase44 validity violation blocked",
        )

        obj["verification"]["valid"] = old
        save(PHASE44, obj)
        run()

        # 15
        checkpoint = load(CHECKPOINT)
        old = checkpoint["attestationDigest"]
        checkpoint["attestationDigest"] = "0" * 64
        save(CHECKPOINT, checkpoint)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "checkpoint digest drift blocked",
        )

        checkpoint["attestationDigest"] = old
        save(CHECKPOINT, checkpoint)
        run()

        # 16
        checkpoint = load(CHECKPOINT)
        old_projection = checkpoint["attestationProjection"]

        tampered = json.loads(json.dumps(old_projection))
        tampered["artifacts"][0]["path"] = "tampered-path"

        checkpoint["attestationProjection"] = tampered
        save(CHECKPOINT, checkpoint)

        result = run()
        data = load(OUTPUT)

        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "checkpoint projection tampering blocked",
        )

        checkpoint["attestationProjection"] = old_projection
        save(CHECKPOINT, checkpoint)
        run()

        # 17
        first = load(OUTPUT)["verification"]["attestationDigest"]

        result = run()

        second = load(OUTPUT)["verification"]["attestationDigest"]

        assert_true(
            result.returncode == 0
            and first == second
            and len(first) == 64,
            "deterministic attestation digest",
        )

    finally:
        TARGET.write_bytes(original_target)
        PHASE44.write_bytes(original_phase44)
        CHECKPOINT.write_bytes(original_checkpoint)

        run()

    print()
    print(f"RESULT: {PASS}/{PASS + FAIL} PASSED")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
