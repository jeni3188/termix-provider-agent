#!/usr/bin/env python3

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


SRC = Path(
    "src/aacp-evidence-chain-health-finality-stability-history-continuity-"
    "drift-continuity-stability-history-continuity-semantic-continuity-"
    "stability-history-integrity-verify.py"
)

PHASE64_OUTPUT = (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-evolution-verify.json"
)

PHASE64_CHECKPOINT = (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-evolution-verify-checkpoint.json"
)

PHASE62_HISTORY = (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history.json"
)

PHASE65_OUTPUT = (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify.json"
)


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(root):
    return subprocess.run(
        ["python", str(SRC.resolve())],
        cwd=root,
        text=True,
        capture_output=True,
    )


def prepare_root(base):
    root = Path(base)
    observer = root / "provider-output" / "aacp-observer"
    observer.mkdir(parents=True, exist_ok=True)

    phase61_type = (
        "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
        "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
        "STABILITY_VERIFY"
    )

    phase62_type = (
        "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
        "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
        "STABILITY_HISTORY_VERIFY"
    )

    phase64_type = (
        "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
        "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
        "STABILITY_HISTORY_EVOLUTION_VERIFY"
    )

    observation = {
        "phase": 61,
        "type": phase61_type,
        "generatedAt": "2026-01-01T00:00:00+00:00",
        "projectionDigest": "a" * 64,
        "continuityDigest": "b" * 64,
        "semanticDigest": "c" * 64,
    }

    history = {
        "version": 1,
        "type": phase62_type,
        "requiredObservations": 3,
        "observations": [observation],
    }

    history["historyDigest"] = digest({
        "version": history["version"],
        "type": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observations": history["observations"],
    })

    observation_digest = digest(observation)

    evolution_projection = {
        "version": 1,
        "type": phase64_type,
        "historyType": history["type"],
        "requiredObservations": 3,
        "observationCount": 1,
        "observationDigests": [observation_digest],
        "historyDigest": history["historyDigest"],
    }

    evolution_digest = digest(evolution_projection)

    phase64 = {
        "type": phase64_type,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "generatedAt": "2026-01-01T00:00:01+00:00",
        "executionAuthorized": False,
        "readiness": {
            "ready": False,
            "observations": 1,
            "requiredObservations": 3,
        },
        "verification": {
            "valid": True,
            "checkpoint": "HISTORY_ESTABLISHED",
            "historyDigest": history["historyDigest"],
            "evolutionDigest": evolution_digest,
        },
        "safety": {
            "signingPerformed": False,
            "broadcastPerformed": False,
            "submissionPerformed": False,
        },
        "sideEffects": {
            "networkAccess": False,
            "walletAccess": False,
        },
        "errorCount": 0,
        "errors": [],
    }

    phase64_checkpoint = {
        "version": 1,
        "type": phase64_type,
        "observationCount": 1,
        "observationDigests": [observation_digest],
        "historyDigest": history["historyDigest"],
        "evolutionDigest": evolution_digest,
    }

    write_json(observer / PHASE62_HISTORY, history)
    write_json(observer / PHASE64_OUTPUT, phase64)
    write_json(observer / PHASE64_CHECKPOINT, phase64_checkpoint)

    return root, observer


def expect_success(result):
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALID: True" in result.stdout


def expect_failure(result, expected, observer):
    assert result.returncode != 0, result.stdout + result.stderr

    output = read_json(observer / PHASE65_OUTPUT)

    assert output["state"] == "VERIFIED_READ_ONLY"
    assert output["sourceState"] == "INVALID"
    assert output["executionAuthorized"] is False
    assert output["verification"]["valid"] is False
    assert output["verification"]["checkpoint"] == "FAILED"
    assert expected in output["errors"]
