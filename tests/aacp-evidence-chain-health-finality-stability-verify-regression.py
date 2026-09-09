#!/usr/bin/env python3

import copy
import json
import subprocess
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]

SOURCE = (
    BASE
    / "src"
    / "aacp-evidence-chain-health-finality-stability-verify.py"
)

PHASE51 = (
    BASE
    / "provider-output"
    / "aacp-observer"
    / "latest-aacp-evidence-chain-health-cross-artifact-attestation-"
      "chain-finality-continuity-verify.json"
)

CHECKPOINT = (
    BASE
    / "provider-output"
    / "aacp-observer"
    / "aacp-evidence-chain-health-finality-stability-checkpoint.json"
)

OUTPUT = (
    BASE
    / "provider-output"
    / "aacp-observer"
    / "latest-aacp-evidence-chain-health-finality-stability-verify.json"
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


def clean():
    CHECKPOINT.unlink(missing_ok=True)
    OUTPUT.unlink(missing_ok=True)


def establish():
    clean()

    result = run_verifier()

    assert_true(result.returncode == 0, "establish exit")

    out = load(OUTPUT)

    assert_true(
        out["state"] == "CHECKPOINT_ESTABLISHED",
        "establish state",
    )
    assert_true(
        out["sourceState"] == "CHECKPOINT_ESTABLISHED",
        "establish sourceState",
    )
    assert_true(
        out["readiness"]["ready"] is False,
        "establish ready",
    )
    assert_true(
        out["verification"]["valid"] is True,
        "establish valid",
    )
    assert_true(
        out["verification"]["checkpoint"] == "ESTABLISHED",
        "establish checkpoint",
    )
    assert_true(
        out["verification"]["verifiedLayers"] == 0,
        "establish layers",
    )
    assert_true(
        out["errorCount"] == 0,
        "establish errors",
    )
    assert_true(
        CHECKPOINT.exists(),
        "checkpoint exists",
    )


def verify_normal():
    result = run_verifier()

    assert_true(result.returncode == 0, "normal exit")

    out = load(OUTPUT)

    assert_true(
        out["state"] == "VERIFIED_READ_ONLY",
        "normal state",
    )
    assert_true(
        out["sourceState"] == "VERIFIED_READ_ONLY",
        "normal sourceState",
    )
    assert_true(
        out["readiness"]["ready"] is True,
        "normal ready",
    )
    assert_true(
        out["verification"]["valid"] is True,
        "normal valid",
    )
    assert_true(
        out["verification"]["checkpoint"] == "VERIFIED",
        "normal checkpoint",
    )
    assert_true(
        out["verification"]["verifiedLayers"] == 1,
        "normal layers",
    )
    assert_true(
        out["errorCount"] == 0,
        "normal errors",
    )


def test_deterministic_digest():
    first = load(OUTPUT)["verification"]["stabilityDigest"]

    result = run_verifier()

    assert_true(result.returncode == 0, "deterministic exit")

    second = load(OUTPUT)["verification"]["stabilityDigest"]

    assert_true(
        first == second,
        "stability digest must be deterministic",
    )


def test_generated_at_only_change_is_ignored():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["generatedAt"] = "2099-01-01T00:00:00+00:00"

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode == 0,
        "generatedAt-only change must be ignored",
    )

    out = load(OUTPUT)

    assert_true(
        out["state"] == "VERIFIED_READ_ONLY",
        "generatedAt-only state",
    )

    save(PHASE51, original)

    assert_true(
        run_verifier().returncode == 0,
        "restore after generatedAt-only change",
    )


def test_state_drift():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["state"] = "BLOCKED"

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(result.returncode != 0, "state drift must block")

    out = load(OUTPUT)

    assert_true(
        out["state"] == "BLOCKED",
        "state drift blocked state",
    )

    save(PHASE51, original)


def test_source_state_drift():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["sourceState"] = "BLOCKED"

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "sourceState drift must block",
    )

    save(PHASE51, original)


