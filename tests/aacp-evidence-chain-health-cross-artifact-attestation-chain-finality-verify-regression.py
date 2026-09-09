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
    "cross-artifact-attestation-chain-finality-verify.py"
)

PHASES = {
    45: BASE / (
        "latest-aacp-evidence-chain-health-"
        "cross-artifact-identity-attestation.json"
    ),
    46: BASE / (
        "latest-aacp-evidence-chain-health-"
        "cross-artifact-attestation-consistency-verify.json"
    ),
    47: BASE / (
        "latest-aacp-evidence-chain-health-"
        "cross-artifact-attestation-drift-verify.json"
    ),
    48: BASE / (
        "latest-aacp-evidence-chain-health-"
        "cross-artifact-attestation-drift-continuity-verify.json"
    ),
    49: BASE / (
        "latest-aacp-evidence-chain-health-"
        "cross-artifact-attestation-temporal-continuity-verify.json"
    ),
}

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-"
    "cross-artifact-attestation-chain-finality-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-chain-finality-verify.json"
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
    obj = load(OUTPUT)

    assert obj["state"] == "VERIFIED_READ_ONLY"
    assert obj["sourceState"] == "VERIFIED_READ_ONLY"
    assert obj["readiness"]["ready"] is True
    assert obj["verification"]["valid"] is True
    assert obj["verification"]["checkpoint"] == "VERIFIED"
    assert obj["verification"]["requiredLayers"] == 5
    assert obj["verification"]["verifiedLayers"] == 5
    assert obj["errorCount"] == 0


def assert_blocked():
    obj = load(OUTPUT)

    assert obj["state"] == "BLOCKED"
    assert obj["sourceState"] == "BLOCKED"
    assert obj["readiness"]["ready"] is False
    assert obj["verification"]["valid"] is False
    assert obj["verification"]["checkpoint"] == "BLOCKED"
    assert obj["verification"]["verifiedLayers"] == 0
    assert obj["errorCount"] > 0


with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)

    originals = {}

    for phase, path in PHASES.items():
        backup = tmp / path.name
        shutil.copy2(path, backup)
        originals[phase] = backup

    checkpoint_backup = tmp / CHECKPOINT.name
    shutil.copy2(CHECKPOINT, checkpoint_backup)

    try:
        # 1. Normal verification.
        result = run()
        assert result.returncode == 0
        assert_verified()

        # 2. Phase45 missing.
        PHASES[45].unlink()

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[45], PHASES[45])

        # 3. Phase46 missing.
        PHASES[46].unlink()

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[46], PHASES[46])

        # 4. Phase47 missing.
        PHASES[47].unlink()

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[47], PHASES[47])

        # 5. Phase48 missing.
        PHASES[48].unlink()

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[48], PHASES[48])

        # 6. Phase49 missing.
        PHASES[49].unlink()

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[49], PHASES[49])

        # 7. Corrupted Phase49.
        PHASES[49].write_text("{corrupted")

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[49], PHASES[49])

        # 8. Phase45 type violation.
        obj = load(PHASES[45])
        obj["type"] = "WRONG_TYPE"
        PHASES[45].write_text(json.dumps(obj, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[45], PHASES[45])

        # 9. Phase46 execution authorization violation.
        obj = load(PHASES[46])
        obj["executionAuthorized"] = True
        PHASES[46].write_text(json.dumps(obj, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[46], PHASES[46])

        # 10. Phase47 wallet safety violation.
        obj = load(PHASES[47])
        obj["safety"]["walletUsed"] = True
        PHASES[47].write_text(json.dumps(obj, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[47], PHASES[47])

        # 11. Phase48 signing safety violation.
        obj = load(PHASES[48])
        obj["safety"]["signingPerformed"] = True
        PHASES[48].write_text(json.dumps(obj, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[48], PHASES[48])

        # 12. Phase49 broadcast safety violation.
        obj = load(PHASES[49])
        obj["safety"]["broadcastPerformed"] = True
        PHASES[49].write_text(json.dumps(obj, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[49], PHASES[49])

        # 13. Phase49 submission safety violation.
        obj = load(PHASES[49])
        obj["safety"]["submissionPerformed"] = True
        PHASES[49].write_text(json.dumps(obj, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[49], PHASES[49])

        # 14. Phase48 validity violation.
        obj = load(PHASES[48])
        obj["verification"]["valid"] = False
        PHASES[48].write_text(json.dumps(obj, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[48], PHASES[48])

        # 15. Phase49 readiness violation.
        obj = load(PHASES[49])
        obj["readiness"]["ready"] = False
        PHASES[49].write_text(json.dumps(obj, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[49], PHASES[49])

        # 16. Phase49 digest malformed.
        obj = load(PHASES[49])
        obj["verification"]["temporalDigest"] = "bad"
        PHASES[49].write_text(json.dumps(obj, indent=2, sort_keys=True))

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(originals[49], PHASES[49])

        # 17. Checkpoint digest tampering.
        checkpoint = load(CHECKPOINT)
        checkpoint["finalityDigest"] = "0" * 64
        CHECKPOINT.write_text(
            json.dumps(checkpoint, indent=2, sort_keys=True)
        )

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(checkpoint_backup, CHECKPOINT)

        # 18. Checkpoint projection tampering.
        checkpoint = load(CHECKPOINT)
        checkpoint["finalityProjection"]["mode"] = "WRITE"
        CHECKPOINT.write_text(
            json.dumps(checkpoint, indent=2, sort_keys=True)
        )

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(checkpoint_backup, CHECKPOINT)

        # 19. Checkpoint type tampering.
        checkpoint = load(CHECKPOINT)
        checkpoint["type"] = "WRONG_TYPE"
        CHECKPOINT.write_text(
            json.dumps(checkpoint, indent=2, sort_keys=True)
        )

        result = run()
        assert result.returncode != 0
        assert_blocked()

        shutil.copy2(checkpoint_backup, CHECKPOINT)

        # 20. Deterministic finality digest.
        result = run()
        assert result.returncode == 0
        assert_verified()

        first = load(OUTPUT)["verification"]["finalityDigest"]

        result = run()
        assert result.returncode == 0
        assert_verified()

        second = load(OUTPUT)["verification"]["finalityDigest"]

        assert first == second
        assert len(first) == 64

        print("20/20 PASSED")

    finally:
        for phase, backup in originals.items():
            shutil.copy2(backup, PHASES[phase])

        shutil.copy2(checkpoint_backup, CHECKPOINT)
