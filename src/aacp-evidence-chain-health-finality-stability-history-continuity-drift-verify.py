#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "provider-output" / "aacp-observer"

PHASE53_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_VERIFY"
)

PHASE54_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_VERIFY"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_DRIFT_VERIFY"
)

PHASE53_OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-verify.json"
)

PHASE53_HISTORY = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history.json"
)

PHASE54_OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-continuity-verify.json"
)

CHECKPOINT = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-drift-checkpoint.json"
)

OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-continuity-drift-verify.json"
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


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def valid_digest(value):
    return isinstance(value, str) and bool(
        re.fullmatch(r"[0-9a-f]{64}", value)
    )


def valid_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.tzinfo is not None
    except Exception:
        return False


def safety_ok(obj):
    safety = obj.get("safety")
    if not isinstance(safety, dict):
        return False

    return not any(
        isinstance(value, bool) and value is True
        for value in safety.values()
    )


def validate_phase54(obj):
    if not isinstance(obj, dict):
        return False, "phase54_invalid_json"

    if obj.get("version") != 1:
        return False, "phase54_version_invalid"

    if obj.get("type") != PHASE54_TYPE:
        return False, "phase54_type_mismatch"

    if obj.get("mode") != "READ_ONLY":
        return False, "phase54_mode_violation"

    if obj.get("executionAuthorized") is not False:
        return False, "phase54_execution_authorization_violation"

    if not safety_ok(obj):
        return False, "phase54_safety_violation"

    if obj.get("errorCount") != 0:
        return False, "phase54_error_count_nonzero"

    if obj.get("errors") != []:
        return False, "phase54_errors_nonempty"

    if not valid_timestamp(obj.get("generatedAt")):
        return False, "phase54_generated_at_invalid"

    if obj.get("state") != "VERIFIED_READ_ONLY":
        return False, "phase54_state_invalid"

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        return False, "phase54_source_state_invalid"

    readiness = obj.get("readiness")
    if not isinstance(readiness, dict):
        return False, "phase54_readiness_invalid"

    if readiness.get("ready") is not True:
        return False, "phase54_not_ready"

    verification = obj.get("verification")
    if not isinstance(verification, dict):
        return False, "phase54_verification_invalid"

    if verification.get("valid") is not True:
        return False, "phase54_invalid"

    if verification.get("requiredLayers") != 1:
        return False, "phase54_required_layers_invalid"

    if verification.get("verifiedLayers") != 1:
        return False, "phase54_verified_layers_invalid"

    if verification.get("checkpoint") != "VERIFIED":
        return False, "phase54_checkpoint_invalid"

    continuity_digest = verification.get("continuityDigest")

    if not valid_digest(continuity_digest):
        return False, "phase54_continuity_digest_invalid"

    return True, None


def validate_phase53(obj):
    if not isinstance(obj, dict):
        return False, "phase53_invalid_json"

    if obj.get("version") != 1:
        return False, "phase53_version_invalid"

    if obj.get("type") != PHASE53_TYPE:
        return False, "phase53_type_mismatch"

    if obj.get("mode") != "READ_ONLY":
        return False, "phase53_mode_violation"

    if obj.get("executionAuthorized") is not False:
        return False, "phase53_execution_authorization_violation"

    if not safety_ok(obj):
        return False, "phase53_safety_violation"

    if obj.get("errorCount") != 0:
        return False, "phase53_error_count_nonzero"

    if obj.get("errors") != []:
        return False, "phase53_errors_nonempty"

    verification = obj.get("verification")
    if not isinstance(verification, dict):
        return False, "phase53_verification_invalid"

    if verification.get("valid") is not True:
        return False, "phase53_invalid"

    if verification.get("requiredObservations") != 3:
        return False, "phase53_required_observations_invalid"

    if verification.get("observedObservations") != 3:
        return False, "phase53_observed_observations_invalid"

    if verification.get("checkpoint") != "VERIFIED":
        return False, "phase53_checkpoint_invalid"

    if not valid_digest(verification.get("stabilityDigest")):
        return False, "phase53_stability_digest_invalid"

    if not valid_digest(verification.get("historyDigest")):
        return False, "phase53_history_digest_invalid"

    return True, None


