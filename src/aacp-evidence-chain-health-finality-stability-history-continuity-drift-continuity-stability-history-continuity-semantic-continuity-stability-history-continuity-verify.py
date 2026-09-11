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
    "STABILITY_HISTORY_CONTINUITY_VERIFY"
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
    "semantic-continuity-stability-history-continuity-verify.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-continuity-verify-checkpoint.json"
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
    "semantic-continuity-stability-history-continuity-checkpoint.json"
)


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def load_json(path):
    try:
        with path.open(encoding="utf-8") as f:
            return True, json.load(f)
    except Exception:
        return False, None


def aware_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.tzinfo is not None and dt.utcoffset() is not None
    except Exception:
        return False


def valid_digest(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def fail(errors):
    result = {
        "type": TYPE,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "INVALID",
        "generatedAt": datetime.now().astimezone().isoformat(),
        "executionAuthorized": False,
        "readiness": {"ready": False},
        "verification": {
            "valid": False,
            "checkpoint": "FAILED",
            "historyDigest": "",
            "continuityDigest": "",
            "semanticDigest": "",
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


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(
        prefix=".phase63-",
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


def validate_phase62_output(x):
    if not isinstance(x, dict):
        return False

    try:
        if x["version"] != 1:
            return False
        if x["type"] != PHASE62_TYPE:
            return False
        if x["mode"] != "READ_ONLY":
            return False
        if x["executionAuthorized"] is not False:
            return False
        if x["state"] != "VERIFIED_READ_ONLY":
            return False
        if x["sourceState"] != "VERIFIED_READ_ONLY":
            return False
        if not aware_timestamp(x["generatedAt"]):
            return False

        r = x["readiness"]
        v = x["verification"]
        s = x["safety"]
        se = x["sideEffects"]

        if not isinstance(r["ready"], bool):
            return False

        if r["requiredObservations"] != 3:
            return False

        if not isinstance(r["observations"], int):
            return False

        if not 1 <= r["observations"] <= 3:
            return False

        if v["valid"] is not True:
            return False

        checkpoint = v["checkpoint"]

        if checkpoint not in ("HISTORY_ESTABLISHED", "VERIFIED"):
            return False

        if checkpoint == "HISTORY_ESTABLISHED":
            if r["ready"] is not False:
                return False
            if r["observations"] >= r["requiredObservations"]:
                return False

        if checkpoint == "VERIFIED":
            if r["ready"] is not True:
                return False
            if r["observations"] != r["requiredObservations"]:
                return False
        if not valid_digest(v["historyDigest"]):
            return False
        if not valid_digest(v["projectionDigest"]):
            return False
        if not valid_digest(v["continuityDigest"]):
            return False
        if not valid_digest(v["semanticDigest"]):
            return False

        if x["errorCount"] != 0 or x["errors"] != []:
            return False

        if s["signingPerformed"] is not False:
            return False
        if s["broadcastPerformed"] is not False:
            return False
        if s["submissionPerformed"] is not False:
            return False
        if se["networkAccess"] is not False:
            return False
        if se["walletAccess"] is not False:
            return False

        return True
    except (KeyError, TypeError):
        return False


def validate_history(history):
    if not isinstance(history, dict):
        return False, "history_not_object"

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

    for i, item in enumerate(observations):
        if not isinstance(item, dict):
            return False, f"history_observation_{i}_invalid"

        if item.get("phase") != 61:
            return False, f"history_observation_{i}_phase_invalid"

        if item.get("type") != (
            "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
            "CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_"
            "SEMANTIC_CONTINUITY_STABILITY_VERIFY"
        ):
            return False, f"history_observation_{i}_type_invalid"

        timestamp = item.get("generatedAt")
        if not aware_timestamp(timestamp):
            return False, f"history_observation_{i}_timestamp_invalid"

        current_time = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

        if previous_time is not None and current_time < previous_time:
            return False, "history_timestamp_regression"

        previous_time = current_time

        for field in (
            "projectionDigest",
            "continuityDigest",
            "semanticDigest",
        ):
            if not valid_digest(item.get(field)):
                return False, f"history_observation_{i}_{field}_invalid"

    expected_history_digest = digest({
        "version": history["version"],
        "type": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observations": history["observations"],
    })

    if history.get("historyDigest") != expected_history_digest:
        return False, "history_digest_invalid"

    return True, ""


def validate_phase62_checkpoint(checkpoint, phase62):
    if not isinstance(checkpoint, dict):
        return False, "phase62_checkpoint_invalid"

    try:
        if checkpoint["version"] != 1:
            return False, "phase62_checkpoint_version_invalid"

        if checkpoint["type"] != PHASE62_TYPE:
            return False, "phase62_checkpoint_type_invalid"

        if checkpoint["requiredObservations"] != 3:
            return False, "phase62_checkpoint_required_observations_invalid"

        for field in (
            "projectionDigest",
            "continuityDigest",
            "semanticDigest",
        ):
            if not valid_digest(checkpoint[field]):
                return False, f"phase62_checkpoint_{field}_invalid"

        v = phase62["verification"]

        if checkpoint["projectionDigest"] != v["projectionDigest"]:
            return False, "phase62_checkpoint_projection_drift"

        if checkpoint["continuityDigest"] != v["continuityDigest"]:
            return False, "phase62_checkpoint_continuity_drift"

        if checkpoint["semanticDigest"] != v["semanticDigest"]:
            return False, "phase62_checkpoint_semantic_drift"

        return True, ""
    except (KeyError, TypeError):
        return False, "phase62_checkpoint_contract_invalid"


def continuity_projection(phase62, history):
    v = phase62["verification"]
    r = phase62["readiness"]

    return {
        "phase62Type": phase62["type"],
        "version": phase62["version"],
        "mode": phase62["mode"],
        "state": phase62["state"],
        "sourceState": phase62["sourceState"],
        "ready": r["ready"],
        "requiredObservations": r["requiredObservations"],
        "observations": r["observations"],
        "checkpoint": v["checkpoint"],
        "historyDigest": v["historyDigest"],
        "projectionDigest": v["projectionDigest"],
        "continuityDigest": v["continuityDigest"],
        "semanticDigest": v["semanticDigest"],
        "historyObservationCount": len(history["observations"]),
        "historyRequiredObservations": history["requiredObservations"],
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

    ok, checkpoint = load_json(PHASE62_CHECKPOINT)
    if not ok:
        fail(["phase62_checkpoint_load_failed"])

    checkpoint_ok, checkpoint_error = validate_phase62_checkpoint(
        checkpoint,
        phase62,
    )
    if not checkpoint_ok:
        fail([checkpoint_error])

    projection = continuity_projection(phase62, history)
    continuity_digest = digest(projection)

    semantic_projection = {
        "type": TYPE,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "ready": phase62["readiness"]["ready"],
        "valid": phase62["verification"]["valid"],
        "checkpoint": phase62["verification"]["checkpoint"],
        "historyDigest": phase62["verification"]["historyDigest"],
        "projectionDigest": phase62["verification"]["projectionDigest"],
        "continuityDigest": phase62["verification"]["continuityDigest"],
        "semanticDigest": phase62["verification"]["semanticDigest"],
        "historyObservationCount": len(history["observations"]),
        "historyRequiredObservations": history["requiredObservations"],
        "executionAuthorized": False,
        "networkAccess": False,
        "walletAccess": False,
        "signingPerformed": False,
        "broadcastPerformed": False,
        "submissionPerformed": False,
        "errorCount": 0,
        "errors": [],
    }

    semantic_digest = digest(semantic_projection)

    if CHECKPOINT.exists():
        ok, phase63_checkpoint = load_json(CHECKPOINT)
        if not ok or not isinstance(phase63_checkpoint, dict):
            fail(["phase63_checkpoint_load_failed"])

        expected = {
            "version": 1,
            "type": TYPE,
            "continuityDigest": continuity_digest,
            "semanticDigest": semantic_digest,
        }

        if phase63_checkpoint != expected:
            fail(["phase63_continuity_stability_drift"])

        checkpoint_state = "VERIFIED"
        ready = True
    else:
        phase63_checkpoint = {
            "version": 1,
            "type": TYPE,
            "continuityDigest": continuity_digest,
            "semanticDigest": semantic_digest,
        }
        write_json(CHECKPOINT, phase63_checkpoint)
        checkpoint_state = "HISTORY_ESTABLISHED"
        ready = False

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
            "phase62HistoryObservations": len(history["observations"]),
        },
        "verification": {
            "valid": True,
            "checkpoint": checkpoint_state,
            "historyDigest": phase62["verification"]["historyDigest"],
            "continuityDigest": continuity_digest,
            "semanticDigest": semantic_digest,
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
    print("PHASE62 HISTORY OBSERVATIONS:", len(history["observations"]))
    print("HISTORY DIGEST:", result["verification"]["historyDigest"])
    print("CONTINUITY DIGEST:", continuity_digest)
    print("SEMANTIC DIGEST:", semantic_digest)
    print("ERROR COUNT:", 0)


if __name__ == "__main__":
    main()
