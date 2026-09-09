#!/usr/bin/env python3

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path("provider-output/aacp-observer")

SOURCE = Path(
    "src/aacp-evidence-chain-health-"
    "cross-artifact-attestation-temporal-continuity-verify.py"
)

PHASE45 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-identity-attestation.json"
)

PHASE46 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-consistency-verify.json"
)

PHASE47 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-drift-verify.json"
)

PHASE48 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-drift-continuity-verify.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-"
    "cross-artifact-attestation-temporal-continuity-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-temporal-continuity-verify.json"
)


def run():
    return subprocess.run(
        [sys.executable, str(SOURCE)],
        text=True,
        capture_output=True,
    )


def load(path):
    return json.loads(path.read_text())


def assert_verified():
    x = load(OUTPUT)

    assert x["state"] == "VERIFIED_READ_ONLY"
    assert x["sourceState"] == "VERIFIED_READ_ONLY"
    assert x["readiness"]["ready"] is True
    assert x["verification"]["valid"] is True
    assert x["verification"]["checkpoint"] == "VERIFIED"
    assert x["verification"]["requiredLayers"] == 4
    assert x["verification"]["verifiedLayers"] == 4
    assert x["errorCount"] == 0


def assert_blocked():
    x = load(OUTPUT)

    assert x["state"] == "BLOCKED"
    assert x["sourceState"] == "BLOCKED"
    assert x["readiness"]["ready"] is False
    assert x["verification"]["valid"] is False
    assert x["verification"]["checkpoint"] == "BLOCKED"
    assert x["verification"]["verifiedLayers"] == 0
    assert x["errorCount"] > 0


def backup(path, directory):
    target = directory / path.name
    shutil.copy2(path, target)
    return target


def restore(path, target):
    shutil.copy2(target, path)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    originals = {
        "phase45": backup(PHASE45, tmp),
        "phase46": backup(PHASE46, tmp),
        "phase47": backup(PHASE47, tmp),
        "phase48": backup(PHASE48, tmp),
        "checkpoint": backup(CHECKPOINT, tmp),
    }

    try:
        # 1. Normal temporal continuity.
        result = run()
        assert result.returncode == 0
        assert_verified()

        # 2. Phase45 malformed timestamp.
        x = load(PHASE45)
        x["generatedAt"] = "not-a-timestamp"
        PHASE45.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE45, originals["phase45"])

        # 3. Phase46 malformed timestamp.
        x = load(PHASE46)
        x["generatedAt"] = "not-a-timestamp"
        PHASE46.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE46, originals["phase46"])

        # 4. Phase47 malformed timestamp.
        x = load(PHASE47)
        x["generatedAt"] = "not-a-timestamp"
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, originals["phase47"])

        # 5. Phase48 malformed timestamp.
        x = load(PHASE48)
        x["generatedAt"] = "not-a-timestamp"
        PHASE48.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE48, originals["phase48"])

        # 6. Timestamp regression Phase46 < Phase45.
        x45 = load(PHASE45)
        x46 = load(PHASE46)

        x46["generatedAt"] = x45["generatedAt"]
        PHASE46.write_text(json.dumps(x46, indent=2, sort_keys=True))

        # Equal timestamps are valid, so force an earlier timestamp.
        x46["generatedAt"] = "2000-01-01T00:00:00+00:00"
        PHASE46.write_text(json.dumps(x46, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE46, originals["phase46"])

        # 7. Phase45 state violation.
        x = load(PHASE45)
        x["state"] = "BLOCKED"
        PHASE45.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE45, originals["phase45"])

        # 8. Phase46 validity violation.
        x = load(PHASE46)
        x["verification"]["valid"] = False
        PHASE46.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE46, originals["phase46"])

        # 9. Phase47 readiness violation.
        x = load(PHASE47)
        x["readiness"]["ready"] = False
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, originals["phase47"])

        # 10. Phase48 checkpoint violation.
        x = load(PHASE48)
        x["verification"]["checkpoint"] = "BLOCKED"
        PHASE48.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE48, originals["phase48"])

        # 11. Phase45 execution authorization violation.
        x = load(PHASE45)
        x["executionAuthorized"] = True
        PHASE45.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE45, originals["phase45"])

        # 12. Phase46 wallet safety violation.
        x = load(PHASE46)
        x["safety"]["walletUsed"] = True
        PHASE46.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE46, originals["phase46"])

        # 13. Phase47 signing safety violation.
        x = load(PHASE47)
        x["safety"]["signingPerformed"] = True
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, originals["phase47"])

        # 14. Phase48 broadcast safety violation.
        x = load(PHASE48)
        x["safety"]["broadcastPerformed"] = True
        PHASE48.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE48, originals["phase48"])

        # 15. Phase45 corrupt JSON.
        PHASE45.write_text("{corrupted")

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE45, originals["phase45"])

        # 16. Missing Phase48.
        PHASE48.unlink()

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE48, originals["phase48"])

        # 17. Corrupted checkpoint.
        CHECKPOINT.write_text("{corrupted")

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(CHECKPOINT, originals["checkpoint"])

        # 18. Deterministic digest.
        result = run()
        assert result.returncode == 0
        assert_verified()

        first = load(OUTPUT)["verification"]["temporalDigest"]

        result = run()
        assert result.returncode == 0
        assert_verified()

        second = load(OUTPUT)["verification"]["temporalDigest"]

        assert first == second
        assert len(first) == 64

        print("18/18 PASSED")

    finally:
        for name, target in originals.items():
            path = {
                "phase45": PHASE45,
                "phase46": PHASE46,
                "phase47": PHASE47,
                "phase48": PHASE48,
                "checkpoint": CHECKPOINT,
            }[name]
            restore(path, target)
