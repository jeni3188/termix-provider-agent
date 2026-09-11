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
    "STABILITY_HISTORY_EVOLUTION_VERIFY"
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

BASE = Path("provider-output/aacp-observer")

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-evolution-verify.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-evolution-verify-checkpoint.json"
)

PHASE62_OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-verify.json"
)

PHASE62_HISTORY = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history.json"
)

PHASE62_CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-checkpoint.json"
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
        prefix=".phase64-",
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
            "requiredObservations": 3,
            "observations": 0,
        },
        "verification": {
            "valid": False,
            "checkpoint": "FAILED",
            "historyDigest": "",
            "evolutionDigest": "",
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


def validate_phase62_output(value):
    if not isinstance(value, dict):
        return False

    if value.get("type") != PHASE62_TYPE:
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

    if not isinstance(readiness, dict):
        return False
    if not isinstance(verification, dict):
        return False
    if not isinstance(safety, dict):
        return False
    if not isinstance(side_effects, dict):
        return False

    if readiness.get("requiredObservations") != 3:
        return False

    observations = readiness.get("observations")
    if not isinstance(observations, int) or not 1 <= observations <= 3:
        return False

    if verification.get("valid") is not True:
        return False
    if verification.get("checkpoint") not in {
        "HISTORY_ESTABLISHED",
        "VERIFIED",
    }:
        return False

    if verification.get("historyDigest") is None:
        return False

    for field in (
        "historyDigest",
        "projectionDigest",
        "continuityDigest",
        "semanticDigest",
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

    if verification["checkpoint"] == "HISTORY_ESTABLISHED":
        if readiness.get("ready") is not False:
            return False
        if observations >= 3:
            return False

    if verification["checkpoint"] == "VERIFIED":
        if readiness.get("ready") is not True:
            return False
        if observations != 3:
            return False

    return True


def validate_phase62_checkpoint(checkpoint, phase62):
    if not isinstance(checkpoint, dict):
        return False

    if checkpoint.get("version") != 1:
        return False
    if checkpoint.get("type") != PHASE62_TYPE:
        return False
    if checkpoint.get("requiredObservations") != 3:
        return False

    for field in (
        "projectionDigest",
        "continuityDigest",
        "semanticDigest",
    ):
        if not valid_digest(checkpoint.get(field)):
            return False

    verification = phase62["verification"]

    return (
        checkpoint["projectionDigest"] == verification["projectionDigest"]
        and checkpoint["continuityDigest"] == verification["continuityDigest"]
        and checkpoint["semanticDigest"] == verification["semanticDigest"]
    )


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

        if observation.get("type") != PHASE61_TYPE:
            return False, f"history_observation_{index}_type_invalid"

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
            return False, f"history_observation_{index}_timestamp_timezone_invalid"

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

    expected = digest({
        "version": history["version"],
        "type": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observations": observations,
    })

    if history.get("historyDigest") != expected:
        return False, "history_digest_invalid"

    return True, ""


def observation_digest(observation):
    return digest(observation)


def evolution_projection(history):
    observations = history["observations"]

    return {
        "version": 1,
        "type": TYPE,
        "historyType": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observationCount": len(observations),
        "observationDigests": [
            observation_digest(observation)
            for observation in observations
        ],
        "historyDigest": history["historyDigest"],
    }


def main():
    ok, phase62 = load_json(PHASE62_OUTPUT)
    if not ok:
        fail(["phase62_load_failed"])

    if not validate_phase62_output(phase62):
        fail(["phase62_contract_invalid"])

    ok, history = load_json(PHASE62_HISTORY)
    if not ok:
        fail(["phase62_history_load_failed"])

    history_ok, history_error = validate_history(history)

    if not history_ok:
        fail([history_error])

    if phase62["verification"]["historyDigest"] != history["historyDigest"]:
        fail(["phase62_history_digest_mismatch"])

    ok, checkpoint62 = load_json(PHASE62_CHECKPOINT)
    if not ok:
        fail(["phase62_checkpoint_load_failed"])

    if not validate_phase62_checkpoint(checkpoint62, phase62):
        fail(["phase62_checkpoint_invalid"])

    projection = evolution_projection(history)
    evolution_digest = digest(projection)

    current_observation_digests = projection["observationDigests"]

    checkpoint_state = "HISTORY_ESTABLISHED"
    ready = False

    if CHECKPOINT.exists():
        ok, previous = load_json(CHECKPOINT)

        if not ok or not isinstance(previous, dict):
            fail(["phase64_checkpoint_load_failed"])

        if previous.get("version") != 1:
            fail(["phase64_checkpoint_version_invalid"])

        if previous.get("type") != TYPE:
            fail(["phase64_checkpoint_type_invalid"])

        previous_count = previous.get("observationCount")
        previous_digests = previous.get("observationDigests")

        if (
            not isinstance(previous_count, int)
            or not 1 <= previous_count <= 3
        ):
            fail(["phase64_checkpoint_observation_count_invalid"])

        if (
            not isinstance(previous_digests, list)
            or len(previous_digests) != previous_count
            or any(not valid_digest(item) for item in previous_digests)
        ):
            fail(["phase64_checkpoint_observation_digests_invalid"])

        if previous_count > len(current_observation_digests):
            fail(["phase64_history_shrank"])

        if current_observation_digests[:previous_count] != previous_digests:
            fail(["phase64_history_mutation"])

        if len(current_observation_digests) - previous_count > 1:
            fail(["phase64_history_jump"])

        checkpoint_state = "VERIFIED"
        ready = len(current_observation_digests) >= 3

    checkpoint = {
        "version": 1,
        "type": TYPE,
        "observationCount": len(current_observation_digests),
        "observationDigests": current_observation_digests,
        "historyDigest": history["historyDigest"],
        "evolutionDigest": evolution_digest,
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
            "ready": ready,
            "requiredObservations": 3,
            "observations": len(current_observation_digests),
        },
        "verification": {
            "valid": True,
            "checkpoint": checkpoint_state,
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

    write_json(OUTPUT, result)

    print("STATE:", result["state"])
    print("SOURCE STATE:", result["sourceState"])
    print("READY:", ready)
    print("VALID:", True)
    print("CHECKPOINT:", checkpoint_state)
    print("OBSERVATIONS:", len(current_observation_digests))
    print("HISTORY DIGEST:", history["historyDigest"])
    print("EVOLUTION DIGEST:", evolution_digest)
    print("ERROR COUNT:", 0)


if __name__ == "__main__":
    main()
