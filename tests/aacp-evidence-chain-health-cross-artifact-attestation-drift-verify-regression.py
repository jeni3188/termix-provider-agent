#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

BASE = Path("provider-output/aacp-observer")

SOURCE = BASE.parent.parent / "src" / (
    "aacp-evidence-chain-health-cross-artifact-attestation-drift-verify.py"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-drift-verify.json"
)

PHASE45 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-identity-attestation.json"
)

PHASE46 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-consistency-verify.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-cross-artifact-attestation-"
    "drift-checkpoint.json"
)


def read(path):
    return json.loads(path.read_text())


def write(path, obj):
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    )


def run():
    r = subprocess.run(
        [sys.executable, str(SOURCE)],
        capture_output=True,
        text=True,
    )

    payload = read(OUTPUT)

    return r.returncode, r.stdout, r.stderr, payload


def assert_verified(payload, name):
    assert payload["state"] == "VERIFIED_READ_ONLY", (
        f"{name}: state"
    )
    assert payload["sourceState"] == "VERIFIED_READ_ONLY", (
        f"{name}: sourceState"
    )
    assert payload["readiness"]["ready"] is True, (
        f"{name}: readiness"
    )
    assert payload["verification"]["valid"] is True, (
        f"{name}: validity"
    )
    assert payload["verification"]["checkpoint"] == "VERIFIED", (
        f"{name}: checkpoint"
    )
    assert payload["verification"]["requiredLayers"] == 14, (
        f"{name}: required layers"
    )
    assert payload["verification"]["verifiedLayers"] == 14, (
        f"{name}: verified layers"
    )
    assert payload["errorCount"] == 0, (
        f"{name}: errors"
    )


def assert_blocked(payload, name):
    assert payload["state"] == "BLOCKED", (
        f"{name}: state not BLOCKED"
    )
    assert payload["sourceState"] == "BLOCKED", (
        f"{name}: sourceState not BLOCKED"
    )
    assert payload["readiness"]["ready"] is False, (
        f"{name}: readiness"
    )
    assert payload["verification"]["valid"] is False, (
        f"{name}: validity"
    )
    assert payload["verification"]["verifiedLayers"] == 0, (
        f"{name}: verified layers"
    )
    assert payload["errorCount"] > 0, (
        f"{name}: no errors"
    )


def restore():
    PHASE45.write_text(PHASE45_ORIGINAL)
    PHASE46.write_text(PHASE46_ORIGINAL)
    CHECKPOINT.write_text(CHECKPOINT_ORIGINAL)


PHASE45_ORIGINAL = PHASE45.read_text()
PHASE46_ORIGINAL = PHASE46.read_text()
CHECKPOINT_ORIGINAL = CHECKPOINT.read_text()


def main():
    try:
        # 1. Normal repeat verification.
        rc, _, _, payload = run()
        assert rc == 0
        assert_verified(payload, "normal")

        # 2. Phase45 artifact SHA drift.
        p45 = read(PHASE45)
        p45["verification"]["artifacts"][0]["sha256"] = "0" * 64
        write(PHASE45, p45)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase45 artifact sha drift")
        assert any(
            "phase31: artifact identity drift" in e
            or "artifact identity projection drift" in e
            for e in payload["errors"]
        )

        restore()

        # 3. Phase45 attestation digest drift.
        p45 = read(PHASE45)
        p45["verification"]["attestationDigest"] = "0" * 64
        write(PHASE45, p45)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase45 attestation drift")

        restore()

        # 4. Phase46 consistency digest drift.
        p46 = read(PHASE46)
        p46["verification"]["consistencyDigest"] = "0" * 64
        write(PHASE46, p46)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase46 consistency drift")
        assert any(
            "checkpoint: drift detected" in e
            for e in payload["errors"]
        )

        restore()

        # 5. Phase45 missing.
        saved = PHASE45.read_text()
        PHASE45.unlink()

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase45 missing")

        PHASE45.write_text(saved)

        # 6. Phase46 missing.
        saved = PHASE46.read_text()
        PHASE46.unlink()

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase46 missing")

        PHASE46.write_text(saved)

        # 7. Phase45 corrupt JSON.
        saved = PHASE45.read_text()
        PHASE45.write_text("{corrupt")

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase45 corrupt")

        PHASE45.write_text(saved)

        # 8. Phase46 corrupt JSON.
        saved = PHASE46.read_text()
        PHASE46.write_text("{corrupt")

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase46 corrupt")

        PHASE46.write_text(saved)

        # 9. Checkpoint corrupt JSON.
        saved = CHECKPOINT.read_text()
        CHECKPOINT.write_text("{corrupt")

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "checkpoint corrupt")

        CHECKPOINT.write_text(saved)

        # 10. Checkpoint digest tampering.
        cp = read(CHECKPOINT)
        cp["driftDigest"] = "0" * 64
        write(CHECKPOINT, cp)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "checkpoint digest tampering")
        assert any(
            "checkpoint: drift detected" in e
            for e in payload["errors"]
        )

        restore()

        # 11. Checkpoint projection tampering.
        cp = read(CHECKPOINT)
        cp["driftProjection"]["artifacts"][0]["sha256"] = "0" * 64
        write(CHECKPOINT, cp)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "checkpoint projection tampering")
        assert any(
            "checkpoint: projection drift" in e
            for e in payload["errors"]
        )

        restore()

        # 12. Phase46 execution authorization violation.
        p46 = read(PHASE46)
        p46["executionAuthorized"] = True
        write(PHASE46, p46)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "execution authorization")
        assert any(
            "phase46: safety violation" in e
            for e in payload["errors"]
        )

        restore()

        # 13. Phase46 wallet violation.
        p46 = read(PHASE46)
        p46["safety"]["walletAccessed"] = True
        write(PHASE46, p46)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "wallet violation")

        restore()

        # 14. Phase46 signing violation.
        p46 = read(PHASE46)
        p46["safety"]["signingPerformed"] = True
        write(PHASE46, p46)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "signing violation")

        restore()

        # 15. Phase46 broadcast violation.
        p46 = read(PHASE46)
        p46["safety"]["broadcastPerformed"] = True
        write(PHASE46, p46)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "broadcast violation")

        restore()

        # 16. Phase46 submission violation.
        p46 = read(PHASE46)
        p46["safety"]["submissionPerformed"] = True
        write(PHASE46, p46)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "submission violation")

        restore()

        # 17. Phase45 malformed digest.
        p45 = read(PHASE45)
        p45["verification"]["attestationDigest"] = "bad"
        write(PHASE45, p45)

        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "malformed phase45 digest")
        assert any(
            "phase45: malformed attestation digest" in e
            for e in payload["errors"]
        )

        restore()

        # 18. Deterministic digest.
        rc, _, _, payload1 = run()
        assert rc == 0
        digest1 = payload1["verification"]["driftDigest"]

        rc, _, _, payload2 = run()
        assert rc == 0
        digest2 = payload2["verification"]["driftDigest"]

        assert digest1 == digest2, (
            "drift digest is not deterministic"
        )

        assert_verified(payload2, "deterministic digest")

        print("18/18 PASSED")
        return 0

    finally:
        restore()


if __name__ == "__main__":
    raise SystemExit(main())
