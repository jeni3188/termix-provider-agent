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
    "STABILITY_HISTORY_INTEGRITY_VERIFY"
)

PHASE64_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_HISTORY_EVOLUTION_VERIFY"
)

PHASE62_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_HISTORY_VERIFY"
)

BASE = Path("provider-output/aacp-observer")

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify.json"
)

CHECKPOINT = BASE / (
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
        prefix=".phase65-",
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
            "requiredObservations": 3,
        },
        "verification": {
            "valid": False,
            "checkpoint": "FAILED",
            "historyDigest": "",
            "evolutionDigest": "",
            "integrityDigest": "",
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


def validate_phase64_output(value):
    if not isinstance(value, dict):
        return False

    if value.get("type") != PHASE64_TYPE:
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
        or not 1 <= observations <= 3
    ):
        return False

    if verification.get("valid") is not True:
        return False

    if verification.get("checkpoint") not in {
        "HISTORY_ESTABLISHED",
        "VERIFIED",
    }:
        return False

    for field in (
        "historyDigest",
        "evolutionDigest",
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

    expected_ready = observations == 3

    if readiness.get("ready") is not expected_ready:
        return False

    if observations == 1:
        if verification.get("checkpoint") != "HISTORY_ESTABLISHED":
            return False
    else:
        if verification.get("checkpoint") != "VERIFIED":
            return False

    return True


def validate_history(history):
    if not isinstance(history, dict):
        return False, "history_contract_invalid"

    if history.get("version") != 1:
        return False, "history_version_invalid"

    if history.get("type") != PHASE62_TYPE:
        return False, "history_type_invalid"

    if history.get("requiredObservations") != 3:
        return False, "history_required_observations_invalid"

    observations = history.get("observations")

    if not isinstance(observations, list):
        return False, "history_observations_invalid"

    if not 1 <= len(observations) <= 3:
        return False, "history_observation_count_invalid"

    previous_time = None

    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            return False, f"history_observation_{index}_invalid"

        if observation.get("phase") != 61:
            return False, f"history_observation_{index}_phase_invalid"

        generated_at = observation.get("generatedAt")

        if not isinstance(generated_at, str):
            return False, f"history_observation_{index}_timestamp_invalid"

        try:
            current_time = datetime.fromisoformat(
                generated_at.replace("Z", "+00:00")
            )
        except ValueError:
            return False, f"history_observation_{index}_timestamp_invalid"

        if current_time.tzinfo is None:
            return False, (
                f"history_observation_{index}_timestamp_timezone_invalid"
            )

        if previous_time is not None and current_time < previous_time:
            return False, "history_timestamp_regression"

        previous_time = current_time

        for field in (
            "projectionDigest",
            "continuityDigest",
            "semanticDigest",
        ):
            if not valid_digest(observation.get(field)):
                return False, f"history_observation_{index}_{field}_invalid"

    expected_history_digest = digest({
        "version": history["version"],
        "type": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observations": observations,
    })

    if history.get("historyDigest") != expected_history_digest:
        return False, "history_digest_invalid"

    return True, ""


def observation_digest(observation):
    return digest(observation)


def evolution_projection(history):
    observations = history["observations"]

    return {
        "version": 1,
        "type": PHASE64_TYPE,
        "historyType": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observationCount": len(observations),
        "observationDigests": [
            observation_digest(observation)
            for observation in observations
        ],
        "historyDigest": history["historyDigest"],
    }


def validate_phase64_checkpoint(checkpoint, phase64):
    if not isinstance(checkpoint, dict):
        return False, "phase64_checkpoint_invalid"

    if checkpoint.get("version") != 1:
        return False, "phase64_checkpoint_version_invalid"

    if checkpoint.get("type") != PHASE64_TYPE:
        return False, "phase64_checkpoint_type_invalid"

    count = checkpoint.get("observationCount")
    digests = checkpoint.get("observationDigests")

    if not isinstance(count, int) or not 1 <= count <= 3:
        return False, "phase64_checkpoint_observation_count_invalid"

    if (
        not isinstance(digests, list)
        or len(digests) != count
        or any(not valid_digest(x) for x in digests)
    ):
        return False, "phase64_checkpoint_observation_digests_invalid"

    for field in ("historyDigest", "evolutionDigest"):
        if not valid_digest(checkpoint.get(field)):
            return False, f"phase64_checkpoint_{field}_invalid"

    verification = phase64["verification"]

    if checkpoint["historyDigest"] != verification["historyDigest"]:
        return False, "phase64_checkpoint_history_digest_mismatch"

    if checkpoint["evolutionDigest"] != verification["evolutionDigest"]:
        return False, "phase64_checkpoint_evolution_digest_mismatch"

    if checkpoint["observationCount"] != phase64["readiness"]["observations"]:
        return False, "phase64_checkpoint_observation_count_mismatch"

    return True, ""


def integrity_projection(
    phase64,
    checkpoint64,
    history,
    evolution_digest,
):
    return {
        "version": 1,
        "type": TYPE,
        "phase64Type": PHASE64_TYPE,
        "observationCount": len(history["observations"]),
        "historyDigest": history["historyDigest"],
        "evolutionDigest": evolution_digest,
        "phase64CheckpointDigest": digest(checkpoint64),
        "phase64OutputDigest": digest(phase64),
    }


def main():
    ok, phase64 = load_json(PHASE64_OUTPUT)

    if not ok:
        fail(["phase64_load_failed"])

    if not validate_phase64_output(phase64):
        fail(["phase64_contract_invalid"])

    ok, history = load_json(PHASE62_HISTORY)

    if not ok:
        fail(["phase62_history_load_failed"])

    history_ok, history_error = validate_history(history)

    if not history_ok:
        fail([history_error])

    projection = evolution_projection(history)
    expected_evolution_digest = digest(projection)

    if (
        phase64["verification"]["historyDigest"]
        != history["historyDigest"]
    ):
        fail(["phase64_history_digest_mismatch"])

    if (
        phase64["verification"]["evolutionDigest"]
        != expected_evolution_digest
    ):
        fail(["phase64_evolution_digest_mismatch"])

    if phase64["readiness"]["observations"] != len(history["observations"]):
        fail(["phase64_observation_count_mismatch"])

    ok, checkpoint64 = load_json(PHASE64_CHECKPOINT)

    if not ok:
        fail(["phase64_checkpoint_load_failed"])

    checkpoint_ok, checkpoint_error = validate_phase64_checkpoint(
        checkpoint64,
        phase64,
    )

    if not checkpoint_ok:
        fail([checkpoint_error])

    expected_observation_digests = projection["observationDigests"]

    if checkpoint64["observationDigests"] != expected_observation_digests:
        fail(["phase64_observation_digest_mismatch"])

    integrity = integrity_projection(
        phase64,
        checkpoint64,
        history,
        expected_evolution_digest,
    )

    integrity_digest = digest(integrity)

    checkpoint = {
        "version": 1,
        "type": TYPE,
        "observationCount": len(history["observations"]),
        "historyDigest": history["historyDigest"],
        "evolutionDigest": expected_evolution_digest,
        "integrityDigest": integrity_digest,
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
            "ready": len(history["observations"]) == 3,
            "observations": len(history["observations"]),
            "requiredObservations": 3,
        },
        "verification": {
            "valid": True,
            "checkpoint": "VERIFIED",
            "historyDigest": history["historyDigest"],
            "evolutionDigest": expected_evolution_digest,
            "integrityDigest": integrity_digest,
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
    print("OBSERVATIONS:", len(history["observations"]))
    print("HISTORY DIGEST:", history["historyDigest"])
    print("EVOLUTION DIGEST:", expected_evolution_digest)
    print("INTEGRITY DIGEST:", integrity_digest)
    print("ERROR COUNT:", 0)


if __name__ == "__main__":
    main()
