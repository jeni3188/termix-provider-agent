#!/usr/bin/env python3

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
SOURCE = (
    BASE
    / "src"
    / "aacp-evidence-chain-health-cross-artifact-attestation-chain-finality-continuity-verify.py"
)

PHASE50 = (
    BASE
    / "provider-output"
    / "aacp-observer"
    / "latest-aacp-evidence-chain-health-cross-artifact-attestation-chain-finality-verify.json"
)

CHECKPOINT = (
    BASE
    / "provider-output"
    / "aacp-observer"
    / "aacp-evidence-chain-health-cross-artifact-attestation-chain-finality-continuity-checkpoint.json"
)

OUTPUT = (
    BASE
    / "provider-output"
    / "aacp-observer"
    / "latest-aacp-evidence-chain-health-cross-artifact-attestation-chain-finality-continuity-verify.json"
)


def run_verifier():
    return subprocess.run(
        [sys.executable, str(SOURCE)],
        cwd=BASE,
        text=True,
        capture_output=True,
    )


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, obj):
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def clean_state():
    CHECKPOINT.unlink(missing_ok=True)
    OUTPUT.unlink(missing_ok=True)


def establish():
    clean_state()
    result = run_verifier()
    assert_true(result.returncode == 0, "first run must exit 0")
    out = load(OUTPUT)
    assert_true(
        out["state"] == "CHECKPOINT_ESTABLISHED",
        "first state must establish checkpoint",
    )
    assert_true(out["verification"]["verifiedLayers"] == 0, "first verifiedLayers")
    assert_true(out["verification"]["valid"] is True, "first valid")
    assert_true(out["readiness"]["ready"] is False, "first readiness")
    assert_true(CHECKPOINT.exists(), "checkpoint must exist")


def verify_normal():
    result = run_verifier()
    assert_true(result.returncode == 0, "normal continuity must exit 0")
    out = load(OUTPUT)
    assert_true(out["state"] == "VERIFIED_READ_ONLY", "normal state")
    assert_true(out["sourceState"] == "VERIFIED_READ_ONLY", "normal sourceState")
    assert_true(out["readiness"]["ready"] is True, "normal ready")
    assert_true(out["verification"]["valid"] is True, "normal valid")
    assert_true(out["verification"]["checkpoint"] == "VERIFIED", "normal checkpoint")
    assert_true(out["verification"]["verifiedLayers"] == 1, "normal verifiedLayers")
    assert_true(out["errorCount"] == 0, "normal errors")


def test_deterministic_digest():
    first = load(OUTPUT)["verification"]["continuityDigest"]
    result = run_verifier()
    assert_true(result.returncode == 0, "deterministic rerun")
    second = load(OUTPUT)["verification"]["continuityDigest"]
    assert_true(first == second, "digest must be deterministic")


def test_phase50_generated_at_change_is_ignored():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["generatedAt"] = "2099-01-01T00:00:00+00:00"
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode == 0, "generatedAt-only drift must be ignored")
    out = load(OUTPUT)
    assert_true(
        out["state"] == "VERIFIED_READ_ONLY",
        "generatedAt-only drift state",
    )
    assert_true(
        out["verification"]["valid"] is True,
        "generatedAt-only drift valid",
    )
    assert_true(
        out["verification"]["checkpoint"] == "VERIFIED",
        "generatedAt-only drift checkpoint",
    )

    save(PHASE50, original)
    assert_true(
        run_verifier().returncode == 0,
        "restore after generatedAt-only drift",
    )


def test_phase50_missing():
    original = PHASE50.read_bytes()
    PHASE50.unlink()

    result = run_verifier()
    assert_true(result.returncode != 0, "missing Phase50 must block")
    out = load(OUTPUT)
    assert_true(out["state"] == "BLOCKED", "missing Phase50 state")

    PHASE50.write_bytes(original)


