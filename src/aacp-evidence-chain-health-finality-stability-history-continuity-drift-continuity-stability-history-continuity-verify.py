#!/usr/bin/env python3

import hashlib
import json
import os
from datetime import datetime, timezone

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_VERIFY"
)

PHASE58_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_VERIFY"
)

BASE = "provider-output/aacp-observer"

PHASE58_PATH = os.path.join(
    BASE,
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-verify.json",
)

HISTORY_PATH = os.path.join(
    BASE,
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history.json",
)

CHECKPOINT_PATH = os.path.join(
    BASE,
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-checkpoint.json",
)

OUTPUT_PATH = os.path.join(
    BASE,
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-verify.json",
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
        canonical(value).encode("utf-8")
    ).hexdigest()


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
        json.dump(
            payload,
            f,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        f.write("\n")

    os.replace(tmp, path)


def timezone_valid(value):
    if not isinstance(value, str):
        return False

    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except Exception:
        return False


def safety_clean(value):
    if not isinstance(value, dict):
        return False

    return not any(v is True for v in value.values())


def validate_phase58(obj):
    errors = []

    if not isinstance(obj, dict):
        return ["PHASE58_NOT_OBJECT"]

    if obj.get("version") != 1:
        errors.append("PHASE58_VERSION_INVALID")

    if obj.get("type") != PHASE58_TYPE:
        errors.append("PHASE58_TYPE_INVALID")

    if obj.get("mode") != "READ_ONLY":
        errors.append("PHASE58_MODE_INVALID")

    if obj.get("executionAuthorized") is not False:
        errors.append("PHASE58_EXECUTION_AUTHORIZATION_VIOLATION")

    if not safety_clean(obj.get("safety")):
        errors.append("PHASE58_SAFETY_VIOLATION")

    side = obj.get("sideEffects")

    if not isinstance(side, dict):
        errors.append("PHASE58_SIDE_EFFECTS_INVALID")
    else:
        for key in (
            "broadcast",
            "networkAccess",
            "signing",
            "submission",
            "walletAccess",
        ):
            if side.get(key) is True:
                errors.append(
                    f"PHASE58_SIDE_EFFECT_{key.upper()}_VIOLATION"
                )

    if obj.get("errorCount") != 0:
        errors.append("PHASE58_ERROR_COUNT_INVALID")

    if obj.get("errors") != []:
        errors.append("PHASE58_ERRORS_NOT_EMPTY")

    if not timezone_valid(obj.get("generatedAt")):
        errors.append("PHASE58_GENERATED_AT_INVALID")

    if obj.get("state") != "VERIFIED_READ_ONLY":
        errors.append("PHASE58_STATE_INVALID")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("PHASE58_SOURCE_STATE_INVALID")

    readiness = obj.get("readiness")

    if not isinstance(readiness, dict):
        errors.append("PHASE58_READINESS_INVALID")
    elif readiness.get("ready") is not True:
        errors.append("PHASE58_NOT_READY")

    verification = obj.get("verification")

    if not isinstance(verification, dict):
        errors.append("PHASE58_VERIFICATION_INVALID")
        return errors

    if verification.get("valid") is not True:
        errors.append("PHASE58_VALIDITY_INVALID")

    if verification.get("requiredObservations") != 3:
        errors.append("PHASE58_REQUIRED_OBSERVATIONS_INVALID")

    if verification.get("observedObservations") != 3:
        errors.append("PHASE58_OBSERVED_OBSERVATIONS_INVALID")

    if verification.get("history") != "VERIFIED_READ_ONLY":
        errors.append("PHASE58_HISTORY_NOT_VERIFIED")

    history_digest = verification.get("historyDigest")

    if not isinstance(history_digest, str) or len(history_digest) != 64:
        errors.append("PHASE58_HISTORY_DIGEST_INVALID")
    else:
        try:
            int(history_digest, 16)
        except ValueError:
            errors.append("PHASE58_HISTORY_DIGEST_NOT_HEX")

    return errors


def validate_history(history):
    errors = []

    if not isinstance(history, dict):
        return ["HISTORY_NOT_OBJECT"]

    if history.get("version") != 1:
        errors.append("HISTORY_VERSION_INVALID")

    expected_type = (
        "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
        "DRIFT_CONTINUITY_STABILITY_HISTORY_VERIFY"
    )

    if history.get("type") != expected_type:
        errors.append("HISTORY_TYPE_INVALID")

    if history.get("requiredObservations") != 3:
        errors.append("HISTORY_REQUIRED_OBSERVATIONS_INVALID")

    observations = history.get("observations")

    if not isinstance(observations, list):
        errors.append("HISTORY_OBSERVATIONS_INVALID")
        return errors

    if len(observations) != 3:
        errors.append("HISTORY_NOT_COMPLETE")

    previous = None

    for index, observation in enumerate(observations):
        prefix = f"OBSERVATION_{index + 1}"

        if not isinstance(observation, dict):
            errors.append(f"{prefix}_INVALID")
            continue

        if observation.get("phase") != 57:
            errors.append(f"{prefix}_PHASE_INVALID")

        if observation.get("type") != (
            "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
            "DRIFT_CONTINUITY_STABILITY_VERIFY"
        ):
            errors.append(f"{prefix}_TYPE_INVALID")

        timestamp = observation.get("generatedAt")

        if not timezone_valid(timestamp):
            errors.append(f"{prefix}_TIME_INVALID")
        else:
            current = datetime.fromisoformat(timestamp)

            if previous is not None and current < previous:
                errors.append(f"{prefix}_TIME_NON_MONOTONIC")

            previous = current

        for field in (
            "semanticDigest",
            "stabilityDigest",
            "sourceContinuityDigest",
        ):
            value = observation.get(field)

            if not isinstance(value, str) or len(value) != 64:
                errors.append(f"{prefix}_{field.upper()}_INVALID")
                continue

            try:
                int(value, 16)
            except ValueError:
                errors.append(f"{prefix}_{field.upper()}_NOT_HEX")

    stored = history.get("historyDigest")

    if not isinstance(stored, str) or len(stored) != 64:
        errors.append("HISTORY_DIGEST_INVALID")
    else:
        try:
            int(stored, 16)
        except ValueError:
            errors.append("HISTORY_DIGEST_NOT_HEX")

    if not errors and stored != history_digest(history):
        errors.append("HISTORY_DIGEST_MISMATCH")

    return errors


def history_projection(history):
    return {
        "version": history.get("version"),
        "type": history.get("type"),
        "requiredObservations": history.get(
            "requiredObservations"
        ),
        "observations": history.get("observations"),
    }


def history_digest(history):
    return digest(history_projection(history))


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint,
    continuity_digest,
    errors,
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
                "HISTORY_CONTINUITY_VERIFIED"
                if ready
                else "CHECKPOINT_ESTABLISHED"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 1,
            "verifiedLayers": 1 if ready else 0,
            "checkpoint": checkpoint,
            "continuityDigest": continuity_digest,
        },
        "sources": {
            "phase58": PHASE58_PATH,
            "history": HISTORY_PATH,
            "checkpoint": CHECKPOINT_PATH,
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
    phase58, phase58_error = load_json(PHASE58_PATH)

    if phase58 is None:
        errors = [phase58_error or "PHASE58_MISSING"]

        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "UNVERIFIED",
            "",
            errors,
        )

        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: UNVERIFIED")
        print("ERROR COUNT:", len(errors))
        return 1

    phase58_errors = validate_phase58(phase58)

    if phase58_errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "UNVERIFIED",
            "",
            phase58_errors,
        )

        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: UNVERIFIED")
        print("ERROR COUNT:", len(phase58_errors))
        return 1

    history, history_error = load_json(HISTORY_PATH)

    if history is None:
        errors = [history_error or "HISTORY_MISSING"]

        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "UNVERIFIED",
            "",
            errors,
        )

        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: UNVERIFIED")
        print("ERROR COUNT:", len(errors))
        return 1

    history_errors = validate_history(history)

    if history_errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "UNVERIFIED",
            "",
            history_errors,
        )

        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: UNVERIFIED")
        print("ERROR COUNT:", len(history_errors))
        return 1

    projection = history_projection(history)
    continuity_digest = digest(projection)

    checkpoint, checkpoint_error = load_json(CHECKPOINT_PATH)

    if checkpoint is None:
        checkpoint_payload = {
            "version": 1,
            "type": TYPE,
            "historyProjection": projection,
            "continuityDigest": continuity_digest,
        }

        write_json(CHECKPOINT_PATH, checkpoint_payload)

        output = build_output(
            "VERIFIED_READ_ONLY",
            "VERIFIED_READ_ONLY",
            False,
            True,
            "CHECKPOINT_ESTABLISHED",
            continuity_digest,
            [],
        )

        write_json(OUTPUT_PATH, output)

        print("STATE: VERIFIED_READ_ONLY")
        print("SOURCE STATE: VERIFIED_READ_ONLY")
        print("READY: False")
        print("VALID: True")
        print("CHECKPOINT: CHECKPOINT_ESTABLISHED")
        print("CONTINUITY DIGEST:", continuity_digest)
        print("ERROR COUNT: 0")
        return 0

    if checkpoint_error:
        errors = [checkpoint_error]

        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "UNVERIFIED",
            "",
            errors,
        )

        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: UNVERIFIED")
        print("ERROR COUNT:", len(errors))
        return 1

    checkpoint_errors = []

    if checkpoint.get("version") != 1:
        checkpoint_errors.append("CHECKPOINT_VERSION_INVALID")

    if checkpoint.get("type") != TYPE:
        checkpoint_errors.append("CHECKPOINT_TYPE_INVALID")

    if checkpoint.get("historyProjection") != projection:
        checkpoint_errors.append("CHECKPOINT_PROJECTION_MISMATCH")

    if checkpoint.get("continuityDigest") != continuity_digest:
        checkpoint_errors.append("CHECKPOINT_DIGEST_MISMATCH")

    if checkpoint_errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "UNVERIFIED",
            "",
            checkpoint_errors,
        )

        write_json(OUTPUT_PATH, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: UNVERIFIED")
        print("ERROR COUNT:", len(checkpoint_errors))
        return 1

    output = build_output(
        "VERIFIED_READ_ONLY",
        "VERIFIED_READ_ONLY",
        True,
        True,
        "VERIFIED",
        continuity_digest,
        [],
    )

    write_json(OUTPUT_PATH, output)

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("CONTINUITY DIGEST:", continuity_digest)
    print("ERROR COUNT: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
