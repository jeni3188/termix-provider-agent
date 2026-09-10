#!/usr/bin/env python3

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

SRC = (
    "src/aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-verify.py"
)

PHASE58_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_VERIFY"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_VERIFY"
)


def run(tmp, expect=0):
    result = subprocess.run(
        ["python", SRC],
        cwd=tmp,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == expect, (
        f"expected {expect}, got {result.returncode}\n"
        f"stdout={result.stdout}\n"
        f"stderr={result.stderr}"
    )

    return result


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def setup():
    tmp = tempfile.mkdtemp(prefix="phase59-regression-")

    base = os.path.join(tmp, "provider-output", "aacp-observer")
    os.makedirs(base, exist_ok=True)

    target = os.path.join(tmp, SRC)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy2(SRC, target)

    phase58_path = os.path.join(
        base,
        "latest-aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-verify.json",
    )

    history_path = os.path.join(
        base,
        "aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history.json",
    )

    phase58 = {
        "version": 1,
        "type": PHASE58_TYPE,
        "generatedAt": "2026-09-10T01:00:00+00:00",
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
        "readiness": {
            "ready": True,
        },
        "verification": {
            "valid": True,
            "requiredObservations": 3,
            "observedObservations": 3,
            "history": "VERIFIED_READ_ONLY",
            "historyDigest": "a" * 64,
        },
        "errors": [],
        "errorCount": 0,
        "policy": {
            "mode": "READ_ONLY",
            "failClosed": True,
            "networkAllowed": False,
            "walletAllowed": False,
            "signingAllowed": False,
            "broadcastAllowed": False,
            "submissionAllowed": False,
        },
    }

    observations = []

    for i in range(3):
        observations.append(
            {
                "phase": 57,
                "type": (
                    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
                    "CONTINUITY_DRIFT_CONTINUITY_STABILITY_VERIFY"
                ),
                "generatedAt": (
                    f"2026-09-10T01:0{i}:00+00:00"
                ),
                "semanticDigest": "b" * 64,
                "stabilityDigest": "c" * 64,
                "sourceContinuityDigest": "d" * 64,
            }
        )

    history = {
        "version": 1,
        "type": (
            "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
            "DRIFT_CONTINUITY_STABILITY_HISTORY_VERIFY"
        ),
        "requiredObservations": 3,
        "observations": observations,
    }

    # Reproduce canonical history digest.
    projection = {
        "version": history["version"],
        "type": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observations": history["observations"],
    }

    canonical = json.dumps(
        projection,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


    history["historyDigest"] = hashlib.sha256(
        canonical.encode()
    ).hexdigest()

    write(phase58_path, phase58)
    write(history_path, history)

    return tmp, phase58_path, history_path


def checkpoint_file(tmp):
    return os.path.join(
        tmp,
        "provider-output",
        "aacp-observer",
        "aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-checkpoint.json",
    )


def test():
    tmp, phase58_path, history_path = setup()

    output_path = os.path.join(
        tmp,
        "provider-output",
        "aacp-observer",
        "latest-aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-verify.json",
    )

    # 1. First run establishes checkpoint.
    r = run(tmp)
    assert "CHECKPOINT: CHECKPOINT_ESTABLISHED" in r.stdout

    output = load(output_path)
    assert output["verification"]["valid"] is True
    assert output["readiness"]["ready"] is False

    checkpoint = load(checkpoint_file(tmp))
    assert checkpoint["type"] == TYPE

    # 2. Second run verifies continuity.
    r = run(tmp)
    assert "CHECKPOINT: VERIFIED" in r.stdout

    output = load(output_path)
    assert output["state"] == "VERIFIED_READ_ONLY"
    assert output["readiness"]["ready"] is True
    assert output["verification"]["valid"] is True

    # 3. Deterministic continuity digest.
    digest1 = output["verification"]["continuityDigest"]
    r = run(tmp)
    output2 = load(output_path)
    assert output2["verification"]["continuityDigest"] == digest1

    # 4. Phase58 generatedAt-only change is ignored.
    phase58 = load(phase58_path)
    phase58["generatedAt"] = "2026-09-10T09:00:00+00:00"
    write(phase58_path, phase58)
    assert run(tmp).returncode == 0

    # 5. History generatedAt change is NOT ignored.
    history = load(history_path)
    history["observations"][0]["generatedAt"] = (
        "2026-09-10T99:00:00+00:00"
    )
    write(history_path, history)
    assert run(tmp, 1).returncode == 1

    # Restore.
    shutil.rmtree(tmp)

    tmp, phase58_path, history_path = setup()

    # 6. Checkpoint projection tampering.
    run(tmp)
    checkpoint = load(checkpoint_file(tmp))
    checkpoint["historyProjection"]["requiredObservations"] = 99
    write(checkpoint_file(tmp), checkpoint)
    assert run(tmp, 1).returncode == 1

    # 7. Checkpoint digest tampering.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    run(tmp)
    checkpoint = load(checkpoint_file(tmp))
    checkpoint["continuityDigest"] = "e" * 64
    write(checkpoint_file(tmp), checkpoint)
    assert run(tmp, 1).returncode == 1

    # 8. Checkpoint type tampering.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    run(tmp)
    checkpoint = load(checkpoint_file(tmp))
    checkpoint["type"] = "INVALID"
    write(checkpoint_file(tmp), checkpoint)
    assert run(tmp, 1).returncode == 1

    # 9. Phase58 validity violation.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    run(tmp)
    phase58 = load(phase58_path)
    phase58["verification"]["valid"] = False
    write(phase58_path, phase58)
    assert run(tmp, 1).returncode == 1

    # 10. Execution authorization violation.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    run(tmp)
    phase58 = load(phase58_path)
    phase58["executionAuthorized"] = True
    write(phase58_path, phase58)
    assert run(tmp, 1).returncode == 1

    # 11. Wallet safety violation.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    run(tmp)
    phase58 = load(phase58_path)
    phase58["safety"]["walletUsed"] = True
    write(phase58_path, phase58)
    assert run(tmp, 1).returncode == 1

    # 12. Signing safety violation.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    run(tmp)
    phase58 = load(phase58_path)
    phase58["safety"]["signingPerformed"] = True
    write(phase58_path, phase58)
    assert run(tmp, 1).returncode == 1

    # 13. Broadcast side effect violation.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    run(tmp)
    phase58 = load(phase58_path)
    phase58["sideEffects"]["broadcast"] = True
    write(phase58_path, phase58)
    assert run(tmp, 1).returncode == 1

    # 14. Submission side effect violation.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    run(tmp)
    phase58 = load(phase58_path)
    phase58["sideEffects"]["submission"] = True
    write(phase58_path, phase58)
    assert run(tmp, 1).returncode == 1

    # 15. Missing history.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    os.remove(history_path)
    assert run(tmp, 1).returncode == 1

    # 16. Corrupt history.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    with open(history_path, "w", encoding="utf-8") as f:
        f.write("{broken")
    assert run(tmp, 1).returncode == 1

    # 17. Missing Phase58.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    os.remove(phase58_path)
    assert run(tmp, 1).returncode == 1

    # 18. Corrupt Phase58.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    with open(phase58_path, "w", encoding="utf-8") as f:
        f.write("{broken")
    assert run(tmp, 1).returncode == 1

    # 19. Observation count violation.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    history = load(history_path)
    history["observations"].pop()
    # Recompute digest so structural validation catches the count.
    projection = {
        "version": history["version"],
        "type": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observations": history["observations"],
    }
    canonical = json.dumps(
        projection,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    history["historyDigest"] = hashlib.sha256(
        canonical.encode()
    ).hexdigest()
    write(history_path, history)
    assert run(tmp, 1).returncode == 1

    # 20. Observation ordering violation.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    history = load(history_path)
    history["observations"][2]["generatedAt"] = (
        "2026-09-10T00:00:00+00:00"
    )
    projection = {
        "version": history["version"],
        "type": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observations": history["observations"],
    }
    canonical = json.dumps(
        projection,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    history["historyDigest"] = hashlib.sha256(
        canonical.encode()
    ).hexdigest()
    write(history_path, history)
    assert run(tmp, 1).returncode == 1

    # 21. History digest mismatch.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    history = load(history_path)
    history["historyDigest"] = "f" * 64
    write(history_path, history)
    assert run(tmp, 1).returncode == 1

    # 22. Final restored verification.
    shutil.rmtree(tmp)
    tmp, phase58_path, history_path = setup()
    run(tmp)
    r = run(tmp)
    assert "STATE: VERIFIED_READ_ONLY" in r.stdout
    assert "READY: True" in r.stdout
    assert "VALID: True" in r.stdout
    assert "CHECKPOINT: VERIFIED" in r.stdout

    shutil.rmtree(tmp)


if __name__ == "__main__":
    test()
    print("22/22 PASSED")
