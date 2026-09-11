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
    "STABILITY_HISTORY_VERIFY"
)

PHASE61_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_VERIFY"
)

BASE = Path("provider-output/aacp-observer")

PHASE61_OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-verify.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-verify.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-checkpoint.json"
)

HISTORY = BASE / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history.json"
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
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(c in "0123456789abcdef" for c in value)


def semantic_projection(x):
    v = x["verification"]
    s = x["safety"]
    se = x["sideEffects"]

    return {
        "type": x["type"],
        "version": x["version"],
        "mode": x["mode"],
        "state": x["state"],
        "sourceState": x["sourceState"],
        "ready": x["readiness"]["ready"],
        "valid": v["valid"],
        "checkpoint": v["checkpoint"],
        "continuityDigest": v["continuityDigest"],
        "semanticDigest": v["semanticDigest"],
        "executionAuthorized": x["executionAuthorized"],
        "networkAccess": se["networkAccess"],
        "walletAccess": se["walletAccess"],
        "signingPerformed": s["signingPerformed"],
        "broadcastPerformed": s["broadcastPerformed"],
        "submissionPerformed": s["submissionPerformed"],
        "errorCount": x["errorCount"],
        "errors": x["errors"],
    }


def validate_phase61(x):
    if not isinstance(x, dict):
        return False

    try:
        if x["version"] != 1:
            return False
        if x["type"] != PHASE61_TYPE:
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

        if r["ready"] is not True:
            return False
        if v["valid"] is not True:
            return False
        if v["checkpoint"] != "VERIFIED":
            return False

        if not valid_digest(v["continuityDigest"]):
            return False
        if not valid_digest(v["semanticDigest"]):
            return False

        if x["errorCount"] != 0:
            return False
        if x["errors"] != []:
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


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(
        prefix=".phase62-",
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
        "readiness": {"ready": False},
        "verification": {
            "valid": False,
            "checkpoint": "FAILED",
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


def main():
    ok, phase61 = load_json(PHASE61_OUTPUT)

    if not ok:
        fail(["phase61_load_failed"])

    if not validate_phase61(phase61):
        fail(["phase61_contract_invalid"])

    projection = semantic_projection(phase61)
    projection_digest = digest(projection)

    continuity_digest = phase61["verification"]["continuityDigest"]
    semantic_digest = phase61["verification"]["semanticDigest"]

    observation = {
        "phase": 61,
        "type": PHASE61_TYPE,
        "generatedAt": datetime.now().astimezone().isoformat(),
        "projectionDigest": projection_digest,
        "continuityDigest": continuity_digest,
        "semanticDigest": semantic_digest,
    }

    history_exists = HISTORY.exists()

    if history_exists:
        ok, history = load_json(HISTORY)
        if not ok:
            fail(["history_load_failed"])

        if not isinstance(history, dict):
            fail(["history_not_object"])

        if history.get("version") != 1:
            fail(["history_version_invalid"])

        if history.get("type") != TYPE:
            fail(["history_type_invalid"])

        observations = history.get("observations")

        if not isinstance(observations, list):
            fail(["history_observations_invalid"])

        for i, item in enumerate(observations):
            if not isinstance(item, dict):
                fail([f"history_observation_{i}_invalid"])

            if item.get("phase") != 61:
                fail([f"history_observation_{i}_phase_invalid"])

            if item.get("type") != PHASE61_TYPE:
                fail([f"history_observation_{i}_type_invalid"])

            if not aware_timestamp(item.get("generatedAt")):
                fail([f"history_observation_{i}_timestamp_invalid"])

            for field in (
                "projectionDigest",
                "continuityDigest",
                "semanticDigest",
            ):
                if not valid_digest(item.get(field)):
                    fail([f"history_observation_{i}_{field}_invalid"])

        if observations:
            previous_time = datetime.fromisoformat(
                observations[-1]["generatedAt"].replace("Z", "+00:00")
            )
            current_time = datetime.fromisoformat(
                observation["generatedAt"].replace("Z", "+00:00")
            )

            if current_time < previous_time:
                fail(["history_timestamp_regression"])

    else:
        history = {
            "version": 1,
            "type": TYPE,
            "requiredObservations": 3,
            "observations": [],
        }

    observations = history["observations"]

    if observations:
        previous = observations[-1]

        if previous["projectionDigest"] != projection_digest:
            fail(["semantic_projection_drift"])

        if previous["continuityDigest"] != continuity_digest:
            fail(["continuity_digest_drift"])

        if previous["semanticDigest"] != semantic_digest:
            fail(["semantic_digest_drift"])

    observations.append(observation)

    if len(observations) > 3:
        observations[:] = observations[-3:]

    history_digest = digest({
        "version": history["version"],
        "type": history["type"],
        "requiredObservations": history["requiredObservations"],
        "observations": history["observations"],
    })

    history["historyDigest"] = history_digest

    write_json(HISTORY, history)

    checkpoint_exists = CHECKPOINT.exists()

    if not checkpoint_exists:
        checkpoint = {
            "version": 1,
            "type": TYPE,
            "requiredObservations": 3,
            "projectionDigest": projection_digest,
            "continuityDigest": continuity_digest,
            "semanticDigest": semantic_digest,
        }

        write_json(CHECKPOINT, checkpoint)

        checkpoint_state = "HISTORY_ESTABLISHED"
        ready = False

    else:
        ok, checkpoint = load_json(CHECKPOINT)

        if not ok or not isinstance(checkpoint, dict):
            fail(["checkpoint_load_failed"])

        expected = {
            "version": 1,
            "type": TYPE,
            "requiredObservations": 3,
            "projectionDigest": projection_digest,
            "continuityDigest": continuity_digest,
            "semanticDigest": semantic_digest,
        }

        if checkpoint != expected:
            fail(["history_stability_drift"])

        checkpoint_state = "VERIFIED"
        ready = len(observations) >= 3

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
            "observations": len(observations),
        },
        "verification": {
            "valid": True,
            "checkpoint": checkpoint_state,
            "historyDigest": history_digest,
            "projectionDigest": projection_digest,
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
    print("OBSERVATIONS:", len(observations))
    print("HISTORY DIGEST:", history_digest)
    print("PROJECTION DIGEST:", projection_digest)
    print("CONTINUITY DIGEST:", continuity_digest)
    print("SEMANTIC DIGEST:", semantic_digest)
    print("ERROR COUNT:", 0)


if __name__ == "__main__":
    main()
