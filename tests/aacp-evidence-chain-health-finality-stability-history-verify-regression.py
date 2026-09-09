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
    / "aacp-evidence-chain-health-finality-stability-history-verify.py"
)

PHASE52 = (
    BASE
    / "provider-output"
    / "aacp-observer"
    / "latest-aacp-evidence-chain-health-finality-stability-verify.json"
)

HISTORY = (
    BASE
    / "provider-output"
    / "aacp-observer"
    / "aacp-evidence-chain-health-finality-stability-history.json"
)

OUTPUT = (
    BASE
    / "provider-output"
    / "aacp-observer"
    / "latest-aacp-evidence-chain-health-finality-stability-history-verify.json"
)


def run():
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


def clean():
    HISTORY.unlink(missing_ok=True)
    OUTPUT.unlink(missing_ok=True)


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def establish():
    clean()

    result = run()
    assert_true(result.returncode == 0, "establish exit")

    out = load(OUTPUT)

    assert_true(out["state"] == "HISTORY_ESTABLISHED", "state")
    assert_true(out["sourceState"] == "HISTORY_ESTABLISHED", "source")
    assert_true(out["readiness"]["ready"] is False, "ready")
    assert_true(out["verification"]["valid"] is True, "valid")
    assert_true(out["verification"]["checkpoint"] == "ESTABLISHED", "checkpoint")
    assert_true(out["verification"]["observedObservations"] == 1, "observations")
    assert_true(out["errorCount"] == 0, "errors")
    assert_true(HISTORY.exists(), "history missing")


def progress():
    result = run()
    assert_true(result.returncode == 0, "progress exit")

    out = load(OUTPUT)

    assert_true(out["state"] == "HISTORY_PROGRESS", "progress state")
    assert_true(out["readiness"]["ready"] is False, "progress ready")
    assert_true(out["verification"]["valid"] is True, "progress valid")
    assert_true(out["verification"]["checkpoint"] == "IN_PROGRESS", "progress checkpoint")
    assert_true(out["verification"]["observedObservations"] == 2, "progress observations")


def complete():
    result = run()
    assert_true(result.returncode == 0, "complete exit")

    out = load(OUTPUT)

    assert_true(out["state"] == "VERIFIED_READ_ONLY", "complete state")
    assert_true(out["sourceState"] == "VERIFIED_READ_ONLY", "complete source")
    assert_true(out["readiness"]["ready"] is True, "complete ready")
    assert_true(out["verification"]["valid"] is True, "complete valid")
    assert_true(out["verification"]["checkpoint"] == "VERIFIED", "complete checkpoint")
    assert_true(out["verification"]["observedObservations"] == 3, "complete observations")
    assert_true(out["errorCount"] == 0, "complete errors")


def test_deterministic_digest():
    first = load(OUTPUT)["verification"]["historyDigest"]

    result = run()
    assert_true(result.returncode != 0, "completed history must not silently append")

    out = load(OUTPUT)
    assert_true(out["state"] == "BLOCKED", "completed history blocked")

    history = load(HISTORY)
    assert_true(history["historyDigest"] == first, "history digest changed")


def test_stability_digest_consistency():
    history = load(HISTORY)
    observations = history["observations"]

    assert_true(len(observations) == 3, "history count")
    digests = {x["stabilityDigest"] for x in observations}

    assert_true(len(digests) == 1, "stability digest drift")