def validate_history(history, expected_stability_digest, expected_history_digest):
    if not isinstance(history, dict):
        return False, "history_corrupt_or_unreadable"

    if history.get("version") != 1:
        return False, "history_version_invalid"

    if history.get("type") != PHASE53_TYPE:
        return False, "history_type_mismatch"

    if history.get("requiredObservations") != 3:
        return False, "history_required_observations_invalid"

    if not valid_timestamp(history.get("createdAt")):
        return False, "history_created_at_invalid"

    observations = history.get("observations")

    if not isinstance(observations, list):
        return False, "history_observations_invalid"

    if len(observations) != 3:
        return False, "history_observation_count_invalid"

    for index, observation in enumerate(observations, 1):
        if not isinstance(observation, dict):
            return False, "history_observation_invalid"

        if observation.get("observation") != index:
            return False, "history_observation_number_invalid"

        if not valid_timestamp(observation.get("generatedAt")):
            return False, "history_observation_generated_at_invalid"

        if observation.get("stabilityDigest") != expected_stability_digest:
            return False, "history_observation_stability_digest_mismatch"

    projection = {
        "version": 1,
        "type": PHASE53_TYPE,
        "mode": "READ_ONLY",
        "requiredObservations": 3,
        "observations": observations,
    }

    calculated_history_digest = digest(projection)

    if calculated_history_digest != expected_history_digest:
        return False, "history_digest_mismatch"

    if history.get("historyDigest") != expected_history_digest:
        return False, "stored_history_digest_mismatch"

    return True, None


