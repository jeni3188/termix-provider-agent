#!/usr/bin/env python3

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "src" / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-"
    "drift-continuity-stability-history-continuity-semantic-"
    "continuity-stability-history-evolution-verify.py"
)

PHASE62_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_HISTORY_VERIFY"
)

PHASE61_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_VERIFY"
)

PHASE64_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_HISTORY_EVOLUTION_VERIFY"
)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def observation(index, timestamp):
    return {
        "phase": 61,
        "type": PHASE61_TYPE,
        "generatedAt": timestamp,
        "projectionDigest": ("a", "b", "c")[index] * 64,
        "continuityDigest": ("d", "e", "f")[index] * 64,
        "semanticDigest": ("1", "2", "3")[index] * 64,
    }


def make_history(observations):
    result = {
        "version": 1,
        "type": PHASE62_TYPE,
        "requiredObservations": 3,
        "observations": observations,
    }

    result["historyDigest"] = digest({
        "version": result["version"],
        "type": result["type"],
        "requiredObservations": result["requiredObservations"],
        "observations": result["observations"],
    })

    return result


def phase62_fixture(history):
    return {
        "type": PHASE62_TYPE,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "generatedAt": "2026-09-10T00:00:03+00:00",
        "executionAuthorized": False,
        "readiness": {
            "ready": len(history["observations"]) == 3,
            "requiredObservations": 3,
            "observations": len(history["observations"]),
        },
        "verification": {
            "valid": True,
            "checkpoint": (
                "VERIFIED"
                if len(history["observations"]) == 3
                else "HISTORY_ESTABLISHED"
            ),
            "historyDigest": history["historyDigest"],
            "projectionDigest": "b" * 64,
            "continuityDigest": "c" * 64,
            "semanticDigest": "d" * 64,
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


def run(root):
    return subprocess.run(
        [sys.executable, str(SOURCE)],
        cwd=root,
        text=True,
        capture_output=True,
    )


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    base = root / "provider-output" / "aacp-observer"

    output = base / (
        "latest-aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-"
        "semantic-continuity-stability-history-evolution-verify.json"
    )

    history_path = base / (
        "aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-"
        "semantic-continuity-stability-history.json"
    )

    checkpoint62 = base / (
        "aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-"
        "semantic-continuity-stability-history-continuity-checkpoint.json"
    )

    checkpoint64 = base / (
        "aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-"
        "semantic-continuity-stability-history-evolution-verify-checkpoint.json"
    )

    o1 = observation(0, "2026-09-10T00:00:01+00:00")
    o2 = observation(1, "2026-09-10T00:00:02+00:00")
    o3 = observation(2, "2026-09-10T00:00:03+00:00")

    history = make_history([o1])
    phase62 = phase62_fixture(history)

    write(
        base / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history-verify.json"
        ),
        phase62,
    )

    write(history_path, history)

    write(
        checkpoint62,
        {
            "version": 1,
            "type": PHASE62_TYPE,
            "requiredObservations": 3,
            "projectionDigest": "b" * 64,
            "continuityDigest": "c" * 64,
            "semanticDigest": "d" * 64,
        },
    )

    # R1: establish.
    r1 = run(root)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    d1 = json.loads(output.read_text())
    assert d1["verification"]["checkpoint"] == "HISTORY_ESTABLISHED"
    assert d1["readiness"]["ready"] is False
    assert d1["verification"]["valid"] is True

    # R2: identical history is stable.
    r2 = run(root)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    d2 = json.loads(output.read_text())
    assert d2["verification"]["checkpoint"] == "VERIFIED"
    assert d2["readiness"]["ready"] is False
    assert d2["verification"]["evolutionDigest"] == d1["verification"]["evolutionDigest"]

    # R3: append exactly one observation.
    history = make_history([o1, o2])
    phase62 = phase62_fixture(history)
    write(history_path, history)
    write(
        base / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history-verify.json"
        ),
        phase62,
    )

    r3 = run(root)
    assert r3.returncode == 0, r3.stdout + r3.stderr
    d3 = json.loads(output.read_text())
    assert d3["readiness"]["observations"] == 2

    # R4: append the third observation and become ready.
    history = make_history([o1, o2, o3])
    phase62 = phase62_fixture(history)
    write(history_path, history)
    write(
        base / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history-verify.json"
        ),
        phase62,
    )

    r4 = run(root)
    assert r4.returncode == 0, r4.stdout + r4.stderr
    d4 = json.loads(output.read_text())
    assert d4["readiness"]["observations"] == 3
    assert d4["readiness"]["ready"] is True

    # R5: mutate an existing observation.
    mutated = dict(o2)
    mutated["semanticDigest"] = "9" * 64
    history = make_history([o1, mutated, o3])
    phase62 = phase62_fixture(history)
    write(history_path, history)
    write(
        base / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history-verify.json"
        ),
        phase62,
    )

    r5 = run(root)
    assert r5.returncode != 0
    failed5 = json.loads(output.read_text())
    assert failed5["verification"]["valid"] is False
    assert "phase64_history_mutation" in failed5["errors"]

    # Restore valid history.
    history = make_history([o1, o2, o3])
    phase62 = phase62_fixture(history)
    write(history_path, history)
    write(
        base / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history-verify.json"
        ),
        phase62,
    )

    # R6: remove an observation.
    history = make_history([o1, o2])
    phase62 = phase62_fixture(history)
    write(history_path, history)
    write(
        base / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history-verify.json"
        ),
        phase62,
    )

    r6 = run(root)
    assert r6.returncode != 0
    failed6 = json.loads(output.read_text())
    assert failed6["verification"]["valid"] is False
    assert "phase64_history_shrank" in failed6["errors"]

    # R7: restore and jump by two observations from a one-observation checkpoint
    # is covered by a fresh isolated fixture.
    root2 = Path(tempfile.mkdtemp(dir=Path(td)))
    base2 = root2 / "provider-output" / "aacp-observer"

    history2 = make_history([o1])
    phase62_2 = phase62_fixture(history2)

    write(
        base2 / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history-verify.json"
        ),
        phase62_2,
    )
    write(
        base2 / (
            "aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history.json"
        ),
        history2,
    )
    write(
        base2 / (
            "aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history-continuity-checkpoint.json"
        ),
        {
            "version": 1,
            "type": PHASE62_TYPE,
            "requiredObservations": 3,
            "projectionDigest": "b" * 64,
            "continuityDigest": "c" * 64,
            "semanticDigest": "d" * 64,
        },
    )

    # Establish the Phase64 checkpoint at one observation.
    r7a = run(root2)
    assert r7a.returncode == 0, r7a.stdout + r7a.stderr

    history2 = make_history([o1, o2, o3])
    phase62_2 = phase62_fixture(history2)
    write(
        base2 / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history-verify.json"
        ),
        phase62_2,
    )
    write(
        base2 / (
            "aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-history.json"
        ),
        history2,
    )

    r7 = run(root2)
    assert r7.returncode != 0
    failed7 = json.loads(
        (
            base2 / (
                "latest-aacp-evidence-chain-health-finality-stability-history-"
                "continuity-drift-continuity-stability-history-continuity-"
                "semantic-continuity-stability-history-evolution-verify.json"
            )
        ).read_text()
    )
    assert failed7["verification"]["valid"] is False
    assert "phase64_history_jump" in failed7["errors"]

print("PHASE64 REGRESSION: 7/7 PASSED")