def test_readiness_drift():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["readiness"]["ready"] = False

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "readiness drift must block",
    )

    save(PHASE51, original)


def test_validity_drift():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["verification"]["valid"] = False

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "validity drift must block",
    )

    save(PHASE51, original)


def test_checkpoint_drift():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["verification"]["checkpoint"] = "ESTABLISHED"

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "checkpoint drift must block",
    )

    save(PHASE51, original)


def test_continuity_digest_drift():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["verification"]["continuityDigest"] = "0" * 64

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "continuity digest drift must block",
    )

    save(PHASE51, original)


def test_execution_authorized():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["executionAuthorized"] = True

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "execution authorization must block",
    )

    save(PHASE51, original)


def test_wallet_violation():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["safety"]["walletUsed"] = True

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "wallet violation must block",
    )

    save(PHASE51, original)


def test_signing_violation():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["safety"]["signingPerformed"] = True

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "signing violation must block",
    )

    save(PHASE51, original)


def test_broadcast_violation():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["safety"]["broadcastPerformed"] = True

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "broadcast violation must block",
    )

    save(PHASE51, original)


def test_submission_violation():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["safety"]["submissionPerformed"] = True

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "submission violation must block",
    )

    save(PHASE51, original)


def test_error_count():
    original = load(PHASE51)

    modified = copy.deepcopy(original)
    modified["errorCount"] = 1

    save(PHASE51, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "errorCount violation must block",
    )

    save(PHASE51, original)


def test_corrupt_phase51():
    original = PHASE51.read_bytes()

    PHASE51.write_text(
        "{corrupted",
        encoding="utf-8",
    )

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "corrupt Phase51 must block",
    )

    out = load(OUTPUT)

    assert_true(
        out["state"] == "BLOCKED",
        "corrupt Phase51 state",
    )

    PHASE51.write_bytes(original)


def test_missing_phase51():
    original = PHASE51.read_bytes()

    PHASE51.unlink()

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "missing Phase51 must block",
    )

    PHASE51.write_bytes(original)


def test_checkpoint_digest_tampering():
    original = load(CHECKPOINT)

    modified = copy.deepcopy(original)
    modified["stabilityDigest"] = "0" * 64

    save(CHECKPOINT, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "checkpoint digest tampering must block",
    )

    save(CHECKPOINT, original)


def test_checkpoint_projection_tampering():
    original = load(CHECKPOINT)

    modified = copy.deepcopy(original)
    modified["stabilityProjection"]["mode"] = "MUTATED"

    save(CHECKPOINT, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "checkpoint projection tampering must block",
    )

    save(CHECKPOINT, original)


def test_checkpoint_type_tampering():
    original = load(CHECKPOINT)

    modified = copy.deepcopy(original)
    modified["type"] = "INVALID_TYPE"

    save(CHECKPOINT, modified)

    result = run_verifier()

    assert_true(
        result.returncode != 0,
        "checkpoint type tampering must block",
    )

    save(CHECKPOINT, original)


def main():
    tests = [
        establish,
        verify_normal,
        test_deterministic_digest,
        test_generated_at_only_change_is_ignored,
        test_state_drift,
        test_source_state_drift,
        test_readiness_drift,
        test_validity_drift,
        test_checkpoint_drift,
        test_continuity_digest_drift,
        test_execution_authorized,
        test_wallet_violation,
        test_signing_violation,
        test_broadcast_violation,
        test_submission_violation,
        test_error_count,
        test_corrupt_phase51,
        test_missing_phase51,
        test_checkpoint_digest_tampering,
        test_checkpoint_projection_tampering,
        test_checkpoint_type_tampering,
        verify_normal,
    ]

    passed = 0

    try:
        for test in tests:
            test()
            passed += 1
    finally:
        clean()

    print(f"{passed}/{len(tests)} PASSED")


if __name__ == "__main__":
    main()
