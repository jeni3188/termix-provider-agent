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
    "cross-artifact-attestation-drift-continuity-verify.py"
)

PHASE47 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-drift-verify.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-"
    "cross-artifact-attestation-drift-continuity-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-drift-continuity-verify.json"
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
    assert x["verification"]["requiredLayers"] == 14
    assert x["verification"]["verifiedLayers"] == 14
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

    phase47_backup = backup(PHASE47, tmp)
    checkpoint_backup = backup(CHECKPOINT, tmp)

    try:
        # 1. Normal repeat verification.
        result = run()
        assert result.returncode == 0
        assert_verified()

        # 2. Phase47 driftDigest tampering.
        x = load(PHASE47)
        x["verification"]["driftDigest"] = "0" * 64
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 3. Phase47 state violation.
        x = load(PHASE47)
        x["state"] = "BLOCKED"
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 4. Phase47 sourceState violation.
        x = load(PHASE47)
        x["sourceState"] = "BLOCKED"
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 5. Phase47 readiness violation.
        x = load(PHASE47)
        x["readiness"]["ready"] = False
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 6. Phase47 validity violation.
        x = load(PHASE47)
        x["verification"]["valid"] = False
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 7. Phase47 execution authorization violation.
        x = load(PHASE47)
        x["executionAuthorized"] = True
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 8. Phase47 wallet safety violation.
        x = load(PHASE47)
        x["safety"]["walletUsed"] = True
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 9. Phase47 signing safety violation.
        x = load(PHASE47)
        x["safety"]["signingPerformed"] = True
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 10. Phase47 broadcast safety violation.
        x = load(PHASE47)
        x["safety"]["broadcastPerformed"] = True
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 11. Phase47 submission safety violation.
        x = load(PHASE47)
        x["safety"]["submissionPerformed"] = True
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 12. Phase47 non-zero errorCount.
        x = load(PHASE47)
        x["errorCount"] = 1
        PHASE47.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 13. Phase47 corrupt JSON.
        PHASE47.write_text("{corrupted")

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 14. Missing Phase47.
        PHASE47.unlink()

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(PHASE47, phase47_backup)

        # 15. Corrupt checkpoint.
        CHECKPOINT.write_text("{corrupted")

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(CHECKPOINT, checkpoint_backup)

        # 16. Checkpoint digest tampering.
        x = load(CHECKPOINT)
        x["continuityDigest"] = "0" * 64
        CHECKPOINT.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(CHECKPOINT, checkpoint_backup)

        # 17. Checkpoint projection tampering.
        x = load(CHECKPOINT)
        x["continuityProjection"]["mode"] = "EXECUTION"
        CHECKPOINT.write_text(json.dumps(x, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        restore(CHECKPOINT, checkpoint_backup)

        # 18. Deterministic digest.
        result = run()
        assert result.returncode == 0
        assert_verified()

        first = load(OUTPUT)["verification"]["continuityDigest"]

        result = run()
        assert result.returncode == 0
        assert_verified()

        second = load(OUTPUT)["verification"]["continuityDigest"]

        assert first == second
        assert len(first) == 64

        print("18/18 PASSED")

    finally:
        restore(PHASE47, phase47_backup)
        restore(CHECKPOINT, checkpoint_backup)
