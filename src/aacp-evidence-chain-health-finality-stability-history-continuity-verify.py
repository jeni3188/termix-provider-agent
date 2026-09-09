#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "provider-output" / "aacp-observer"

PHASE53_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_VERIFY"
TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_VERIFY"

PHASE53_PATH = (
    OUT_DIR
    / "latest-aacp-evidence-chain-health-finality-stability-history-verify.json"
)

HISTORY_PATH = (
    OUT_DIR
    / "aacp-evidence-chain-health-finality-stability-history.json"
)

CHECKPOINT_PATH = (
    OUT_DIR
    / "aacp-evidence-chain-health-finality-stability-history-continuity-checkpoint.json"
)

OUTPUT_PATH = (
    OUT_DIR
    / "latest-aacp-evidence-chain-health-finality-stability-history-continuity-verify.json"
)

REQUIRED_OBSERVATIONS = 3
HEX64 = re.compile(r"^[0-9a-f]{64}$")


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
    return datetime.now().astimezone().isoformat()


def timestamp_ok(value):
    if not isinstance(value, str) or not value:
        return False

    try:
        parsed = datetime.fromisoformat(value)
        return (
            parsed.tzinfo is not None
            and parsed.utcoffset() is not None
        )
    except ValueError:
        return False


def safety_ok(obj):
    safety = obj.get("safety")

    if not isinstance(safety, dict):
        return False

    return not any(
        isinstance(value, bool) and value is True
        for value in safety.values()
    )


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def save_json(path, obj):
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def validate_phase53(obj):
    errors = []

    if not isinstance(obj, dict):
        return False, ["phase53_invalid_json"]

    if obj.get("type") != PHASE53_TYPE:
        errors.append("phase53_type_mismatch")

    if obj.get("mode") != "READ_ONLY":
        errors.append("phase53_mode_violation")

    if obj.get("executionAuthorized") is not False:
        errors.append("phase53_execution_authorized")

    if not safety_ok(obj):
        errors.append("phase53_safety_violation")

    if obj.get("errorCount") != 0:
        errors.append("phase53_error_count")

    if obj.get("errors") != []:
        errors.append("phase53_errors_not_empty")

    if not timestamp_ok(obj.get("generatedAt")):
        errors.append("phase53_generated_at_invalid")

    if obj.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase53_state")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase53_source_state")

    readiness = obj.get("readiness")

    if not isinstance(readiness, dict):
        errors.append("phase53_readiness_missing")
    elif readiness.get("ready") is not True:
        errors.append("phase53_not_ready")

    verification = obj.get("verification")

    if not isinstance(verification, dict):
        errors.append("phase53_verification_missing")
        return False, errors

    if verification.get("valid") is not True:
        errors.append("phase53_invalid")

    if verification.get("requiredObservations") != REQUIRED_OBSERVATIONS:
        errors.append("phase53_required_observations")

    if verification.get("observedObservations") != REQUIRED_OBSERVATIONS:
        errors.append("phase53_observed_observations")

    if verification.get("checkpoint") != "VERIFIED":
        errors.append("phase53_checkpoint")

    stability_digest = verification.get("stabilityDigest")

    if (
        not isinstance(stability_digest, str)
        or not HEX64.fullmatch(stability_digest)
    ):
        errors.append("phase53_stability_digest_invalid")

    history_digest = verification.get("historyDigest")

    if (
        not isinstance(history_digest, str)
        or not HEX64.fullmatch(history_digest)
    ):
        errors.append("phase53_history_digest_invalid")

    return not errors, errors


def validate_history(history, expected_stability_digest, expected_history_digest):
    errors = []

    if not isinstance(history, dict):
        return False, ["history_invalid"]

    if history.get("version") != 1:
        errors.append("history_version")

    if history.get("type") != PHASE53_TYPE:
        errors.append("history_type_mismatch")

    if history.get("requiredObservations") != REQUIRED_OBSERVATIONS:
        errors.append("history_required_observations")

    if not timestamp_ok(history.get("createdAt")):
        errors.append("history_created_at_invalid")

    observations = history.get("observations")

    if not isinstance(observations, list):
        errors.append("history_observations_invalid")
        return False, errors

    if len(observations) != REQUIRED_OBSERVATIONS:
        errors.append("history_observation_count")

    for index, observation in enumerate(observations, start=1):
        if not isinstance(observation, dict):
            errors.append(f"history_observation_{index}_invalid")
            continue

        if observation.get("observation") != index:
            errors.append(f"history_observation_{index}_number")

        if not timestamp_ok(observation.get("generatedAt")):
            errors.append(f"history_observation_{index}_generated_at")

        if observation.get("stabilityDigest") != expected_stability_digest:
            errors.append(f"history_observation_{index}_stability_digest")

    projection = history.get("historyProjection")

    if not isinstance(projection, dict):
        errors.append("history_projection_invalid")
    else:
        expected_projection = {
            "version": 1,
            "type": PHASE53_TYPE,
            "mode": "READ_ONLY",
            "requiredObservations": REQUIRED_OBSERVATIONS,
            "observations": observations,
        }

        if projection != expected_projection:
            errors.append("history_projection_mismatch")

        recomputed = digest(projection)

        if recomputed != expected_history_digest:
            errors.append("history_digest_integrity_mismatch")

    stored_digest = history.get("historyDigest")

    if stored_digest != expected_history_digest:
        errors.append("history_digest_mismatch")

    return not errors, errors


