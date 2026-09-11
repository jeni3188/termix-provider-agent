#!/usr/bin/env python3

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_HISTORY_INTEGRITY_CONTINUITY_STABILITY_HISTORY_DETERMINISM_VERIFY"
)

PHASE65_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_HISTORY_INTEGRITY_VERIFY"
)

BASE = Path("provider-output/aacp-observer")

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-continuity-stability-history-determinism-verify.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-continuity-stability-history-determinism-verify-checkpoint.json"
)

PHASE65_OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify.json"
)

PHASE65_CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify-checkpoint.json"
)

PHASE64_OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-evolution-verify.json"
)

PHASE64_CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-evolution-verify-checkpoint.json"
)

PHASE62_HISTORY = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history.json"
)


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def valid_digest(value):
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def load_json(path):
    try:
        return True, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False, None


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(
        prefix=".phase69-",
        suffix=".tmp",
        dir=str(path.parent),
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(
                value,
                f,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp, path)

    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def fail(errors):
    result = {
        "type": TYPE,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "INVALID",
        "generatedAt": datetime.now().astimezone().isoformat(),
        "executionAuthorized": False,
        "readiness": {
            "ready": False,
            "observations": 0,
            "requiredObservations": 1,
        },
        "verification": {
            "valid": False,
            "checkpoint": "FAILED",
            "integrityDigest": "",
            "continuityDigest": "",
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
        "errorCount": len(errors),
        "errors": errors,
    }

    write_json(OUTPUT, result)

    print("STATE:", result["state"])
    print("SOURCE STATE:", result["sourceState"])
    print("READY:", False)
    print("VALID:", False)
    print("CHECKPOINT:", "FAILED")
    print("ERROR COUNT:", len(errors))

    raise SystemExit(1)


def validate_phase65_output(value):
    if not isinstance(value, dict):
        return False

    if value.get("type") != PHASE65_TYPE:
        return False
    if value.get("version") != 1:
        return False
    if value.get("mode") != "READ_ONLY":
        return False
    if value.get("state") != "VERIFIED_READ_ONLY":
        return False
    if value.get("sourceState") != "VERIFIED_READ_ONLY":
        return False
    if value.get("executionAuthorized") is not False:
        return False

    readiness = value.get("readiness")
    verification = value.get("verification")
    safety = value.get("safety")
    side_effects = value.get("sideEffects")

    if not all(
        isinstance(x, dict)
        for x in (readiness, verification, safety, side_effects)
    ):
        return False

    observations = readiness.get("observations")

    if (
        readiness.get("requiredObservations") != 3
        or not isinstance(observations, int)
        or observations != 3
    ):
        return False

    if readiness.get("ready") is not True:
        return False

    if verification.get("valid") is not True:
        return False

    if verification.get("checkpoint") != "VERIFIED":
        return False

    for field in (
        "historyDigest",
        "evolutionDigest",
        "integrityDigest",
    ):
        if not valid_digest(verification.get(field)):
            return False

    for field in (
        "signingPerformed",
        "broadcastPerformed",
        "submissionPerformed",
    ):
        if safety.get(field) is not False:
            return False

    for field in (
        "networkAccess",
        "walletAccess",
    ):
        if side_effects.get(field) is not False:
            return False

    if value.get("errorCount") != 0:
        return False

    if value.get("errors") != []:
        return False

    return True


def validate_phase65_checkpoint(checkpoint, phase65):
    if not isinstance(checkpoint, dict):
        return False, "phase65_checkpoint_invalid"

    if checkpoint.get("version") != 1:
        return False, "phase65_checkpoint_version_invalid"

    if checkpoint.get("type") != PHASE65_TYPE:
        return False, "phase65_checkpoint_type_invalid"

    observation_count = checkpoint.get("observationCount")

    if observation_count != 3:
        return False, "phase65_checkpoint_observation_count_invalid"

    for field in (
        "historyDigest",
        "evolutionDigest",
        "integrityDigest",
    ):
        if not valid_digest(checkpoint.get(field)):
            return False, f"phase65_checkpoint_{field}_invalid"

    verification = phase65["verification"]

    for field in (
        "historyDigest",
        "evolutionDigest",
        "integrityDigest",
    ):
        if checkpoint[field] != verification[field]:
            return False, f"phase65_checkpoint_{field}_mismatch"

    if checkpoint["observationCount"] != phase65["readiness"]["observations"]:
        return False, "phase65_checkpoint_observation_count_mismatch"

    return True, ""


def phase65_integrity_projection(
    phase64,
    checkpoint64,
    history,
    evolution_digest,
):
    return {
        "version": 1,
        "type": PHASE65_TYPE,
        "phase64Type": phase64["type"],
        "observationCount": len(history["observations"]),
        "historyDigest": history["historyDigest"],
        "evolutionDigest": evolution_digest,
        "phase64CheckpointDigest": digest(checkpoint64),
        "phase64OutputDigest": digest(phase64),
    }


def continuity_projection(
    phase65,
    checkpoint65,
    reconstructed_integrity_digest,
):
    return {
        "version": 1,
        "type": TYPE,
        "phase65Type": PHASE65_TYPE,
        "observationCount": phase65["readiness"]["observations"],
        "integrityDigest": reconstructed_integrity_digest,
        "phase65CheckpointDigest": digest(checkpoint65),
    }


def main():
    ok, phase65 = load_json(PHASE65_OUTPUT)

    if not ok:
        fail(["phase65_load_failed"])

    if not validate_phase65_output(phase65):
        fail(["phase65_contract_invalid"])

    ok, checkpoint65 = load_json(PHASE65_CHECKPOINT)

    if not ok:
        fail(["phase65_checkpoint_load_failed"])

    checkpoint_ok, checkpoint_error = validate_phase65_checkpoint(
        checkpoint65,
        phase65,
    )

    if not checkpoint_ok:
        fail([checkpoint_error])

    ok, phase64 = load_json(PHASE64_OUTPUT)

    if not ok:
        fail(["phase64_load_failed"])

    ok, checkpoint64 = load_json(PHASE64_CHECKPOINT)

    if not ok:
        fail(["phase64_checkpoint_load_failed"])

    ok, history = load_json(PHASE62_HISTORY)

    if not ok:
        fail(["phase62_history_load_failed"])

    if not isinstance(history, dict):
        fail(["phase62_history_contract_invalid"])

    observations = history.get("observations")

    if (
        history.get("version") != 1
        or not isinstance(observations, list)
        or len(observations) != 3
    ):
        fail(["phase62_history_contract_invalid"])

    observation_digests = [
        digest(observation)
        for observation in observations
    ]

    evolution_projection = {
        "version": 1,
        "type": phase64["type"],
        "historyType": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observationCount": len(observations),
        "observationDigests": observation_digests,
        "historyDigest": history["historyDigest"],
    }

    expected_evolution_digest = digest(evolution_projection)

    if (
        phase65["verification"]["evolutionDigest"]
        != expected_evolution_digest
    ):
        fail(["phase65_evolution_digest_reconstruction_mismatch"])

    integrity = phase65_integrity_projection(
        phase64,
        checkpoint64,
        history,
        expected_evolution_digest,
    )

    expected_integrity_digest = digest(integrity)

    if (
        expected_integrity_digest
        != phase65["verification"]["integrityDigest"]
    ):
        fail(["phase65_integrity_digest_reconstruction_mismatch"])

    continuity = continuity_projection(
        phase65,
        checkpoint65,
        expected_integrity_digest,
    )

    continuity_digest = digest(continuity)

    checkpoint = {
        "version": 1,
        "type": TYPE,
        "observationCount": phase65["readiness"]["observations"],
        "integrityDigest": expected_integrity_digest,
        "continuityDigest": continuity_digest,
        "phase65CheckpointDigest": digest(checkpoint65),
    }

    write_json(CHECKPOINT, checkpoint)

    result = {
        "type": TYPE,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "generatedAt": datetime.now().astimezone().isoformat(),
        "executionAuthorized": False,
        "readiness": {
            "ready": True,
            "observations": phase65["readiness"]["observations"],
            "requiredObservations": 1,
        },
        "verification": {
            "valid": True,
            "checkpoint": "VERIFIED",
            "integrityDigest": expected_integrity_digest,
            "continuityDigest": continuity_digest,
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

    write_json(OUTPUT, result)

    print("STATE:", result["state"])
    print("SOURCE STATE:", result["sourceState"])
    print("READY:", result["readiness"]["ready"])
    print("VALID:", True)
    print("CHECKPOINT:", "VERIFIED")
    print("OBSERVATIONS:", phase65["readiness"]["observations"])
    print("INTEGRITY DIGEST:", expected_integrity_digest)
    print("CONTINUITY DIGEST:", continuity_digest)
    print("ERROR COUNT:", 0)


if __name__ == "__main__":
    main()
