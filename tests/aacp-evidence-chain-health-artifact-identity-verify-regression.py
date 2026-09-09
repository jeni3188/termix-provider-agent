#!/usr/bin/env python3

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/aacp-evidence-chain-health-artifact-identity-verify.py"
BASE = ROOT / "provider-output/aacp-observer"

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-artifact-identity-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-artifact-identity-verify.json"
)

PHASE43 = BASE / (
    "latest-aacp-evidence-chain-health-temporal-continuity-verify.json"
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

    original_phase43 = PHASE43.read_text()
    original_checkpoint = CHECKPOINT.read_text()

    artifacts = sorted(
        BASE.glob("latest-aacp-evidence-chain-health-*.json")
    )

    target = BASE / (
        "latest-aacp-evidence-chain-health-audit-history-audit-history.json"
    )

    original_target = target.read_text()

    try:
        # 1. Normal verification
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode == 0
            and data["state"] == "VERIFIED_READ_ONLY"
            and data["readiness"]["ready"] is True
            and data["verification"]["valid"] is True
            and data["verification"]["verifiedLayers"] == 13,
            "normal identity verification",
        )

        # 2. Missing artifact
        target.unlink()
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED"
            and data["verification"]["valid"] is False,
            "missing artifact blocked",
        )
        target.write_text(original_target)

        # Restore valid output/checkpoint
        run()

        # 3. Corrupt JSON
        target.write_text("{broken")
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "corrupt JSON blocked",
        )
        target.write_text(original_target)
        run()

        # 4. Wrong type
        obj = load(target)
        old_type = obj["type"]
        obj["type"] = "WRONG_TYPE"
        save(target, obj)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "wrong artifact type blocked",
        )
        obj["type"] = old_type
        save(target, obj)
        run()

        # 5. Mode violation
        obj = load(target)
        old_mode = obj.get("mode")
        obj["mode"] = "EXECUTION"
        save(target, obj)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "mode violation blocked",
        )
        obj["mode"] = old_mode
        save(target, obj)
        run()

        # 6. SHA-256 identity drift
        raw = target.read_bytes()
        target.write_bytes(raw + b"\n")
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "SHA-256 identity drift blocked",
        )
        target.write_bytes(raw)
        run()

        # 7. generatedAt malformed
        obj = load(target)
        old_generated = obj["generatedAt"]
        obj["generatedAt"] = "NOT-A-TIMESTAMP"
        save(target, obj)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "malformed generatedAt blocked",
        )
        obj["generatedAt"] = old_generated
        save(target, obj)
        run()

        # 8. execution authorization violation
        obj = load(target)
        old_auth = obj.get("executionAuthorized")
        obj["executionAuthorized"] = True
        save(target, obj)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "execution authorization violation blocked",
        )
        obj["executionAuthorized"] = old_auth
        save(target, obj)
        run()

        # 9. wallet violation
        obj = load(target)
        old = obj["safety"]["walletUsed"]
        obj["safety"]["walletUsed"] = True
        save(target, obj)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "wallet safety violation blocked",
        )
        obj["safety"]["walletUsed"] = old
        save(target, obj)
        run()

        # 10. signing violation
        obj = load(target)
        old = obj["safety"]["signingPerformed"]
        obj["safety"]["signingPerformed"] = True
        save(target, obj)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "signing safety violation blocked",
        )
        obj["safety"]["signingPerformed"] = old
        save(target, obj)
        run()

        # 11. broadcast violation
        obj = load(target)
        old = obj["safety"]["broadcastPerformed"]
        obj["safety"]["broadcastPerformed"] = True
        save(target, obj)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "broadcast safety violation blocked",
        )
        obj["safety"]["broadcastPerformed"] = old
        save(target, obj)
        run()

        # 12. submission violation
        obj = load(target)
        old = obj["safety"]["submissionPerformed"]
        obj["safety"]["submissionPerformed"] = True
        save(target, obj)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "submission safety violation blocked",
        )
        obj["safety"]["submissionPerformed"] = old
        save(target, obj)
        run()

        # 13. error count violation
        obj = load(target)
        old_count = obj["errorCount"]
        old_errors = obj["errors"]
        obj["errorCount"] = 1
        obj["errors"] = ["synthetic"]
        save(target, obj)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "error count violation blocked",
        )
        obj["errorCount"] = old_count
        obj["errors"] = old_errors
        save(target, obj)
        run()

        # 14. Phase43 readiness violation
        phase43 = load(PHASE43)
        old_ready = phase43["readiness"]["ready"]
        phase43["readiness"]["ready"] = False
        save(PHASE43, phase43)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "Phase43 readiness violation blocked",
        )
        phase43["readiness"]["ready"] = old_ready
        save(PHASE43, phase43)
        run()

        # 15. Phase43 validity violation
        phase43 = load(PHASE43)
        old_valid = phase43["verification"]["valid"]
        phase43["verification"]["valid"] = False
        save(PHASE43, phase43)
        result = run()
        data = load(OUTPUT)
        assert_true(
            result.returncode != 0
            and data["state"] == "BLOCKED",
            "Phase43 validity violation blocked",
        )
        phase43["verification"]["valid"] = old_valid
        save(PHASE43, phase43)
        run()

        # 16. Deterministic identity digest
        first = load(OUTPUT)["verification"]["identityDigest"]
        result = run()
        second = load(OUTPUT)["verification"]["identityDigest"]

        assert_true(
            result.returncode == 0
            and first == second
            and len(first) == 64,
            "deterministic identity digest",
        )

    finally:
        PHASE43.write_text(original_phase43)
        target.write_text(original_target)
        CHECKPOINT.write_text(original_checkpoint)
        run()

    print()
    print(f"RESULT: {PASS}/{PASS + FAIL} PASSED")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
