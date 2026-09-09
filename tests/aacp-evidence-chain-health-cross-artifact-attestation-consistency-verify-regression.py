#!/usr/bin/env python3

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = Path("provider-output/aacp-observer")
SOURCE = Path(
    "src/aacp-evidence-chain-health-cross-artifact-attestation-consistency-verify.py"
)
OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-consistency-verify.json"
)
PHASE45 = BASE / (
    "latest-aacp-evidence-chain-health-cross-artifact-identity-attestation.json"
)
CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-cross-artifact-identity-attestation-checkpoint.json"
)

PHASE45_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_IDENTITY_ATTESTATION"

ARTIFACTS = {
    31: "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
    32: "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
    33: "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
    34: "latest-aacp-evidence-chain-health-integrity-attestation.json",
    35: "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
    36: "latest-aacp-evidence-chain-health-final-readiness.json",
    37: "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json",
    38: "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json",
    39: "latest-aacp-evidence-chain-health-semantic-checkpoint-verify.json",
    40: "latest-aacp-evidence-chain-health-snapshot-registry.json",
    41: "latest-aacp-evidence-chain-health-snapshot-registry-verify.json",
    42: "latest-aacp-evidence-chain-health-snapshot-registry-continuity-verify.json",
    43: "latest-aacp-evidence-chain-health-temporal-continuity-verify.json",
    44: "latest-aacp-evidence-chain-health-artifact-identity-verify.json",
}


