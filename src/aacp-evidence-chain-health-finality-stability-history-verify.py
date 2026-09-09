#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "provider-output" / "aacp-observer"

PHASE52_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_VERIFY"

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_VERIFY"

PHASE52_PATH = (
    OUT_DIR
    / "latest-aacp-evidence-chain-health-finality-stability-verify.json"
)

HISTORY_PATH = (
    OUT_DIR
    / "aacp-evidence-chain-health-finality-stability-history.json"
)

OUTPUT_PATH = (
    OUT_DIR
    / "latest-aacp-evidence-chain-health-finality-stability-history-verify.json"
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


def validate_phase52(obj):
    errors = []

    if not isinstance(obj, dict):
        return False, ["phase52_invalid_json"]

    if obj.get("type") != PHASE52_TYPE:
        errors.append("phase52_type_mismatch")

    if obj.get("mode") != "READ_ONLY":
        errors.append("phase52_mode_violation")

    if obj.get("executionAuthorized") is not False:
        errors.append("phase52_execution_authorized")

    if not safety_ok(obj):
        errors.append("phase52_safety_violation")

    if obj.get("errorCount") != 0:
        errors.append("phase52_error_count")

    if obj.get("errors") != []:
        errors.append("phase52_errors_not_empty")

    if not timestamp_ok(obj.get("generatedAt")):
        errors.append("phase52_generated_at_invalid")

    if obj.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase52_state")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase52_source_state")

    readiness = obj.get("readiness")

    if not isinstance(readiness, dict):
        errors.append("phase52_readiness_missing")
    elif readiness.get("ready") is not True:
        errors.append("phase52_not_ready")

    verification = obj.get("verification")

    if not isinstance(verification, dict):
        errors.append("phase52_verification_missing")
        return False, errors

    if verification.get("valid") is not True:
        errors.append("phase52_invalid")

    if verification.get("requiredLayers") != 1:
        errors.append("phase52_required_layers")

    if verification.get("verifiedLayers") != 1:
        errors.append("phase52_verified_layers")

    if verification.get("checkpoint") != "VERIFIED":
        errors.append("phase52_checkpoint")

    stability_digest = verification.get("stabilityDigest")

    if (
        not isinstance(stability_digest, str)
        or not HEX64.fullmatch(stability_digest)
    ):
        errors.append("phase52_stability_digest_invalid")

    return not errors, errors


def build_projection(phase52):
    verification = phase52["verification"]

    return {
        "version": phase52.get("version"),
        "type": PHASE52_TYPE,
        "mode": phase52.get("mode"),
        "state": phase52.get("state"),
        "sourceState": phase52.get("sourceState"),
        "executionAuthorized": phase52.get("executionAuthorized"),
        "safety": phase52.get("safety"),
        "sideEffects": phase52.get("sideEffects"),
        "readiness": phase52.get("readiness"),
        "verification": {
            "valid": verification.get("valid"),
            "requiredLayers": verification.get("requiredLayers"),
            "verifiedLayers": verification.get("verifiedLayers"),
            "checkpoint": verification.get("checkpoint"),
            "stabilityDigest": verification.get("stabilityDigest"),
        },
        "errors": phase52.get("errors"),
        "errorCount": phase52.get("errorCount"),
        "policy": phase52.get("policy"),
    }


def observation_digest(projection):
    return digest(projection)


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint,
    observed,
    stability_digest,
    history_digest,
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
                "FINALITY_STABILITY_HISTORY_VERIFIED"
                if ready
                else "STABILITY_HISTORY_IN_PROGRESS"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredObservations": REQUIRED_OBSERVATIONS,
            "observedObservations": observed,
            "checkpoint": checkpoint,
            "stabilityDigest": stability_digest,
            "historyDigest": history_digest,
        },
        "sources": {
            "phase52": str(PHASE52_PATH.relative_to(BASE)),
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "readOnly": True,
            "failClosed": True,
            "executionAuthorized": False,
        },
    }


