#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "provider-output" / "aacp-observer"

PHASE55_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_DRIFT_VERIFY"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_DRIFT_CONTINUITY_VERIFY"
)

PHASE55_OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-continuity-drift-verify.json"
)

CHECKPOINT = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history-continuity-drift-continuity-checkpoint.json"
)

OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-continuity-drift-continuity-verify.json"
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


def validate_phase55(obj):
    if not isinstance(obj, dict):
        return False, "phase55_invalid_json"

    if obj.get("version") != 1:
        return False, "phase55_version_invalid"

    if obj.get("type") != PHASE55_TYPE:
        return False, "phase55_type_mismatch"

    if obj.get("mode") != "READ_ONLY":
        return False, "phase55_mode_violation"

    if obj.get("executionAuthorized") is not False:
        return False, "phase55_execution_authorization_violation"

    if not safety_ok(obj):
        return False, "phase55_safety_violation"

    if obj.get("errorCount") != 0:
        return False, "phase55_error_count_nonzero"

    if obj.get("errors") != []:
        return False, "phase55_errors_nonempty"

    if not valid_timestamp(obj.get("generatedAt")):
        return False, "phase55_generated_at_invalid"

    if obj.get("state") != "VERIFIED_READ_ONLY":
        return False, "phase55_state_invalid"

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        return False, "phase55_source_state_invalid"

    readiness = obj.get("readiness")

    if not isinstance(readiness, dict):
        return False, "phase55_readiness_invalid"

    if readiness.get("ready") is not True:
        return False, "phase55_not_ready"

    verification = obj.get("verification")

    if not isinstance(verification, dict):
        return False, "phase55_verification_invalid"

    if verification.get("valid") is not True:
        return False, "phase55_invalid"

    if verification.get("requiredLayers") != 1:
        return False, "phase55_required_layers_invalid"

    if verification.get("verifiedLayers") != 1:
        return False, "phase55_verified_layers_invalid"

    if verification.get("checkpoint") != "VERIFIED":
        return False, "phase55_checkpoint_invalid"

    if not valid_digest(verification.get("driftDigest")):
        return False, "phase55_drift_digest_invalid"

    return True, None


def build_projection(phase55):
    verification = phase55["verification"]

    return {
        "version": 1,
        "type": TYPE,
        "mode": phase55.get("mode"),
        "state": phase55.get("state"),
        "sourceState": phase55.get("sourceState"),
        "executionAuthorized": phase55.get(
            "executionAuthorized"
        ),
        "safety": phase55.get("safety"),
        "sideEffects": phase55.get("sideEffects"),
        "readiness": phase55.get("readiness"),
        "verification": {
            "valid": verification.get("valid"),
            "requiredLayers": verification.get(
                "requiredLayers"
            ),
            "verifiedLayers": verification.get(
                "verifiedLayers"
            ),
            "checkpoint": verification.get(
                "checkpoint"
            ),
            "driftDigest": verification.get(
                "driftDigest"
            ),
        },
        "errors": phase55.get("errors"),
        "errorCount": phase55.get("errorCount"),
        "policy": phase55.get("policy"),
    }


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint_state,
    verified_layers,
    continuity_digest,
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
                "NO_DRIFT_CONTINUITY_CHANGE"
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
            "continuityDigest": continuity_digest,
        },
        "sources": {
            "phase55": str(PHASE55_OUTPUT),
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


def blocked(errors, continuity_digest=""):
    output = build_output(
        "BLOCKED",
        "BLOCKED",
        False,
        False,
        "INVALID",
        0,
        continuity_digest,
        errors,
    )

    write_json(OUTPUT, output)

    print("STATE: BLOCKED")
    print("SOURCE STATE: BLOCKED")
    print("READY: False")
    print("VALID: False")
    print("CHECKPOINT: INVALID")
    print("VERIFIED LAYERS: 0/1")
    print(f"CONTINUITY DIGEST: {continuity_digest}")
    print(f"ERROR COUNT: {len(errors)}")
    print(f"ERRORS: {errors}")

    return 1


def main():
    errors = []

    if not PHASE55_OUTPUT.exists():
        errors.append("phase55_missing")

    phase55 = load_json(PHASE55_OUTPUT)

    ok, error = validate_phase55(phase55)

    if not ok:
        errors.append(error)

    if errors:
        return blocked(errors)

    projection = build_projection(phase55)
    continuity_digest = digest(projection)

    if CHECKPOINT.exists():
        checkpoint = load_json(CHECKPOINT)

        if not isinstance(checkpoint, dict):
            errors.append("checkpoint_corrupt_or_unreadable")

        elif checkpoint.get("version") != 1:
            errors.append("checkpoint_version_invalid")

        elif checkpoint.get("type") != TYPE:
            errors.append("checkpoint_type_mismatch")

        elif not valid_timestamp(
            checkpoint.get("createdAt")
        ):
            errors.append("checkpoint_created_at_invalid")

        elif checkpoint.get(
            "continuityDigest"
        ) != continuity_digest:
            errors.append("continuity_digest_mismatch")

        stored_projection = checkpoint.get(
            "checkpointProjection"
        )

        if not errors and stored_projection != projection:
            errors.append("checkpoint_projection_mismatch")

        if not errors:
            expected_checkpoint_digest = digest({
                "version": checkpoint.get("version"),
                "type": checkpoint.get("type"),
                "continuityDigest": checkpoint.get(
                    "continuityDigest"
                ),
                "checkpointProjection": stored_projection,
            })

            if checkpoint.get(
                "checkpointDigest"
            ) != expected_checkpoint_digest:
                errors.append(
                    "checkpoint_digest_mismatch"
                )

        if errors:
            return blocked(
                errors,
                continuity_digest,
            )

        output = build_output(
            "VERIFIED_READ_ONLY",
            "VERIFIED_READ_ONLY",
            True,
            True,
            "VERIFIED",
            1,
            continuity_digest,
            [],
        )

        write_json(OUTPUT, output)

        print("STATE: VERIFIED_READ_ONLY")
        print("SOURCE STATE: VERIFIED_READ_ONLY")
        print("READY: True")
        print("VALID: True")
        print("CHECKPOINT: VERIFIED")
        print("VERIFIED LAYERS: 1/1")
        print(
            f"CONTINUITY DIGEST: {continuity_digest}"
        )
        print("ERROR COUNT: 0")

        return 0

    checkpoint = {
        "version": 1,
        "type": TYPE,
        "createdAt": datetime.now().astimezone().isoformat(),
        "continuityDigest": continuity_digest,
        "checkpointProjection": projection,
    }

    checkpoint["checkpointDigest"] = digest({
        "version": checkpoint["version"],
        "type": checkpoint["type"],
        "continuityDigest": checkpoint[
            "continuityDigest"
        ],
        "checkpointProjection": checkpoint[
            "checkpointProjection"
        ],
    })

    write_json(CHECKPOINT, checkpoint)

    output = build_output(
        "CHECKPOINT_ESTABLISHED",
        "CHECKPOINT_ESTABLISHED",
        False,
        True,
        "ESTABLISHED",
        0,
        continuity_digest,
        [],
    )

    write_json(OUTPUT, output)

    print("STATE: CHECKPOINT_ESTABLISHED")
    print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
    print("READY: False")
    print("VALID: True")
    print("CHECKPOINT: ESTABLISHED")
    print("VERIFIED LAYERS: 0/1")
    print(
        f"CONTINUITY DIGEST: {continuity_digest}"
    )
    print("ERROR COUNT: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
