#!/usr/bin/env python3

import copy
import json
import os
import shutil
import subprocess
import tempfile

SRC = (
    "src/aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-verify.py"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_VERIFY"
)

PHASE57_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CONTINUITY_DRIFT_CONTINUITY_STABILITY_VERIFY"
)


def run(tmp, expect=0):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    result = subprocess.run(
        ["python", SRC],
        cwd=tmp,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == expect, (
        f"expected {expect}, got {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    return result


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")


def setup():
    tmp = tempfile.mkdtemp(prefix="phase58-regression-")
    os.makedirs(
        os.path.join(tmp, "provider-output", "aacp-observer"),
        exist_ok=True,
    )

    target = os.path.join(tmp, SRC)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy2(SRC, target)

    phase57_path = os.path.join(
        tmp,
        "provider-output",
        "aacp-observer",
        "latest-aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-verify.json",
    )

    phase57 = {
        "version": 1,
        "type": PHASE57_TYPE,
        "generatedAt": "2026-09-09T10:00:00+00:00",
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "executionAuthorized": False,
        "safety": {
            "broadcastPerformed": False,
            "postPerformed": False,
            "privateKeyAccessed": False,
            "signingPerformed": False,
            "submissionPerformed": False,
            "walletUsed": False,
        },
        "sideEffects": {
            "broadcast": False,
            "filesystemRead": True,
            "filesystemWrite": True,
            "networkAccess": False,
            "signing": False,
            "submission": False,
            "walletAccess": False,
        },
        "readiness": {"ready": True},
        "verification": {
            "valid": True,
            "requiredLayers": 1,
            "verifiedLayers": 1,
            "checkpoint": "VERIFIED",
            "stabilityDigest": "a" * 64,
            "sourceContinuityDigest": "b" * 64,
        },
        "errors": [],
        "errorCount": 0,
        "policy": {
            "mode": "READ_ONLY",
            "failClosed": True,
        },
    }

    write(phase57_path, phase57)
    return tmp, phase57_path, phase57


def test():
    tmp, phase57_path, phase57 = setup()

    output_path = os.path.join(
        tmp,
        "provider-output",
        "aacp-observer",
        "latest-aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-verify.json",
    )

    history_path = os.path.join(
        tmp,
        "provider-output",
        "aacp-observer",
        "aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history.json",
    )

    # 1. First observation establishes history.
    r = run(tmp)
    assert "HISTORY: HISTORY_ESTABLISHED" in r.stdout
    output = load(output_path)
    assert output["verification"]["observedObservations"] == 1
    assert output["verification"]["valid"] is True

    # 2. Second observation progresses history.
    phase57["generatedAt"] = "2026-09-09T10:01:00+00:00"
    write(phase57_path, phase57)
    r = run(tmp)
    assert "HISTORY: HISTORY_PROGRESS" in r.stdout
    output = load(output_path)
    assert output["verification"]["observedObservations"] == 2

    # 3. Third observation verifies history.
    phase57["generatedAt"] = "2026-09-09T10:02:00+00:00"
    write(phase57_path, phase57)
    r = run(tmp)
    assert "HISTORY: HISTORY_PROGRESS" in r.stdout
    output = load(output_path)
    assert output["verification"]["observedObservations"] == 3

    # 4. Stable fourth execution verifies without appending.
    phase57["generatedAt"] = "2026-09-09T10:03:00+00:00"
    write(phase57_path, phase57)
    r = run(tmp)
    assert "HISTORY: VERIFIED_READ_ONLY" in r.stdout
    output = load(output_path)
    assert output["verification"]["observedObservations"] == 3

    history = load(history_path)
    assert len(history["observations"]) == 3

    # 5. Phase57 generatedAt-only change is ignored.
    phase57["generatedAt"] = "2026-09-09T10:30:00+00:00"
    write(phase57_path, phase57)
    assert run(tmp).returncode == 0
    assert load(output_path)["verification"]["valid"] is True

    # 6. Stability digest tampering is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["verification"]["stabilityDigest"] = "c" * 64
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 7. Source continuity digest tampering is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["verification"]["sourceContinuityDigest"] = "d" * 64
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 8. Readiness tampering is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["readiness"]["ready"] = False
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 9. Validity tampering is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["verification"]["valid"] = False
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 10. Execution authorization violation is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["executionAuthorized"] = True
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 11. Wallet safety violation is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["safety"]["walletUsed"] = True
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 12. Signing safety violation is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["safety"]["signingPerformed"] = True
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 13. Broadcast safety violation is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["safety"]["broadcastPerformed"] = True
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 14. Submission safety violation is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["safety"]["submissionPerformed"] = True
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 15. Phase57 errorCount violation is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["errorCount"] = 1
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 16. Phase57 checkpoint violation is blocked.
    tampered = copy.deepcopy(phase57)
    tampered["verification"]["checkpoint"] = "UNVERIFIED"
    write(phase57_path, tampered)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 17. Missing Phase57 is blocked.
    os.remove(phase57_path)
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 18. Corrupt Phase57 is blocked.
    with open(phase57_path, "w", encoding="utf-8") as f:
        f.write("{broken")
    assert run(tmp, 1).returncode == 1

    write(phase57_path, phase57)

    # 19. Corrupt history is blocked.
    with open(history_path, "w", encoding="utf-8") as f:
        f.write("{broken")
    assert run(tmp, 1).returncode == 1

    # Restore clean history from scratch.
    os.remove(history_path)

    # Re-establish three observations.
    for timestamp in (
        "2026-09-09T11:00:00+00:00",
        "2026-09-09T11:01:00+00:00",
        "2026-09-09T11:02:00+00:00",
    ):
        phase57["generatedAt"] = timestamp
        write(phase57_path, phase57)
        run(tmp)

    # 20. History digest tampering is blocked.
    history = load(history_path)
    history["historyDigest"] = "e" * 64
    write(history_path, history)
    assert run(tmp, 1).returncode == 1

    # Restore history.
    os.remove(history_path)

    # Rebuild.
    for timestamp in (
        "2026-09-09T12:00:00+00:00",
        "2026-09-09T12:01:00+00:00",
        "2026-09-09T12:02:00+00:00",
    ):
        phase57["generatedAt"] = timestamp
        write(phase57_path, phase57)
        run(tmp)

    # 21. History observation tampering is blocked by digest.
    history = load(history_path)
    history["observations"][0]["stabilityDigest"] = "f" * 64
    write(history_path, history)
    assert run(tmp, 1).returncode == 1

    # 22. Restored clean history verifies.
    os.remove(history_path)

    for timestamp in (
        "2026-09-09T13:00:00+00:00",
        "2026-09-09T13:01:00+00:00",
        "2026-09-09T13:02:00+00:00",
    ):
        phase57["generatedAt"] = timestamp
        write(phase57_path, phase57)
        run(tmp)

    phase57["generatedAt"] = "2026-09-09T13:03:00+00:00"
    write(phase57_path, phase57)

    r = run(tmp)
    assert "STATE: VERIFIED_READ_ONLY" in r.stdout
    assert "READY: True" in r.stdout
    assert "VALID: True" in r.stdout
    assert "HISTORY: VERIFIED_READ_ONLY" in r.stdout

    shutil.rmtree(tmp)


if __name__ == "__main__":
    test()
    print("22/22 PASSED")