def test_generated_at_history_change_ignored():
    history = load(HISTORY)

    modified = copy.deepcopy(history)

    for item in modified["observations"]:
        item["generatedAt"] = "2099-01-01T00:00:00+00:00"

    modified["historyProjection"]["observations"] = modified["observations"]

    import hashlib

    canonical = json.dumps(
        modified["historyProjection"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    modified["historyDigest"] = hashlib.sha256(
        canonical.encode()
    ).hexdigest()

    save(HISTORY, modified)

    result = run()
    assert_true(result.returncode != 0, "history generatedAt mutation should affect integrity")

    save(HISTORY, history)


def test_history_digest_tampering():
    original = load(HISTORY)
    modified = copy.deepcopy(original)
    modified["historyDigest"] = "0" * 64

    save(HISTORY, modified)

    result = run()
    assert_true(result.returncode != 0, "digest tampering must block")

    save(HISTORY, original)


def test_history_projection_tampering():
    original = load(HISTORY)
    modified = copy.deepcopy(original)
    modified["historyProjection"]["mode"] = "MUTATED"

    save(HISTORY, modified)

    result = run()
    assert_true(result.returncode != 0, "projection tampering must block")

    save(HISTORY, original)


def test_history_type_tampering():
    original = load(HISTORY)
    modified = copy.deepcopy(original)
    modified["type"] = "INVALID"

    save(HISTORY, modified)

    result = run()
    assert_true(result.returncode != 0, "type tampering must block")

    save(HISTORY, original)


def test_required_observations_tampering():
    original = load(HISTORY)
    modified = copy.deepcopy(original)
    modified["requiredObservations"] = 99

    save(HISTORY, modified)

    result = run()
    assert_true(result.returncode != 0, "required observation tampering")

    save(HISTORY, original)


def test_phase52_state_drift():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["state"] = "BLOCKED"

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "state drift")

    save(PHASE52, original)


def test_phase52_readiness_drift():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["readiness"]["ready"] = False

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "readiness drift")

    save(PHASE52, original)


def test_phase52_validity_drift():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["verification"]["valid"] = False

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "validity drift")

    save(PHASE52, original)


def test_phase52_checkpoint_drift():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["verification"]["checkpoint"] = "INVALID"

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "checkpoint drift")

    save(PHASE52, original)


def test_phase52_digest_drift():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["verification"]["stabilityDigest"] = "0" * 64

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "Phase52 digest drift")

    save(PHASE52, original)


def test_execution_authorized():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["executionAuthorized"] = True

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "execution authorization")

    save(PHASE52, original)


def test_wallet_violation():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["safety"]["walletUsed"] = True

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "wallet violation")

    save(PHASE52, original)


def test_signing_violation():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["safety"]["signingPerformed"] = True

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "signing violation")

    save(PHASE52, original)


def test_broadcast_violation():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["safety"]["broadcastPerformed"] = True

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "broadcast violation")

    save(PHASE52, original)


def test_submission_violation():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["safety"]["submissionPerformed"] = True

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "submission violation")

    save(PHASE52, original)


def test_error_count_violation():
    original = load(PHASE52)
    modified = copy.deepcopy(original)
    modified["errorCount"] = 1

    save(PHASE52, modified)

    result = run()
    assert_true(result.returncode != 0, "errorCount violation")

    save(PHASE52, original)


def test_corrupt_phase52():
    original = PHASE52.read_bytes()

    PHASE52.write_text("{corrupt", encoding="utf-8")

    result = run()
    assert_true(result.returncode != 0, "corrupt Phase52")

    PHASE52.write_bytes(original)


def test_missing_phase52():
    original = PHASE52.read_bytes()
    PHASE52.unlink()

    result = run()
    assert_true(result.returncode != 0, "missing Phase52")

    PHASE52.write_bytes(original)


def test_corrupt_history():
    original = HISTORY.read_bytes()

    HISTORY.write_text("{corrupt", encoding="utf-8")

    result = run()
    assert_true(result.returncode != 0, "corrupt history")

    HISTORY.write_bytes(original)


def main():
    tests = [
        establish,
        progress,
        complete,
        test_deterministic_digest,
        test_stability_digest_consistency,
        test_generated_at_history_change_ignored,
        test_history_digest_tampering,
        test_history_projection_tampering,
        test_history_type_tampering,
        test_required_observations_tampering,
        test_phase52_state_drift,
        test_phase52_readiness_drift,
        test_phase52_validity_drift,
        test_phase52_checkpoint_drift,
        test_phase52_digest_drift,
        test_execution_authorized,
        test_wallet_violation,
        test_signing_violation,
        test_broadcast_violation,
        test_submission_violation,
        test_error_count_violation,
        test_corrupt_phase52,
        test_missing_phase52,
        test_corrupt_history,
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
