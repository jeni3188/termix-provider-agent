#!/usr/bin/env python3

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / (
    "src/"
    "aacp-evidence-chain-health-finality-stability-history-continuity-"
    "drift-continuity-stability-history-continuity-semantic-continuity-"
    "stability-verify.py"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_VERIFY"
)

PHASE60_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_VERIFY"
)


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(value):
    return hashlib.sha256(
        canonical(value).encode()
    ).hexdigest()


def run(tmp):
    env = os.environ.copy()

    result = subprocess.run(
        [sys.executable, str(SRC)],
        cwd=tmp,
        text=True,
        capture_output=True,
        env=env,
    )

    return result


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            value,
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")


def read(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def phase60_fixture():
    semantic = {
        "type": PHASE60_TYPE,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "ready": True,
        "valid": True,
        "checkpoint": "VERIFIED",
        "continuityDigest": "a" * 64,
        "semanticDigest": "b" * 64,
        "executionAuthorized": False,
        "networkAccess": False,
        "walletAccess": False,
        "signingPerformed": False,
        "broadcastPerformed": False,
        "submissionPerformed": False,
        "errorCount": 0,
        "errors": [],
    }

    return {
        "version": 1,
        "type": PHASE60_TYPE,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "generatedAt": "2026-09-10T10:00:00+00:00",
        "executionAuthorized": False,
        "readiness": {
            "ready": True,
        },
        "verification": {
            "valid": True,
            "checkpoint": "VERIFIED",
            "continuityDigest": semantic["continuityDigest"],
            "semanticDigest": semantic["semanticDigest"],
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


def main():
    failures = []

    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)

        observer = (
            tmp /
            "provider-output" /
            "aacp-observer"
        )

        phase60_path = observer / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-verify.json"
        )

        checkpoint_path = observer / (
            "aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-checkpoint.json"
        )

        output_path = observer / (
            "latest-aacp-evidence-chain-health-finality-stability-history-"
            "continuity-drift-continuity-stability-history-continuity-"
            "semantic-continuity-stability-verify.json"
        )

        write(phase60_path, phase60_fixture())

        # 1. First run establishes checkpoint.
        result = run(tmp)
        out = read(output_path)

        if result.returncode != 0:
            failures.append("FIRST_RUN_NONZERO")

        if out["verification"]["checkpoint"] != "CHECKPOINT_ESTABLISHED":
            failures.append("FIRST_RUN_NOT_ESTABLISHED")

        if out["readiness"]["ready"] is not False:
            failures.append("FIRST_RUN_READY_NOT_FALSE")

        if out["verification"]["valid"] is not True:
            failures.append("FIRST_RUN_INVALID")

        # 2. Phase60 must remain byte-identical.
        phase60_before = phase60_path.read_bytes()

        # 3. Checkpoint must be isolated from Phase60.
        if checkpoint_path == phase60_path:
            failures.append("CHECKPOINT_COLLISION")

        # 4. Second run verifies stability.
        result = run(tmp)
        out = read(output_path)

        if result.returncode != 0:
            failures.append("SECOND_RUN_NONZERO")

        if out["verification"]["checkpoint"] != "VERIFIED":
            failures.append("SECOND_RUN_NOT_VERIFIED")

        if out["readiness"]["ready"] is not True:
            failures.append("SECOND_RUN_NOT_READY")

        # 5. Semantic digest tamper must fail closed.
        checkpoint = read(checkpoint_path)
        checkpoint["semanticDigest"] = "c" * 64
        write(checkpoint_path, checkpoint)

        result = run(tmp)
        out = read(output_path)

        if result.returncode == 0:
            failures.append("SEMANTIC_TAMPER_NOT_REJECTED")

        if out["verification"]["checkpoint"] != "BLOCKED":
            failures.append("SEMANTIC_TAMPER_NOT_BLOCKED")

        if "SEMANTIC_DIGEST_MISMATCH" not in out["errors"]:
            failures.append("SEMANTIC_TAMPER_ERROR_MISSING")

        # 6. Restore checkpoint.
        checkpoint["semanticDigest"] = digest(
            checkpoint["semanticProjection"]
        )
        write(checkpoint_path, checkpoint)

        # The actual semantic digest must equal the Phase60 fixture digest.
        checkpoint["semanticDigest"] = read(
            phase60_path
        )["verification"]["semanticDigest"]
        write(checkpoint_path, checkpoint)

        # 7. Projection tamper must fail closed.
        checkpoint = read(checkpoint_path)
        checkpoint["semanticProjection"]["ready"] = False
        write(checkpoint_path, checkpoint)

        result = run(tmp)
        out = read(output_path)

        if result.returncode == 0:
            failures.append("PROJECTION_TAMPER_NOT_REJECTED")

        if "SEMANTIC_PROJECTION_MISMATCH" not in out["errors"]:
            failures.append("PROJECTION_TAMPER_ERROR_MISSING")

        # 8. Restore from clean checkpoint by deleting and re-establishing.
        checkpoint_path.unlink()

        result = run(tmp)

        if result.returncode != 0:
            failures.append("CHECKPOINT_REESTABLISH_FAILED")

        # 9. Upstream Phase60 tamper must fail closed.
        phase60 = read(phase60_path)
        phase60["verification"]["semanticDigest"] = "d" * 64
        write(phase60_path, phase60)

        result = run(tmp)
        out = read(output_path)

        if result.returncode == 0:
            failures.append("UPSTREAM_TAMPER_NOT_REJECTED")

        if out["verification"]["checkpoint"] != "BLOCKED":
            failures.append("UPSTREAM_TAMPER_NOT_BLOCKED")

        # 10. Restore Phase60 and checkpoint.
        phase60 = phase60_fixture()
        write(phase60_path, phase60)
        checkpoint_path.unlink()

        result = run(tmp)
        if result.returncode != 0:
            failures.append("FINAL_REESTABLISH_FAILED")

        result = run(tmp)
        out = read(output_path)

        if out["verification"]["checkpoint"] != "VERIFIED":
            failures.append("FINAL_NOT_VERIFIED")

        # 11. Phase60 immutability.
        phase60_after = phase60_path.read_bytes()

        if phase60_before != phase60_after:
            failures.append("PHASE60_MODIFIED")

        # 12. Safety contract.
        if out["executionAuthorized"] is not False:
            failures.append("EXECUTION_AUTHORIZATION_VIOLATION")

        if out["sideEffects"]["networkAccess"] is not False:
            failures.append("NETWORK_ACCESS_VIOLATION")

        if out["sideEffects"]["walletAccess"] is not False:
            failures.append("WALLET_ACCESS_VIOLATION")

        if out["safety"]["signingPerformed"] is not False:
            failures.append("SIGNING_VIOLATION")

        if out["safety"]["broadcastPerformed"] is not False:
            failures.append("BROADCAST_VIOLATION")

        if out["safety"]["submissionPerformed"] is not False:
            failures.append("SUBMISSION_VIOLATION")

        if out["type"] != TYPE:
            failures.append("TYPE_INVALID")

    if failures:
        print("FAIL")
        for failure in failures:
            print(failure)
        return 1

    print("12/12 PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
