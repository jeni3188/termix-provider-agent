#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-"
    "drift-continuity-stability-history-continuity-semantic-"
    "continuity-stability-history-continuity-verify.py"
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

PHASE63_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_HISTORY_CONTINUITY_VERIFY"
)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def phase62_fixture(ready=True, history_digest="a" * 64):
    return {
        "type": PHASE62_TYPE,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "generatedAt": "2026-09-10T00:00:03+00:00",
        "executionAuthorized": False,
        "readiness": {
            "ready": ready,
            "requiredObservations": 3,
            "observations": 3,
        },
        "verification": {
            "valid": True,
            "checkpoint": "VERIFIED",
            "historyDigest": history_digest,
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


def make_history(ts="2026-09-10T00:00:01+00:00"):
    observation = {
        "phase": 61,
        "type": PHASE61_TYPE,
        "generatedAt": ts,
        "projectionDigest": "e" * 64,
        "continuityDigest": "f" * 64,
        "semanticDigest": "0" * 64,
    }

    # Import only stdlib logic matching production canonicalization.
    import hashlib
    raw = json.dumps(
        {
            "version": 1,
            "type": PHASE62_TYPE,
            "requiredObservations": 3,
            "observations": [observation],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()

    return {
        "version": 1,
        "type": PHASE62_TYPE,
        "requiredObservations": 3,
        "observations": [observation],
        "historyDigest": hashlib.sha256(raw).hexdigest(),
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
        "semantic-continuity-stability-history-continuity-verify.json"
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

    checkpoint63 = base / (
        "aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-"
        "semantic-continuity-stability-history-continuity-verify-checkpoint.json"
    )

    phase62 = phase62_fixture()
    history = make_history()

    # Align Phase62 historyDigest with fixture.
    phase62["verification"]["historyDigest"] = history["historyDigest"]

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
            "projectionDigest": phase62["verification"]["projectionDigest"],
            "continuityDigest": phase62["verification"]["continuityDigest"],
            "semanticDigest": phase62["verification"]["semanticDigest"],
        },
    )

    r1 = run(root)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    data1 = json.loads(output.read_text())
    assert data1["verification"]["valid"] is True
    assert data1["verification"]["checkpoint"] == "HISTORY_ESTABLISHED"
    assert data1["readiness"]["ready"] is False

    r2 = run(root)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    data2 = json.loads(output.read_text())
    assert data2["verification"]["checkpoint"] == "VERIFIED"
    assert data2["readiness"]["ready"] is True
    assert data2["verification"]["continuityDigest"] == data1["verification"]["continuityDigest"]
    assert data2["verification"]["semanticDigest"] == data1["verification"]["semanticDigest"]

    checkpoint63.write_text(
        checkpoint63.read_text().replace(
            data2["verification"]["continuityDigest"],
            "1" * 64,
        )
    )
    r3 = run(root)
    assert r3.returncode != 0
    failed = json.loads(output.read_text())
    assert failed["verification"]["valid"] is False
    assert "phase63_continuity_stability_drift" in failed["errors"]

    checkpoint63.unlink()
    r4 = run(root)
    assert r4.returncode == 0, r4.stdout + r4.stderr

    history["observations"][0]["generatedAt"] = "2026-09-09T00:00:00+00:00"

    # Recompute the mutated history digest while leaving Phase62's
    # stored historyDigest unchanged. This must trigger the
    # Phase62/history reference mismatch in Phase63.
    import hashlib
    raw = json.dumps(
        {
            "version": history["version"],
            "type": history["type"],
            "requiredObservations": history["requiredObservations"],
            "observations": history["observations"],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    history["historyDigest"] = hashlib.sha256(raw).hexdigest()
    write(history_path, history)

    r5 = run(root)
    assert r5.returncode != 0
    failed2 = json.loads(output.read_text())
    assert failed2["verification"]["valid"] is False
    assert "phase62_history_digest_mismatch" in failed2["errors"]

print("PHASE63 REGRESSION: 5/5 PASSED")
