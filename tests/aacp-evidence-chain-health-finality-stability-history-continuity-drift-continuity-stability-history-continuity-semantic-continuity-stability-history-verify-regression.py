#!/usr/bin/env python3

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / (
    "src/aacp-evidence-chain-health-finality-stability-history-continuity-"
    "drift-continuity-stability-history-continuity-semantic-continuity-"
    "stability-history-verify.py"
)

with tempfile.TemporaryDirectory() as td:
    base = Path(td) / "provider-output" / "aacp-observer"
    base.mkdir(parents=True)

    phase61 = base / (
        "latest-aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-"
        "semantic-continuity-stability-verify.json"
    )

    output = base / (
        "latest-aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-"
        "semantic-continuity-stability-history-verify.json"
    )

    history = base / (
        "aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-"
        "semantic-continuity-stability-history.json"
    )

    checkpoint = base / (
        "aacp-evidence-chain-health-finality-stability-history-"
        "continuity-drift-continuity-stability-history-continuity-"
        "semantic-continuity-stability-history-checkpoint.json"
    )

    fixture = {
        "type": (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_"
    "SEMANTIC_CONTINUITY_STABILITY_VERIFY"
),
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "generatedAt": "2026-09-10T00:00:00+00:00",
        "executionAuthorized": False,
        "readiness": {"ready": True},
        "verification": {
            "valid": True,
            "checkpoint": "VERIFIED",
            "continuityDigest": "a" * 64,
            "semanticDigest": "b" * 64,
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

    phase61.write_text(json.dumps(fixture), encoding="utf-8")

    run_counter = [0]

    def run():
        # Each upstream Phase61 observation must have a strictly
        # increasing timestamp so Phase62 history continuity can
        # validate temporal monotonicity across repeated runs.
        from datetime import datetime, timedelta, timezone

        run_counter[0] += 1
        fixture["generatedAt"] = (
            datetime(2026, 9, 10, 0, 0, tzinfo=timezone.utc)
            + timedelta(seconds=run_counter[0])
        ).isoformat()

        phase61.write_text(
            json.dumps(fixture),
            encoding="utf-8",
        )

        print(f"=== RUN {run_counter[0]} PHASE61 FILE ===")
        print(phase61.read_text(encoding="utf-8"))

        r = subprocess.run(
            ["python", str(SRC)],
            cwd=Path(td),
            env={
                **__import__("os").environ,
                "PYTHONPATH": str(ROOT),
            },
            capture_output=True,
            text=True,
        )
        return r

    def read_output():
        return json.loads(output.read_text(encoding="utf-8"))

    # 1 first run
    r = run()
    if r.returncode != 0:
        print("=== PHASE62 SUBPROCESS FAILURE ===")
        print("RETURN CODE:", r.returncode)
        print("STDOUT:")
        print(r.stdout)
        print("STDERR:")
        print(r.stderr)
    assert r.returncode == 0
    x = read_output()
    assert x["verification"]["checkpoint"] == "HISTORY_ESTABLISHED"
    assert x["readiness"]["ready"] is False

    # 2 history exists
    assert history.exists()

    # 3 second run
    # Diagnostic: inspect the exact Phase61 artifact immediately before
    # subprocess validation on run #2.
    print("=== PHASE61 BEFORE SECOND RUN ===")
    print(phase61.read_text(encoding="utf-8"))
    print("=== PHASE61 FIXTURE BEFORE SECOND RUN ===")
    print(json.dumps(fixture, indent=2, sort_keys=True))
    r = run()
    if r.returncode != 0:
        print("=== PHASE62 SECOND-RUN SUBPROCESS FAILURE ===")
        print("RETURN CODE:", r.returncode)
        print("STDOUT:")
        print(r.stdout)
        print("STDERR:")
        print(r.stderr)
    assert r.returncode == 0
    x = read_output()
    assert x["verification"]["checkpoint"] == "VERIFIED"
    assert x["readiness"]["ready"] is False

    # 4 third run
    r = run()
    if r.returncode != 0:
        print("=== PHASE62 THIRD-RUN SUBPROCESS FAILURE ===")
        print("RETURN CODE:", r.returncode)
        print("STDOUT:")
        print(r.stdout)
        print("STDERR:")
        print(r.stderr)
    assert r.returncode == 0
    x = read_output()
    assert x["verification"]["checkpoint"] == "VERIFIED"
    assert x["readiness"]["ready"] is True
    assert x["readiness"]["observations"] == 3

    # 5 projection tamper
    h = json.loads(history.read_text(encoding="utf-8"))
    h["observations"][-1]["projectionDigest"] = "c" * 64
    history.write_text(json.dumps(h), encoding="utf-8")
    r = run()
    assert r.returncode != 0

    # 6 restore
    history.unlink()
    checkpoint.unlink()
    r = run()
    assert r.returncode == 0

    # 7 continuity tamper
    fixture["verification"]["continuityDigest"] = "d" * 64
    phase61.write_text(json.dumps(fixture), encoding="utf-8")
    r = run()
    assert r.returncode != 0

    # 8 restore upstream
    fixture["verification"]["continuityDigest"] = "a" * 64
    phase61.write_text(json.dumps(fixture), encoding="utf-8")
    history.unlink()
    checkpoint.unlink()
    r = run()
    assert r.returncode == 0

    # 9 semantic tamper
    fixture["verification"]["semanticDigest"] = "e" * 64
    phase61.write_text(json.dumps(fixture), encoding="utf-8")
    r = run()
    assert r.returncode != 0

    # 10 restore + final three observations
    fixture["verification"]["semanticDigest"] = "b" * 64
    phase61.write_text(json.dumps(fixture), encoding="utf-8")
    history.unlink()
    checkpoint.unlink()

    assert run().returncode == 0
    assert run().returncode == 0
    assert run().returncode == 0

    x = read_output()
    assert x["state"] == "VERIFIED_READ_ONLY"
    assert x["sourceState"] == "VERIFIED_READ_ONLY"
    assert x["readiness"]["ready"] is True
    assert x["verification"]["valid"] is True
    assert x["verification"]["checkpoint"] == "VERIFIED"

    # 11 safety
    assert x["executionAuthorized"] is False
    assert x["sideEffects"]["networkAccess"] is False
    assert x["sideEffects"]["walletAccess"] is False
    assert x["safety"]["signingPerformed"] is False
    assert x["safety"]["broadcastPerformed"] is False
    assert x["safety"]["submissionPerformed"] is False

    # 12 required history contract
    h = json.loads(history.read_text(encoding="utf-8"))
    assert h["version"] == 1
    assert h["requiredObservations"] == 3
    assert len(h["observations"]) == 3
    assert len(h["historyDigest"]) == 64

print("12/12 PASSED")
