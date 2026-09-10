#!/usr/bin/env python3

import hashlib
import json
import os
from datetime import datetime, timezone

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_VERIFY"
)

PHASE57_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CONTINUITY_DRIFT_CONTINUITY_STABILITY_VERIFY"
)

BASE = "provider-output/aacp-observer"

PHASE57_PATH = os.path.join(
    BASE,
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-verify.json",
)

HISTORY_PATH = os.path.join(
    BASE,
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history.json",
)

OUTPUT_PATH = os.path.join(
    BASE,
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-verify.json",
)

REQUIRED_OBSERVATIONS = 3


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, "MISSING_FILE"
    except Exception as exc:
        return None, f"CORRUPT_JSON:{exc}"


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def timezone_valid(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.tzinfo is not None
    except Exception:
        return False


def safety_clean(value):
    if not isinstance(value, dict):
        return False
    return not any(v is True for v in value.values())


def validate_phase57(obj):
    errors = []

    if not isinstance(obj, dict):
        return ["PHASE57_NOT_OBJECT"]

    if obj.get("version") != 1:
        errors.append("PHASE57_VERSION_INVALID")

    if obj.get("type") != PHASE57_TYPE:
        errors.append("PHASE57_TYPE_INVALID")

    if obj.get("mode") != "READ_ONLY":
        errors.append("PHASE57_MODE_INVALID")

    if obj.get("executionAuthorized") is not False:
        errors.append("PHASE57_EXECUTION_AUTHORIZATION_VIOLATION")

    if not safety_clean(obj.get("safety")):
        errors.append("PHASE57_SAFETY_VIOLATION")

    side = obj.get("sideEffects")
    if not isinstance(side, dict):
        errors.append("PHASE57_SIDE_EFFECTS_INVALID")
    else:
        for key in (
            "broadcast",
            "networkAccess",
            "signing",
            "submission",
            "walletAccess",
        ):
            if side.get(key) is True:
                errors.append(f"PHASE57_SIDE_EFFECT_{key.upper()}_VIOLATION")

    if obj.get("errorCount") != 0:
        errors.append("PHASE57_ERROR_COUNT_INVALID")

    if obj.get("errors") != []:
        errors.append("PHASE57_ERRORS_NOT_EMPTY")

    if not timezone_valid(obj.get("generatedAt")):
        errors.append("PHASE57_GENERATED_AT_INVALID")

    if obj.get("state") != "VERIFIED_READ_ONLY":
        errors.append("PHASE57_STATE_INVALID")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("PHASE57_SOURCE_STATE_INVALID")

    readiness = obj.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("ready") is not True:
        errors.append("PHASE57_NOT_READY")

    verification = obj.get("verification")
    if not isinstance(verification, dict):
        errors.append("PHASE57_VERIFICATION_INVALID")
        return errors

    if verification.get("valid") is not True:
        errors.append("PHASE57_VALIDITY_INVALID")

    if verification.get("requiredLayers") != 1:
        errors.append("PHASE57_REQUIRED_LAYERS_INVALID")

    if verification.get("verifiedLayers") != 1:
        errors.append("PHASE57_VERIFIED_LAYERS_INVALID")

    if verification.get("checkpoint") != "VERIFIED":
        errors.append("PHASE57_CHECKPOINT_INVALID")

    stability = verification.get("stabilityDigest")
    if not isinstance(stability, str) or len(stability) != 64:
        errors.append("PHASE57_STABILITY_DIGEST_INVALID")
    else:
        try:
            int(stability, 16)
        except ValueError:
            errors.append("PHASE57_STABILITY_DIGEST_NOT_HEX")

    source_digest = verification.get("sourceContinuityDigest")
    if not isinstance(source_digest, str) or len(source_digest) != 64:
        errors.append("PHASE57_SOURCE_CONTINUITY_DIGEST_INVALID")
    else:
        try:
            int(source_digest, 16)
        except ValueError:
            errors.append("PHASE57_SOURCE_CONTINUITY_DIGEST_NOT_HEX")

    return errors


def phase57_projection(obj):
    verification = obj["verification"]

    return {
        "version": 1,
        "type": PHASE57_TYPE,
        "mode": obj.get("mode"),
        "state": obj.get("state"),
        "sourceState": obj.get("sourceState"),
        "executionAuthorized": obj.get("executionAuthorized"),
        "safety": obj.get("safety"),
        "sideEffects": obj.get("sideEffects"),
        "readiness": obj.get("readiness"),
        "verification": {
            "valid": verification.get("valid"),
            "requiredLayers": verification.get("requiredLayers"),
            "verifiedLayers": verification.get("verifiedLayers"),
            "checkpoint": verification.get("checkpoint"),
            "stabilityDigest": verification.get("stabilityDigest"),
            "sourceContinuityDigest": verification.get(
                "sourceContinuityDigest"
            ),
        },
        "errors": obj.get("errors"),
        "errorCount": obj.get("errorCount"),
        "policy": obj.get("policy"),
    }


def observation_from_phase57(obj):
    projection = phase57_projection(obj)
    return {
        "phase": 57,
        "type": PHASE57_TYPE,
        "generatedAt": obj.get("generatedAt"),
        "semanticDigest": digest(projection),
        "stabilityDigest": obj["verification"]["stabilityDigest"],
        "sourceContinuityDigest": obj["verification"][
            "sourceContinuityDigest"
        ],
    }


def history_digest(history):
    projection = {
        "version": history.get("version"),
        "type": history.get("type"),
        "requiredObservations": history.get("requiredObservations"),
        "observations": history.get("observations"),
    }
    return digest(projection)


def validate_history(history):
    errors = []

    if not isinstance(history, dict):
        return ["HISTORY_NOT_OBJECT"]

    if history.get("version") != 1:
        errors.append("HISTORY_VERSION_INVALID")

    if history.get("type") != TYPE:
        errors.append("HISTORY_TYPE_INVALID")

    if history.get("requiredObservations") != REQUIRED_OBSERVATIONS:
        errors.append("HISTORY_REQUIRED_OBSERVATIONS_INVALID")

    observations = history.get("observations")
    if not isinstance(observations, list):
        errors.append("HISTORY_OBSERVATIONS_INVALID")
        return errors

    if len(observations) > REQUIRED_OBSERVATIONS:
        errors.append("HISTORY_TOO_MANY_OBSERVATIONS")

    previous_time = None

    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            errors.append(f"OBSERVATION_{index+1}_INVALID")
            continue

        if observation.get("phase") != 57:
            errors.append(f"OBSERVATION_{index+1}_PHASE_INVALID")

        if observation.get("type") != PHASE57_TYPE:
            errors.append(f"OBSERVATION_{index+1}_TYPE_INVALID")

        timestamp = observation.get("generatedAt")
        if not timezone_valid(timestamp):
            errors.append(f"OBSERVATION_{index+1}_TIME_INVALID")
        else:
            parsed = datetime.fromisoformat(timestamp)
            if previous_time is not None and parsed < previous_time:
                errors.append(f"OBSERVATION_{index+1}_TIME_NON_MONOTONIC")
            previous_time = parsed

        for field in (
            "semanticDigest",
            "stabilityDigest",
            "sourceContinuityDigest",
        ):
            value = observation.get(field)
            if not isinstance(value, str) or len(value) != 64:
                errors.append(
                    f"OBSERVATION_{index+1}_{field.upper()}_INVALID"
                )
            else:
                try:
                    int(value, 16)
                except ValueError:
                    errors.append(
                        f"OBSERVATION_{index+1}_{field.upper()}_NOT_HEX"
                    )

    stored_digest = history.get("historyDigest")

    # A brand-new history is valid before its first observation.
    # The digest is established atomically when observation #1 is appended.
    if len(observations) == 0 and stored_digest is None:
        return errors

    if not isinstance(stored_digest, str) or len(stored_digest) != 64:
        errors.append("HISTORY_DIGEST_INVALID")
    else:
        try:
            int(stored_digest, 16)
        except ValueError:
            errors.append("HISTORY_DIGEST_NOT_HEX")

    if not errors and stored_digest != history_digest(history):
        errors.append("HISTORY_DIGEST_MISMATCH")

    return errors


def build_output(
    state,
    source_state,
    ready,
    valid,
    observations,
    errors,
    history_state,
    history_digest_value,
):
    return {
        "version": 1,
        "type": TYPE,
        "generatedAt": now(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": {
            "broadcastPerformed": False,
            "postPerformed": False,
            "privateKeyAccessed": False,
            "signingPerformed": False,
            "submissionPerformed": False,
            "walletUsed": False,
        },
        "sideEffects": {
            "broadcast": False,
            "filesystemRead": True,
            "filesystemWrite": True,
            "networkAccess": False,
            "signing": False,
            "submission": False,
            "walletAccess": False,
        },
        "readiness": {
            "ready": ready,
            "reason": (
                "HISTORY_COMPLETE_AND_STABLE"
                if ready
                else history_state
            ),
        },
        "verification": {
            "valid": valid,
            "requiredObservations": REQUIRED_OBSERVATIONS,
            "observedObservations": len(observations),
            "history": history_state,
            "historyDigest": history_digest_value,
        },
        "sources": {
            "phase57": PHASE57_PATH,
            "history": HISTORY_PATH,
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "mode": "READ_ONLY",
            "failClosed": True,
            "networkAllowed": False,
            "walletAllowed": False,
            "signingAllowed": False,
            "broadcastAllowed": False,
            "submissionAllowed": False,
        },
    }


def main():
    phase57, phase57_error = load_json(PHASE57_PATH)

    if phase57 is None:
        errors = [phase57_error or "PHASE57_MISSING"]
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            [],
            errors,
            "PHASE57_INVALID",
            "",
        )
        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("HISTORY: PHASE57_INVALID")
        print("ERROR COUNT:", len(errors))
        return 1

    phase57_errors = validate_phase57(phase57)
    if phase57_errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            [],
            phase57_errors,
            "PHASE57_INVALID",
            "",
        )
        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("HISTORY: PHASE57_INVALID")
        print("ERROR COUNT:", len(phase57_errors))
        return 1

    history, history_error = load_json(HISTORY_PATH)

    if history is None:
        if history_error == "MISSING_FILE":
            history = {
                "version": 1,
                "type": TYPE,
                "requiredObservations": REQUIRED_OBSERVATIONS,
                "observations": [],
            }
        else:
            errors = [history_error]
            output = build_output(
                "BLOCKED",
                "BLOCKED",
                False,
                False,
                [],
                errors,
                "HISTORY_CORRUPT",
                "",
            )
            write_json(OUTPUT_PATH, output)
            print("STATE: BLOCKED")
            print("SOURCE STATE: BLOCKED")
            print("READY: False")
            print("VALID: False")
            print("HISTORY: HISTORY_CORRUPT")
            print("ERROR COUNT:", len(errors))
            return 1

    history_errors = validate_history(history)

    if history_errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            history.get("observations", []),
            history_errors,
            "HISTORY_INVALID",
            "",
        )
        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("HISTORY: HISTORY_INVALID")
        print("ERROR COUNT:", len(history_errors))
        return 1

    observations = list(history["observations"])

    if len(observations) < REQUIRED_OBSERVATIONS:
        observation = observation_from_phase57(phase57)
        observations.append(observation)

        history["observations"] = observations
        history["historyDigest"] = history_digest(history)

        write_json(HISTORY_PATH, history)

        if len(observations) == 1:
            history_state = "HISTORY_ESTABLISHED"
        else:
            history_state = "HISTORY_PROGRESS"

        output = build_output(
            "VERIFIED_READ_ONLY",
            "VERIFIED_READ_ONLY",
            False,
            True,
            observations,
            [],
            history_state,
            history["historyDigest"],
        )
        write_json(OUTPUT_PATH, output)

        print("STATE: VERIFIED_READ_ONLY")
        print("SOURCE STATE: VERIFIED_READ_ONLY")
        print("READY: False")
        print("VALID: True")
        print("HISTORY:", history_state)
        print(
            "OBSERVATIONS:",
            len(observations),
            "/",
            REQUIRED_OBSERVATIONS,
        )
        print("HISTORY DIGEST:", history["historyDigest"])
        print("ERROR COUNT: 0")
        return 0

    current = observation_from_phase57(phase57)

    baseline = observations[-1]

    semantic_same = (
        current["semanticDigest"] == baseline["semanticDigest"]
        and current["stabilityDigest"] == baseline["stabilityDigest"]
        and current["sourceContinuityDigest"]
        == baseline["sourceContinuityDigest"]
    )

    if not semantic_same:
        errors = ["PHASE57_HISTORY_SEMANTIC_DRIFT"]
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            observations,
            errors,
            "HISTORY_DRIFT",
            history["historyDigest"],
        )
        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("HISTORY: HISTORY_DRIFT")
        print("ERROR COUNT: 1")
        return 1

    output = build_output(
        "VERIFIED_READ_ONLY",
        "VERIFIED_READ_ONLY",
        True,
        True,
        observations,
        [],
        "VERIFIED_READ_ONLY",
        history["historyDigest"],
    )
    write_json(OUTPUT_PATH, output)

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("HISTORY: VERIFIED_READ_ONLY")
    print(
        "OBSERVATIONS:",
        len(observations),
        "/",
        REQUIRED_OBSERVATIONS,
    )
    print("HISTORY DIGEST:", history["historyDigest"])
    print("ERROR COUNT: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