def test_phase50_corrupt():
    original = PHASE50.read_bytes()
    PHASE50.write_text("{corrupt", encoding="utf-8")

    result = run_verifier()
    assert_true(result.returncode != 0, "corrupt Phase50 must block")
    out = load(OUTPUT)
    assert_true(out["state"] == "BLOCKED", "corrupt Phase50 state")

    PHASE50.write_bytes(original)


def test_phase50_not_ready():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["readiness"]["ready"] = False
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "not-ready Phase50 must block")
    out = load(OUTPUT)
    assert_true(out["state"] == "BLOCKED", "not-ready state")

    save(PHASE50, original)


def test_phase50_invalid():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["verification"]["valid"] = False
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "invalid Phase50 must block")

    save(PHASE50, original)


def test_phase50_checkpoint_invalid():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["verification"]["checkpoint"] = "ESTABLISHED"
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "invalid upstream checkpoint must block")

    save(PHASE50, original)


def test_execution_authorized():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["executionAuthorized"] = True
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "execution authorization must block")

    save(PHASE50, original)


def test_wallet_safety():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["safety"]["walletUsed"] = True
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "wallet violation must block")

    save(PHASE50, original)


def test_signing_safety():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["safety"]["signingPerformed"] = True
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "signing violation must block")

    save(PHASE50, original)


def test_broadcast_safety():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["safety"]["broadcastPerformed"] = True
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "broadcast violation must block")

    save(PHASE50, original)


def test_submission_safety():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["safety"]["submissionPerformed"] = True
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "submission violation must block")

    save(PHASE50, original)


def test_error_count():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["errorCount"] = 1
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "nonzero errorCount must block")

    save(PHASE50, original)


def test_finality_digest_invalid():
    original = load(PHASE50)
    modified = copy.deepcopy(original)
    modified["verification"]["finalityDigest"] = "invalid"
    save(PHASE50, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "invalid finality digest must block")

    save(PHASE50, original)


def test_checkpoint_digest_tampering():
    original = load(CHECKPOINT)
    modified = copy.deepcopy(original)
    modified["continuityDigest"] = "0" * 64
    save(CHECKPOINT, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "checkpoint digest tampering must block")

    save(CHECKPOINT, original)


def test_checkpoint_projection_tampering():
    original = load(CHECKPOINT)
    modified = copy.deepcopy(original)
    modified["continuityProjection"]["mode"] = "MUTATED"
    save(CHECKPOINT, modified)

    result = run_verifier()
    assert_true(result.returncode != 0, "checkpoint projection tampering must block")

    save(CHECKPOINT, original)


def test_checkpoint_missing():
    original = CHECKPOINT.read_bytes()
    CHECKPOINT.unlink()

    result = run_verifier()
    assert_true(result.returncode == 0, "missing checkpoint should establish")
    out = load(OUTPUT)
    assert_true(
        out["state"] == "CHECKPOINT_ESTABLISHED",
        "missing checkpoint state",
    )

    # Recreate and verify continuity.
    result = run_verifier()
    assert_true(result.returncode == 0, "recreated checkpoint verification")

    CHECKPOINT.write_bytes(original)


def main():
    tests = [
        establish,
        verify_normal,
        test_deterministic_digest,
        test_phase50_generated_at_change_is_ignored,
        test_phase50_missing,
        test_phase50_corrupt,
        test_phase50_not_ready,
        test_phase50_invalid,
        test_phase50_checkpoint_invalid,
        test_execution_authorized,
        test_wallet_safety,
        test_signing_safety,
        test_broadcast_safety,
        test_submission_safety,
        test_error_count,
        test_finality_digest_invalid,
        test_checkpoint_digest_tampering,
        test_checkpoint_projection_tampering,
        test_checkpoint_missing,
        verify_normal,
    ]

    passed = 0

    try:
        for test in tests:
            test()
            passed += 1
    finally:
        clean_state()

    print(f"{passed}/{len(tests)} PASSED")


if __name__ == "__main__":
    main()