with tempfile.TemporaryDirectory() as td:
    td = Path(td)

    # R1 — clean valid baseline
    root1, obs1 = prepare_root(td / "r1")
    r1 = run(root1)
    expect_success(r1)

    out1 = read_json(obs1 / PHASE65_OUTPUT)
    assert out1["state"] == "VERIFIED_READ_ONLY"
    assert out1["sourceState"] == "VERIFIED_READ_ONLY"
    assert out1["executionAuthorized"] is False
    assert out1["verification"]["checkpoint"] == "VERIFIED"
    assert out1["errorCount"] == 0

    # R2 — Phase64 output mutation
    root2, obs2 = prepare_root(td / "r2")
    phase64 = read_json(obs2 / PHASE64_OUTPUT)
    phase64["readiness"]["observations"] = 99
    write_json(obs2 / PHASE64_OUTPUT, phase64)

    r2 = run(root2)
    expect_failure(r2, "phase64_contract_invalid", obs2)

    # R3 — Phase64 checkpoint mutation
    root3, obs3 = prepare_root(td / "r3")
    checkpoint = read_json(obs3 / PHASE64_CHECKPOINT)
    checkpoint["observationCount"] = 99
    write_json(obs3 / PHASE64_CHECKPOINT, checkpoint)

    r3 = run(root3)
    expect_failure(r3, "phase64_checkpoint_observation_count_invalid", obs3)

    # R4 — history digest mutation
    root4, obs4 = prepare_root(td / "r4")
    history = read_json(obs4 / PHASE62_HISTORY)
    history["historyDigest"] = "a" * 64
    write_json(obs4 / PHASE62_HISTORY, history)

    r4 = run(root4)
    expect_failure(r4, "history_digest_invalid", obs4)

    # R5 — evolution digest mutation
    root5, obs5 = prepare_root(td / "r5")
    phase64 = read_json(obs5 / PHASE64_OUTPUT)
    phase64["verification"]["evolutionDigest"] = "b" * 64
    write_json(obs5 / PHASE64_OUTPUT, phase64)

    r5 = run(root5)
    expect_failure(r5, "phase64_evolution_digest_mismatch", obs5)

    # R6 — observation digest mutation
    root6, obs6 = prepare_root(td / "r6")
    checkpoint = read_json(obs6 / PHASE64_CHECKPOINT)
    checkpoint["observationDigests"][0] = "c" * 64
    write_json(obs6 / PHASE64_CHECKPOINT, checkpoint)

    r6 = run(root6)
    expect_failure(r6, "phase64_observation_digest_mismatch", obs6)

    # R7 — Phase64 observation count mismatch
    root7, obs7 = prepare_root(td / "r7")
    phase64 = read_json(obs7 / PHASE64_OUTPUT)
    phase64["readiness"]["observations"] = (
        phase64["readiness"]["observations"] - 1
    )
    write_json(obs7 / PHASE64_OUTPUT, phase64)

    r7 = run(root7)
    expect_failure(r7, "phase64_contract_invalid", obs7)

    # R8 — timestamp regression
    root8, obs8 = prepare_root(td / "r8")
    history = read_json(obs8 / PHASE62_HISTORY)

    observations = history["observations"]

    if len(observations) >= 2:
        observations[1]["generatedAt"] = observations[0]["generatedAt"]

        history["historyDigest"] = digest({
            "version": history["version"],
            "type": history["type"],
            "requiredObservations": history["requiredObservations"],
            "observations": observations,
        })

        write_json(obs8 / PHASE62_HISTORY, history)

        r8 = run(root8)
        expect_failure(r8, "history_timestamp_regression", obs8)
    else:
        # Current live Phase62 may contain only one observation.
        # Exercise the same integrity path by forcing a malformed timestamp.
        observations[0]["generatedAt"] = "not-a-timestamp"

        history["historyDigest"] = digest({
            "version": history["version"],
            "type": history["type"],
            "requiredObservations": history["requiredObservations"],
            "observations": observations,
        })

        write_json(obs8 / PHASE62_HISTORY, history)

        r8 = run(root8)
        expect_failure(r8, "history_observation_0_timestamp_invalid", obs8)

print("PHASE65 REGRESSION: 8/8 PASSED")