def blocked(errors, stability_digest=""):
    output = build_output(
        "BLOCKED",
        "BLOCKED",
        False,
        False,
        "INVALID",
        0,
        stability_digest,
        "",
        errors,
    )

    save_json(OUTPUT_PATH, output)

    print("STATE: BLOCKED")
    print("SOURCE STATE: BLOCKED")
    print("READY: False")
    print("VALID: False")
    print("CHECKPOINT: INVALID")
    print("OBSERVATIONS: 0/3")
    print(f"STABILITY DIGEST: {stability_digest}")
    print("HISTORY DIGEST:")
    print(f"ERROR COUNT: {len(errors)}")

    return 1


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    phase52 = load_json(PHASE52_PATH)
    valid, errors = validate_phase52(phase52)

    if not valid:
        return blocked(errors)

    projection = build_projection(phase52)
    stability_digest = observation_digest(projection)

    history_exists = HISTORY_PATH.exists()
    history = load_json(HISTORY_PATH)

    if history_exists and history is None:
        return blocked(
            ["history_corrupt_or_unreadable"],
            stability_digest,
        )

    if history is None:
        observations = [
            {
                "observation": 1,
                "generatedAt": now(),
                "stabilityDigest": stability_digest,
            }
        ]

        history_projection = {
            "version": 1,
            "type": TYPE,
            "mode": "READ_ONLY",
            "requiredObservations": REQUIRED_OBSERVATIONS,
            "observations": observations,
        }

        history_digest = digest(history_projection)

        save_json(
            HISTORY_PATH,
            {
                "version": 1,
                "type": TYPE,
                "createdAt": now(),
                "requiredObservations": REQUIRED_OBSERVATIONS,
                "observations": observations,
                "historyDigest": history_digest,
                "historyProjection": history_projection,
            },
        )

        save_json(
            OUTPUT_PATH,
            build_output(
                "HISTORY_ESTABLISHED",
                "HISTORY_ESTABLISHED",
                False,
                True,
                "ESTABLISHED",
                1,
                stability_digest,
                history_digest,
                [],
            ),
        )

        print("STATE: HISTORY_ESTABLISHED")
        print("SOURCE STATE: HISTORY_ESTABLISHED")
        print("READY: False")
        print("VALID: True")
        print("CHECKPOINT: ESTABLISHED")
        print("OBSERVATIONS: 1/3")
        print(f"STABILITY DIGEST: {stability_digest}")
        print(f"HISTORY DIGEST: {history_digest}")
        print("ERROR COUNT: 0")

        return 0

    if not isinstance(history, dict):
        return blocked(["history_invalid"])

    errors = []

    if history.get("type") != TYPE:
        errors.append("history_type_mismatch")

    if history.get("requiredObservations") != REQUIRED_OBSERVATIONS:
        errors.append("history_required_observations_mismatch")

    observations = history.get("observations")

    if not isinstance(observations, list):
        errors.append("history_observations_invalid")

    history_projection = history.get("historyProjection")
    stored_digest = history.get("historyDigest")

    if not isinstance(history_projection, dict):
        errors.append("history_projection_invalid")

    if not isinstance(stored_digest, str) or not HEX64.fullmatch(stored_digest):
        errors.append("history_digest_invalid")

    if not errors:
        if digest(history_projection) != stored_digest:
            errors.append("history_digest_integrity_mismatch")

        projection_observations = history_projection.get(
            "observations"
        )

        if projection_observations != observations:
            errors.append("history_projection_mismatch")

        if history_projection.get("requiredObservations") != REQUIRED_OBSERVATIONS:
            errors.append("history_projection_required_observations")

    if errors:
        return blocked(errors, stability_digest)

    if len(observations) >= REQUIRED_OBSERVATIONS:
        return blocked(["history_already_complete"], stability_digest)

    last_digest = observations[-1].get("stabilityDigest")

    if last_digest != stability_digest:
        return blocked(
            ["stability_digest_changed"],
            stability_digest,
        )

    next_number = len(observations) + 1

    observations.append(
        {
            "observation": next_number,
            "generatedAt": now(),
            "stabilityDigest": stability_digest,
        }
    )

    history_projection = {
        "version": 1,
        "type": TYPE,
        "mode": "READ_ONLY",
        "requiredObservations": REQUIRED_OBSERVATIONS,
        "observations": observations,
    }

    history_digest = digest(history_projection)

    history["observations"] = observations
    history["historyProjection"] = history_projection
    history["historyDigest"] = history_digest

    save_json(HISTORY_PATH, history)

    ready = len(observations) >= REQUIRED_OBSERVATIONS

    state = (
        "VERIFIED_READ_ONLY"
        if ready
        else "HISTORY_PROGRESS"
    )

    checkpoint = "VERIFIED" if ready else "IN_PROGRESS"

    output = build_output(
        state,
        state,
        ready,
        True,
        checkpoint,
        len(observations),
        stability_digest,
        history_digest,
        [],
    )

    save_json(OUTPUT_PATH, output)

    print(f"STATE: {state}")
    print(f"SOURCE STATE: {state}")
    print(f"READY: {ready}")
    print("VALID: True")
    print(f"CHECKPOINT: {checkpoint}")
    print(f"OBSERVATIONS: {len(observations)}/3")
    print(f"STABILITY DIGEST: {stability_digest}")
    print(f"HISTORY DIGEST: {history_digest}")
    print("ERROR COUNT: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