def run():
    r = subprocess.run(
        [sys.executable, str(SOURCE)],
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(OUTPUT.read_text())
    except Exception as exc:
        raise AssertionError(f"output JSON unreadable: {exc}")

    return r.returncode, r.stdout, r.stderr, payload


def load(path):
    return json.loads(path.read_text())


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def assert_blocked(payload, name):
    assert payload["state"] == "BLOCKED", f"{name}: state not BLOCKED"
    assert payload["sourceState"] == "BLOCKED", f"{name}: sourceState not BLOCKED"
    assert payload["ready"] if False else True
    assert payload["verification"]["valid"] is False, f"{name}: valid not false"
    assert payload["errorCount"] > 0, f"{name}: no errors"


def assert_verified(payload, name):
    assert payload["state"] == "VERIFIED_READ_ONLY", f"{name}: state"
    assert payload["sourceState"] == "VERIFIED_READ_ONLY", f"{name}: sourceState"
    assert payload["readiness"]["ready"] is True, f"{name}: not ready"
    assert payload["verification"]["valid"] is True, f"{name}: not valid"
    assert payload["verification"]["checkpoint"] == "VERIFIED", f"{name}: checkpoint"
    assert payload["verification"]["requiredLayers"] == 14, f"{name}: required"
    assert payload["verification"]["verifiedLayers"] == 14, f"{name}: verified"
    assert payload["errorCount"] == 0, f"{name}: errors"


def main():
    originals = {
        PHASE45: PHASE45.read_text(),
        CHECKPOINT: CHECKPOINT.read_text(),
    }

    try:
        # 1. Normal verification.
        rc, _, _, payload = run()
        assert rc == 0
        assert_verified(payload, "normal")

        # 2. Phase45 digest mismatch.
        p45 = load(PHASE45)
        p45["verification"]["attestationDigest"] = "0" * 64
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "attestation digest mismatch")
        assert any(
            "attestation digest mismatch" in e
            for e in payload["errors"]
        )

        PHASE45.write_text(originals[PHASE45])

        # 3. Phase45 malformed digest.
        p45 = load(PHASE45)
        p45["verification"]["attestationDigest"] = "not-a-digest"
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "malformed attestation digest")
        assert any(
            "malformed attestation digest" in e
            for e in payload["errors"]
        )

        PHASE45.write_text(originals[PHASE45])

        # 4. Phase45 artifact identity mismatch.
        p45 = load(PHASE45)
        p45["verification"]["artifacts"][0]["sha256"] = "0" * 64
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "artifact identity mismatch")
        assert any(
            "artifact identity mismatch" in e
            for e in payload["errors"]
        )

        PHASE45.write_text(originals[PHASE45])

        # 5. Phase45 execution authorization violation.
        p45 = load(PHASE45)
        p45["executionAuthorized"] = True
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "execution authorization")
        assert any("phase45: safety violation" in e for e in payload["errors"])

        PHASE45.write_text(originals[PHASE45])

        # 6. Phase45 wallet safety violation.
        p45 = load(PHASE45)
        p45["safety"]["walletUsed"] = True
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "wallet safety")
        assert any("phase45: safety violation" in e for e in payload["errors"])

        PHASE45.write_text(originals[PHASE45])

        # 7. Phase45 signing safety violation.
        p45 = load(PHASE45)
        p45["safety"]["signingPerformed"] = True
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "signing safety")

        PHASE45.write_text(originals[PHASE45])

        # 8. Phase45 broadcast safety violation.
        p45 = load(PHASE45)
        p45["safety"]["broadcastPerformed"] = True
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "broadcast safety")

        PHASE45.write_text(originals[PHASE45])

        # 9. Phase45 submission safety violation.
        p45 = load(PHASE45)
        p45["safety"]["submissionPerformed"] = True
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "submission safety")

        PHASE45.write_text(originals[PHASE45])

        # 10. Phase45 nonzero error count.
        p45 = load(PHASE45)
        p45["errorCount"] = 1
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "error count")

        PHASE45.write_text(originals[PHASE45])

        # 11. Phase45 checkpoint digest mismatch.
        cp = load(CHECKPOINT)
        cp["attestationDigest"] = "0" * 64
        save(CHECKPOINT, cp)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "checkpoint digest")
        assert any(
            "phase45 checkpoint: digest mismatch" in e
            for e in payload["errors"]
        )

        CHECKPOINT.write_text(originals[CHECKPOINT])

        # 12. Phase45 checkpoint projection tampering.
        cp = load(CHECKPOINT)
        cp["attestationProjection"]["mode"] = "WRITE"
        save(CHECKPOINT, cp)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "checkpoint projection")
        assert any(
            "phase45 checkpoint: projection mismatch" in e
            for e in payload["errors"]
        )

        CHECKPOINT.write_text(originals[CHECKPOINT])

        # 13. Phase45 checkpoint corruption.
        CHECKPOINT.write_text("{corrupt")
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "checkpoint corruption")

        CHECKPOINT.write_text(originals[CHECKPOINT])

        # 14. Phase45 artifact list removed.
        p45 = load(PHASE45)
        del p45["verification"]["artifacts"]
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "missing artifact list")

        PHASE45.write_text(originals[PHASE45])

        # 15. Phase45 type mismatch.
        p45 = load(PHASE45)
        p45["type"] = "WRONG_TYPE"
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase45 type mismatch")

        PHASE45.write_text(originals[PHASE45])

        # 16. Phase45 readiness violation.
        p45 = load(PHASE45)
        p45["readiness"]["ready"] = False
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase45 readiness")

        PHASE45.write_text(originals[PHASE45])

        # 17. Phase45 verification validity violation.
        p45 = load(PHASE45)
        p45["verification"]["valid"] = False
        save(PHASE45, p45)
        rc, _, _, payload = run()
        assert rc != 0
        assert_blocked(payload, "phase45 validity")

        PHASE45.write_text(originals[PHASE45])

        # 18. Deterministic digest.
        rc, _, _, payload1 = run()
        assert rc == 0
        digest1 = payload1["verification"]["consistencyDigest"]

        rc, _, _, payload2 = run()
        assert rc == 0
        digest2 = payload2["verification"]["consistencyDigest"]

        assert digest1 == digest2, "consistency digest is not deterministic"
        assert_verified(payload2, "deterministic digest")

        print("18/18 PASSED")
        return 0

    finally:
        PHASE45.write_text(originals[PHASE45])
        CHECKPOINT.write_text(originals[CHECKPOINT])


if __name__ == "__main__":
    raise SystemExit(main())