def build_projection(phase53, history):
    verification = phase53["verification"]

    return {
        "version": phase53.get("version"),
        "type": TYPE,
        "mode": phase53.get("mode"),
        "state": phase53.get("state"),
        "sourceState": phase53.get("sourceState"),
        "executionAuthorized": phase53.get("executionAuthorized"),
        "safety": phase53.get("safety"),
        "sideEffects": phase53.get("sideEffects"),
        "readiness": phase53.get("readiness"),
        "verification": {
            "valid": verification.get("valid"),
            "requiredObservations": verification.get("requiredObservations"),
            "observedObservations": verification.get("observedObservations"),
            "checkpoint": verification.get("checkpoint"),
            "stabilityDigest": verification.get("stabilityDigest"),
            "historyDigest": verification.get("historyDigest"),
        },
        "history": {
            "version": history.get("version"),
            "type": history.get("type"),
            "requiredObservations": history.get("requiredObservations"),
            "observations": history.get("observations"),
            "historyDigest": history.get("historyDigest"),
        },
        "errors": phase53.get("errors"),
        "errorCount": phase53.get("errorCount"),
        "policy": phase53.get("policy"),
    }


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
                "FINALITY_STABILITY_HISTORY_CONTINUITY_VERIFIED"
                if ready
                else "FINALITY_STABILITY_HISTORY_CONTINUITY_ESTABLISHED"
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
            "phase53": str(PHASE53_PATH.relative_to(BASE)),
            "history": str(HISTORY_PATH.relative_to(BASE)),
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "readOnly": True,
            "failClosed": True,
            "executionAuthorized": False,
        },
    }


def blocked(errors, continuity_digest=""):
    output = build_output(
        "BLOCKED",
        "BLOCKED",
        False,
        False,
        "INVALID",
        continuity_digest,
        errors,
    )

    save_json(OUTPUT_PATH, output)

    print("STATE: BLOCKED")
    print("SOURCE STATE: BLOCKED")
    print("READY: False")
    print("VALID: False")
    print("CHECKPOINT: INVALID")
    print("VERIFIED LAYERS: 0/1")
    print(f"CONTINUITY DIGEST: {continuity_digest}")
    print(f"ERROR COUNT: {len(errors)}")

    return 1


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    phase53 = load_json(PHASE53_PATH)

    valid, errors = validate_phase53(phase53)

    if not valid:
        return blocked(errors)

    history_exists = HISTORY_PATH.exists()
    history = load_json(HISTORY_PATH)

    if not history_exists:
        return blocked(["history_missing"])

    if history is None:
        return blocked(["history_corrupt_or_unreadable"])

    verification = phase53["verification"]
    stability_digest = verification["stabilityDigest"]
    history_digest = verification["historyDigest"]

    history_valid, history_errors = validate_history(
        history,
        stability_digest,
        history_digest,
    )

    if not history_valid:
        return blocked(history_errors)

    projection = build_projection(phase53, history)
    continuity_digest = digest(projection)

    checkpoint_exists = CHECKPOINT_PATH.exists()
    checkpoint = load_json(CHECKPOINT_PATH)

    if not checkpoint_exists:
        checkpoint_projection = {
            "version": 1,
            "type": TYPE,
            "mode": "READ_ONLY",
            "phase53": projection["verification"],
            "history": projection["history"],
        }

        checkpoint_digest = digest(checkpoint_projection)

        save_json(
            CHECKPOINT_PATH,
            {
                "version": 1,
                "type": TYPE,
                "createdAt": now(),
                "continuityDigest": continuity_digest,
                "checkpointProjection": checkpoint_projection,
                "checkpointDigest": checkpoint_digest,
            },
        )

        output = build_output(
            "CHECKPOINT_ESTABLISHED",
            "CHECKPOINT_ESTABLISHED",
            False,
            True,
            "ESTABLISHED",
            continuity_digest,
            [],
        )

        save_json(OUTPUT_PATH, output)

        print("STATE: CHECKPOINT_ESTABLISHED")
        print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
        print("READY: False")
        print("VALID: True")
        print("CHECKPOINT: ESTABLISHED")
        print("VERIFIED LAYERS: 0/1")
        print(f"CONTINUITY DIGEST: {continuity_digest}")
        print("ERROR COUNT: 0")

        return 0

    if checkpoint is None:
        return blocked(
            ["checkpoint_corrupt_or_unreadable"],
            continuity_digest,
        )

    errors = []

    if checkpoint.get("version") != 1:
        errors.append("checkpoint_version")

    if checkpoint.get("type") != TYPE:
        errors.append("checkpoint_type")

    if not timestamp_ok(checkpoint.get("createdAt")):
        errors.append("checkpoint_created_at")

    if checkpoint.get("continuityDigest") != continuity_digest:
        errors.append("continuity_digest_mismatch")

    stored_projection = checkpoint.get("checkpointProjection")

    expected_projection = {
        "version": 1,
        "type": TYPE,
        "mode": "READ_ONLY",
        "phase53": projection["verification"],
        "history": projection["history"],
    }

    if stored_projection != expected_projection:
        errors.append("checkpoint_projection_mismatch")

    checkpoint_digest = checkpoint.get("checkpointDigest")

    if (
        not isinstance(checkpoint_digest, str)
        or not HEX64.fullmatch(checkpoint_digest)
    ):
        errors.append("checkpoint_digest_invalid")
    elif digest(stored_projection) != checkpoint_digest:
        errors.append("checkpoint_digest_integrity_mismatch")

    if errors:
        return blocked(errors, continuity_digest)

    output = build_output(
        "VERIFIED_READ_ONLY",
        "VERIFIED_READ_ONLY",
        True,
        True,
        "VERIFIED",
        continuity_digest,
        [],
    )

    save_json(OUTPUT_PATH, output)

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("VERIFIED LAYERS: 1/1")
    print(f"CONTINUITY DIGEST: {continuity_digest}")
    print("ERROR COUNT: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
