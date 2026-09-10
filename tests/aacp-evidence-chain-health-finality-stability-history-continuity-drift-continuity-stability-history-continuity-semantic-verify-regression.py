#!/usr/bin/env python3

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SRC = (
    "src/aacp-evidence-chain-health-finality-stability-history-continuity-"
    "drift-continuity-stability-history-continuity-semantic-verify.py"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_VERIFY"
)

PHASE59_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_VERIFY"
)

PHASE58_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_VERIFY"
)

BASE = (
    Path("provider-output")
    / "aacp-observer"
)

PHASE59_OUTPUT = (
    BASE
    / "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-verify.json"
)

PHASE58_OUTPUT = (
    BASE
    / "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-verify.json"
)

HISTORY_OUTPUT = (
    BASE
    / "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history.json"
)

PHASE59_CHECKPOINT = (
    BASE
    / "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-checkpoint.json"
)

PHASE60_CHECKPOINT = (
    BASE
    / "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-checkpoint.json"
)

PHASE60_OUTPUT = (
    BASE
    / "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-verify.json"
)


def canonical(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(obj):
    return hashlib.sha256(
        canonical(obj).encode("utf-8")
    ).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            obj,
            f,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        f.write("\n")


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_phase58():
    return {
        "version": 1,
        "type": PHASE58_TYPE,
        "mode": "READ_ONLY",
        "executionAuthorized": False,
        "safety": {
            "signingPerformed": False,
            "broadcastPerformed": False,
            "submissionPerformed": False,
            "walletUsed": False,
            "privateKeyAccessed": False,
            "postPerformed": False,
        },
        "sideEffects": {
            "broadcast": False,
            "networkAccess": False,
            "signing": False,
            "submission": False,
            "walletAccess": False,
            "filesystemRead": True,
            "filesystemWrite": True,
        },
        "errorCount": 0,
        "errors": [],
        "generatedAt": "2026-09-10T00:50:00+00:00",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "readiness": {
            "ready": True,
        },
        "verification": {
            "valid": True,
            "requiredObservations": 3,
            "observedObservations": 3,
            "history": "VERIFIED_READ_ONLY",
            "historyDigest": "b" * 64,
        },
    }


def make_history():
    observations = []

    for index, minute in enumerate((40, 41, 42)):
        observations.append(
            {
                "phase": 57,
                "type": (
                    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_"
                    "HISTORY_CONTINUITY_DRIFT_CONTINUITY_STABILITY_VERIFY"
                ),
                "generatedAt": (
                    f"2026-09-10T00:{minute:02d}:00+00:00"
                ),
                "semanticDigest": str(index + 1) * 64,
                "stabilityDigest": str(index + 4) * 64,
                "sourceContinuityDigest": str(index + 7) * 64,
            }
        )

    history = {
        "version": 1,
        "type": (
            "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
            "CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_VERIFY"
        ),
        "requiredObservations": 3,
        "observations": observations,
    }

    history["historyDigest"] = digest(
        {
            "version": history["version"],
            "type": history["type"],
            "requiredObservations": history["requiredObservations"],
            "observations": history["observations"],
        }
    )

    return history


def make_phase59():
    return {
        "version": 1,
        "type": PHASE59_TYPE,
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "executionAuthorized": False,
        "safety": {
            "signingPerformed": False,
            "broadcastPerformed": False,
            "submissionPerformed": False,
        },
        "sideEffects": {
            "networkAccess": False,
            "walletAccess": False,
        },
        "readiness": {
            "ready": True,
        },
        "verification": {
            "valid": True,
            "checkpoint": "VERIFIED",
            "continuityDigest": "c" * 64,
        },
    }


def prepare_fixture(tmp):
    repo = Path(__file__).resolve().parents[1]

    source_destination = Path(tmp) / SRC
    source_destination.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(
        repo / SRC,
        source_destination,
    )

    base = Path(tmp) / BASE
    base.mkdir(parents=True, exist_ok=True)

    write_json(
        Path(tmp) / PHASE58_OUTPUT,
        make_phase58(),
    )

    write_json(
        Path(tmp) / HISTORY_OUTPUT,
        make_history(),
    )

    write_json(
        Path(tmp) / PHASE59_OUTPUT,
        make_phase59(),
    )


def run_phase60(tmp):
    return subprocess.run(
        [sys.executable, str(Path(tmp) / SRC)],
        cwd=tmp,
        text=True,
        capture_output=True,
    )


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test():
    tmp = tempfile.mkdtemp(
        prefix="phase60-semantic-regression-"
    )

    try:
        prepare_fixture(tmp)

        phase59_path = Path(tmp) / PHASE59_OUTPUT
        phase60_output = Path(tmp) / PHASE60_OUTPUT
        phase60_checkpoint = Path(tmp) / PHASE60_CHECKPOINT
        phase59_checkpoint = Path(tmp) / PHASE59_CHECKPOINT

        original_phase59 = phase59_path.read_bytes()

        # 1 — First run establishes checkpoint.
        result = run_phase60(tmp)

        assert_true(
            result.returncode == 0,
            "first run failed:\n"
            + result.stdout
            + result.stderr,
        )

        output = read_json(phase60_output)

        assert_true(
            output["type"] == TYPE,
            "Phase60 output type invalid",
        )

        assert_true(
            output["state"] == "VERIFIED_READ_ONLY",
            "first state invalid",
        )

        assert_true(
            output["readiness"]["ready"] is False,
            "first ready must be false",
        )

        assert_true(
            output["verification"]["valid"] is True,
            "first valid must be true",
        )

        assert_true(
            output["verification"]["checkpoint"]
            == "CHECKPOINT_ESTABLISHED",
            "checkpoint establishment invalid",
        )

        assert_true(
            len(output["verification"]["semanticDigest"]) == 64,
            "semantic digest invalid",
        )

        # 2 — Phase60 checkpoint is separate.
        assert_true(
            phase60_checkpoint.exists(),
            "Phase60 checkpoint missing",
        )

        assert_true(
            phase60_checkpoint != phase59_checkpoint,
            "Phase60 checkpoint collides with Phase59",
        )

        checkpoint = read_json(phase60_checkpoint)

        assert_true(
            checkpoint["type"] == TYPE,
            "checkpoint type invalid",
        )

        assert_true(
            len(checkpoint["semanticDigest"]) == 64,
            "checkpoint semanticDigest invalid",
        )

        # 3 — Phase59 remains byte-identical.
        assert_true(
            phase59_path.read_bytes() == original_phase59,
            "Phase59 artifact modified",
        )

        # 4 — Second run reaches VERIFIED.
        result = run_phase60(tmp)

        assert_true(
            result.returncode == 0,
            "second run failed:\n"
            + result.stdout
            + result.stderr,
        )

        output = read_json(phase60_output)

        assert_true(
            output["readiness"]["ready"] is True,
            "second ready invalid",
        )

        assert_true(
            output["verification"]["valid"] is True,
            "second valid invalid",
        )

        assert_true(
            output["verification"]["checkpoint"] == "VERIFIED",
            "second checkpoint invalid",
        )

        # 5 — Semantic digest tamper must fail closed.
        checkpoint = read_json(phase60_checkpoint)
        original_semantic_digest = checkpoint["semanticDigest"]

        checkpoint["semanticDigest"] = "0" * 64
        write_json(phase60_checkpoint, checkpoint)

        result = run_phase60(tmp)

        assert_true(
            result.returncode != 0,
            "semantic tamper did not fail",
        )

        output = read_json(phase60_output)

        assert_true(
            output["state"] == "BLOCKED",
            "semantic tamper not BLOCKED",
        )

        assert_true(
            output["verification"]["valid"] is False,
            "semantic tamper valid not false",
        )

        assert_true(
            "CHECKPOINT_SEMANTIC_DIGEST_MISMATCH"
            in output["errors"],
            "semantic mismatch error missing",
        )

        # 6 — Restore semantic digest.
        checkpoint["semanticDigest"] = original_semantic_digest
        write_json(phase60_checkpoint, checkpoint)

        result = run_phase60(tmp)

        assert_true(
            result.returncode == 0,
            "semantic digest restore failed",
        )

        # 7 — Projection tamper must fail closed.
        checkpoint = read_json(phase60_checkpoint)

        original_required = checkpoint["historyProjection"][
            "requiredObservations"
        ]

        checkpoint["historyProjection"][
            "requiredObservations"
        ] = 999

        write_json(phase60_checkpoint, checkpoint)

        result = run_phase60(tmp)

        assert_true(
            result.returncode != 0,
            "projection tamper did not fail",
        )

        output = read_json(phase60_output)

        assert_true(
            output["state"] == "BLOCKED",
            "projection tamper not BLOCKED",
        )

        assert_true(
            "CHECKPOINT_PROJECTION_MISMATCH"
            in output["errors"],
            "projection mismatch error missing",
        )

        # 8 — Restore projection.
        checkpoint["historyProjection"][
            "requiredObservations"
        ] = original_required

        write_json(phase60_checkpoint, checkpoint)

        result = run_phase60(tmp)

        assert_true(
            result.returncode == 0,
            "projection restore failed",
        )

        # 9 — Phase59 upstream tamper must fail closed.
        phase59 = read_json(phase59_path)
        phase59["executionAuthorized"] = True
        write_json(phase59_path, phase59)

        result = run_phase60(tmp)

        assert_true(
            result.returncode != 0,
            "Phase59 tamper did not fail",
        )

        output = read_json(phase60_output)

        assert_true(
            output["state"] == "UNVERIFIED_READ_ONLY",
            "Phase59 tamper state invalid",
        )

        assert_true(
            output["readiness"]["ready"] is False,
            "Phase59 tamper ready invalid",
        )

        assert_true(
            output["verification"]["valid"] is False,
            "Phase59 tamper valid invalid",
        )

        assert_true(
            "phase59_execution_authorized_invalid"
            in output["errors"],
            "Phase59 gate error missing",
        )

        # 10 — Restore Phase59 and verify recovery.
        phase59["executionAuthorized"] = False
        write_json(phase59_path, phase59)

        result = run_phase60(tmp)

        assert_true(
            result.returncode == 0,
            "Phase59 restore failed",
        )

        output = read_json(phase60_output)

        assert_true(
            output["type"] == TYPE,
            "restored output type invalid",
        )

        assert_true(
            output["state"] == "VERIFIED_READ_ONLY",
            "restored state invalid",
        )

        assert_true(
            output["readiness"]["ready"] is True,
            "restored ready invalid",
        )

        assert_true(
            output["verification"]["valid"] is True,
            "restored valid invalid",
        )

        assert_true(
            output["verification"]["checkpoint"] == "VERIFIED",
            "restored checkpoint invalid",
        )

        # 11 — Final upstream immutability check.
        restored_phase59 = read_json(phase59_path)

        assert_true(
            restored_phase59["type"] == PHASE59_TYPE,
            "Phase59 type changed",
        )

        assert_true(
            phase59_path.read_bytes() != b"",
            "Phase59 artifact empty",
        )

        # 12 — Phase60 artifacts remain isolated.
        assert_true(
            phase60_output.name != phase59_path.name,
            "Phase60 output name collision",
        )

        assert_true(
            phase60_checkpoint.name != phase59_checkpoint.name,
            "Phase60 checkpoint name collision",
        )

        print("12/12 PASSED")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test()