def build_drift_projection(phase53, phase54, history):
    phase53_verification = phase53["verification"]
    phase54_verification = phase54["verification"]

    return {
        "version": 1,
        "type": TYPE,
        "mode": "READ_ONLY",
        "phase53": {
            "type": phase53.get("type"),
            "verification": {
                "valid": phase53_verification.get("valid"),
                "requiredObservations": phase53_verification.get(
                    "requiredObservations"
                ),
                "observedObservations": phase53_verification.get(
                    "observedObservations"
                ),
                "checkpoint": phase53_verification.get("checkpoint"),
                "stabilityDigest": phase53_verification.get(
                    "stabilityDigest"
                ),
                "historyDigest": phase53_verification.get(
                    "historyDigest"
                ),
            },
        },
        "phase54": {
            "type": phase54.get("type"),
            "state": phase54.get("state"),
            "sourceState": phase54.get("sourceState"),
            "ready": phase54["readiness"].get("ready"),
            "valid": phase54_verification.get("valid"),
            "requiredLayers": phase54_verification.get(
                "requiredLayers"
            ),
            "verifiedLayers": phase54_verification.get(
                "verifiedLayers"
            ),
            "checkpoint": phase54_verification.get("checkpoint"),
            "continuityDigest": phase54_verification.get(
                "continuityDigest"
            ),
        },
        "history": {
            "version": history.get("version"),
            "type": history.get("type"),
            "requiredObservations": history.get(
                "requiredObservations"
            ),
            "observations": history.get("observations"),
            "historyDigest": history.get("historyDigest"),
        },
    }


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint_state,
    verified_layers,
    drift_digest,
    errors,
):
    return {
        "version": 1,
        "type": TYPE,
        "generatedAt": datetime.now().astimezone().isoformat(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": {
            "postPerformed": False,
            "walletUsed": False,
            "signingPerformed": False,
            "broadcastPerformed": False,
            "submissionPerformed": False,
            "privateKeyAccessed": False,
        },
        "sideEffects": {
            "filesystemRead": True,
            "filesystemWrite": True,
            "networkAccess": False,
            "walletAccess": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "readiness": {
            "ready": ready,
            "reason": (
                "NO_DRIFT_DETECTED"
                if ready
                else "CHECKPOINT_ESTABLISHED"
                if valid and checkpoint_state == "ESTABLISHED"
                else "BLOCKED"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 1,
            "verifiedLayers": verified_layers,
            "checkpoint": checkpoint_state,
            "driftDigest": drift_digest,
        },
        "sources": {
            "phase53": str(PHASE53_OUTPUT),
            "phase53History": str(PHASE53_HISTORY),
            "phase54": str(PHASE54_OUTPUT),
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
    errors = []

    phase53 = load_json(PHASE53_OUTPUT)
    phase54 = load_json(PHASE54_OUTPUT)
    history = load_json(PHASE53_HISTORY)

    ok, error = validate_phase53(phase53)
    if not ok:
        errors.append(error)

    ok, error = validate_phase54(phase54)
    if not ok:
        errors.append(error)

    if not PHASE53_HISTORY.exists():
        errors.append("history_missing")
    else:
        ok, error = validate_history(
            history,
            phase53["verification"]["stabilityDigest"]
            if isinstance(phase53, dict)
            and isinstance(phase53.get("verification"), dict)
            else "",
            phase53["verification"]["historyDigest"]
            if isinstance(phase53, dict)
            and isinstance(phase53.get("verification"), dict)
            else "",
        )

        if not ok:
            errors.append(error)

    if errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "INVALID",
            0,
            "",
            errors,
        )
        write_json(OUTPUT, output)
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: INVALID")
        print("VERIFIED LAYERS: 0/1")
        print("DRIFT DIGEST:")
        print(f"ERROR COUNT: {len(errors)}")
        print(f"ERRORS: {errors}")
        return 1

    projection = build_drift_projection(
        phase53,
        phase54,
        history,
    )

    drift_digest = digest(projection)

    if CHECKPOINT.exists():
        checkpoint = load_json(CHECKPOINT)

        if not isinstance(checkpoint, dict):
            errors.append("checkpoint_corrupt_or_unreadable")
        elif checkpoint.get("version") != 1:
            errors.append("checkpoint_version_invalid")
        elif checkpoint.get("type") != TYPE:
            errors.append("checkpoint_type_mismatch")
        elif not valid_timestamp(checkpoint.get("createdAt")):
            errors.append("checkpoint_created_at_invalid")
        elif checkpoint.get("driftDigest") != drift_digest:
            errors.append("drift_digest_mismatch")
        else:
            stored_projection = checkpoint.get("checkpointProjection")

            if stored_projection != projection:
                errors.append("checkpoint_projection_mismatch")

            expected_checkpoint_digest = digest({
                "version": checkpoint.get("version"),
                "type": checkpoint.get("type"),
                "driftDigest": checkpoint.get("driftDigest"),
                "checkpointProjection": stored_projection,
            })

            if checkpoint.get("checkpointDigest") != expected_checkpoint_digest:
                errors.append("checkpoint_digest_mismatch")

        if errors:
            output = build_output(
                "BLOCKED",
                "BLOCKED",
                False,
                False,
                "INVALID",
                0,
                drift_digest,
                errors,
            )
            write_json(OUTPUT, output)
            print("STATE: BLOCKED")
            print("SOURCE STATE: BLOCKED")
            print("READY: False")
            print("VALID: False")
            print("CHECKPOINT: INVALID")
            print("VERIFIED LAYERS: 0/1")
            print(f"DRIFT DIGEST: {drift_digest}")
            print(f"ERROR COUNT: {len(errors)}")
            print(f"ERRORS: {errors}")
            return 1

        output = build_output(
            "VERIFIED_READ_ONLY",
            "VERIFIED_READ_ONLY",
            True,
            True,
            "VERIFIED",
            1,
            drift_digest,
            [],
        )
        write_json(OUTPUT, output)

        print("STATE: VERIFIED_READ_ONLY")
        print("SOURCE STATE: VERIFIED_READ_ONLY")
        print("READY: True")
        print("VALID: True")
        print("CHECKPOINT: VERIFIED")
        print("VERIFIED LAYERS: 1/1")
        print(f"DRIFT DIGEST: {drift_digest}")
        print("ERROR COUNT: 0")
        return 0

    checkpoint = {
        "version": 1,
        "type": TYPE,
        "createdAt": datetime.now().astimezone().isoformat(),
        "driftDigest": drift_digest,
        "checkpointProjection": projection,
    }

    checkpoint["checkpointDigest"] = digest({
        "version": checkpoint["version"],
        "type": checkpoint["type"],
        "driftDigest": checkpoint["driftDigest"],
        "checkpointProjection": checkpoint["checkpointProjection"],
    })

    write_json(CHECKPOINT, checkpoint)

    output = build_output(
        "CHECKPOINT_ESTABLISHED",
        "CHECKPOINT_ESTABLISHED",
        False,
        True,
        "ESTABLISHED",
        0,
        drift_digest,
        [],
    )
    write_json(OUTPUT, output)

    print("STATE: CHECKPOINT_ESTABLISHED")
    print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
    print("READY: False")
    print("VALID: True")
    print("CHECKPOINT: ESTABLISHED")
    print("VERIFIED LAYERS: 0/1")
    print(f"DRIFT DIGEST: {drift_digest}")
    print("ERROR COUNT: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
