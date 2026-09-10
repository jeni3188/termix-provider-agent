#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "provider-output" / "aacp-observer"

PHASE56_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CONTINUITY_DRIFT_CONTINUITY_VERIFY"
)

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CONTINUITY_DRIFT_CONTINUITY_STABILITY_VERIFY"
)

PHASE56_OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-verify.json"
)

CHECKPOINT = OUT_DIR / (
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-checkpoint.json"
)

OUTPUT = OUT_DIR / (
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-verify.json"
)


def canonical(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def timezone_aware(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


def is_digest(value):
    return isinstance(value, str) and bool(
        re.fullmatch(r"[0-9a-f]{64}", value)
    )


def safety_ok(obj):
    safety = obj.get("safety")
    if not isinstance(safety, dict):
        return False

    return not any(
        isinstance(value, bool) and value is True
        for value in safety.values()
    )


def validate_phase56(obj):
    errors = []

    if not isinstance(obj, dict):
        return ["phase56_invalid"]

    if obj.get("version") != 1:
        errors.append("phase56_version_invalid")

    if obj.get("type") != PHASE56_TYPE:
        errors.append("phase56_type_invalid")

    if obj.get("mode") != "READ_ONLY":
        errors.append("phase56_mode_invalid")

    if obj.get("executionAuthorized") is not False:
        errors.append("phase56_execution_authorized")

    if not safety_ok(obj):
        errors.append("phase56_safety_violation")

    if obj.get("errorCount") != 0:
        errors.append("phase56_error_count")

    if obj.get("errors") != []:
        errors.append("phase56_errors_nonempty")

    if not timezone_aware(obj.get("generatedAt")):
        errors.append("phase56_generated_at_invalid")

    if obj.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase56_state_invalid")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase56_source_state_invalid")

    readiness = obj.get("readiness")
    if not isinstance(readiness, dict):
        errors.append("phase56_readiness_invalid")
    elif readiness.get("ready") is not True:
        errors.append("phase56_not_ready")

    verification = obj.get("verification")
    if not isinstance(verification, dict):
        errors.append("phase56_verification_invalid")
    else:
        if verification.get("valid") is not True:
            errors.append("phase56_not_valid")

        if verification.get("requiredLayers") != 1:
            errors.append("phase56_required_layers_invalid")

        if verification.get("verifiedLayers") != 1:
            errors.append("phase56_verified_layers_invalid")

        if verification.get("checkpoint") != "VERIFIED":
            errors.append("phase56_checkpoint_invalid")

        if not is_digest(verification.get("continuityDigest")):
            errors.append("phase56_continuity_digest_invalid")

    return errors


def build_projection(phase56):
    verification = phase56["verification"]

    return {
        "version": 1,
        "type": TYPE,
        "mode": phase56.get("mode"),
        "state": phase56.get("state"),
        "sourceState": phase56.get("sourceState"),
        "executionAuthorized": phase56.get("executionAuthorized"),
        "safety": phase56.get("safety"),
        "sideEffects": phase56.get("sideEffects"),
        "readiness": phase56.get("readiness"),
        "verification": {
            "valid": verification.get("valid"),
            "requiredLayers": verification.get("requiredLayers"),
            "verifiedLayers": verification.get("verifiedLayers"),
            "checkpoint": verification.get("checkpoint"),
            "continuityDigest": verification.get("continuityDigest"),
        },
        "errors": phase56.get("errors"),
        "errorCount": phase56.get("errorCount"),
        "policy": phase56.get("policy"),
    }


def build_output(
    phase56,
    state,
    source_state,
    ready,
    valid,
    checkpoint_state,
    verified_layers,
    stability_digest,
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
                "STABILITY_CHECKPOINT_ESTABLISHED"
                if checkpoint_state == "ESTABLISHED"
                else "ALL_REQUIRED_STABILITY_CHECKS_VERIFIED"
                if not errors
                else "BLOCKED"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 1,
            "verifiedLayers": verified_layers,
            "checkpoint": checkpoint_state,
            "stabilityDigest": stability_digest,
            "sourceContinuityDigest": (
                phase56.get("verification", {}).get("continuityDigest")
            ),
        },
        "sources": {
            "phase56": str(PHASE56_OUTPUT.relative_to(ROOT)),
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "readOnly": True,
            "failClosed": True,
            "noNetwork": True,
            "noWallet": True,
            "noSigning": True,
            "noBroadcast": True,
            "noSubmission": True,
        },
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    phase56 = load_json(PHASE56_OUTPUT)
    errors = validate_phase56(phase56)

    if errors:
        output = build_output(
            phase56 or {},
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "BLOCKED",
            0,
            "",
            errors,
        )
        save_json(OUTPUT, output)

        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: BLOCKED")
        print("VERIFIED LAYERS: 0/1")
        print("ERROR COUNT:", len(errors))
        return 1

    projection = build_projection(phase56)
    stability_digest = digest(projection)

    checkpoint_exists = CHECKPOINT.exists()
    checkpoint = load_json(CHECKPOINT) if checkpoint_exists else None

    if checkpoint_exists and checkpoint is None:
        errors = ["checkpoint_corrupt_or_unreadable"]

    elif not checkpoint_exists:
        checkpoint_projection = projection
        checkpoint_digest = digest(checkpoint_projection)

        checkpoint = {
            "version": 1,
            "type": TYPE,
            "createdAt": datetime.now().astimezone().isoformat(),
            "stabilityDigest": stability_digest,
            "checkpointProjection": checkpoint_projection,
            "checkpointDigest": checkpoint_digest,
        }

        save_json(CHECKPOINT, checkpoint)

        output = build_output(
            phase56,
            "CHECKPOINT_ESTABLISHED",
            "CHECKPOINT_ESTABLISHED",
            False,
            True,
            "ESTABLISHED",
            0,
            stability_digest,
            [],
        )

        save_json(OUTPUT, output)

        print("STATE: CHECKPOINT_ESTABLISHED")
        print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
        print("READY: False")
        print("VALID: True")
        print("CHECKPOINT: ESTABLISHED")
        print("VERIFIED LAYERS: 0/1")
        print("STABILITY DIGEST:", stability_digest)
        print("ERROR COUNT: 0")
        return 0

    if not errors:
        if checkpoint.get("version") != 1:
            errors.append("checkpoint_version_invalid")

        if checkpoint.get("type") != TYPE:
            errors.append("checkpoint_type_invalid")

        if not timezone_aware(checkpoint.get("createdAt")):
            errors.append("checkpoint_created_at_invalid")

        if checkpoint.get("stabilityDigest") != stability_digest:
            errors.append("stability_digest_mismatch")

        stored_projection = checkpoint.get("checkpointProjection")
        if stored_projection != projection:
            errors.append("checkpoint_projection_mismatch")

        stored_digest = checkpoint.get("checkpointDigest")
        if not is_digest(stored_digest):
            errors.append("checkpoint_digest_invalid")
        elif stored_digest != digest(stored_projection):
            errors.append("checkpoint_digest_mismatch")

    if errors:
        output = build_output(
            phase56,
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "BLOCKED",
            0,
            stability_digest,
            errors,
        )
        save_json(OUTPUT, output)

        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: BLOCKED")
        print("VERIFIED LAYERS: 0/1")
        print("STABILITY DIGEST:", stability_digest)
        print("ERROR COUNT:", len(errors))
        return 1

    output = build_output(
        phase56,
        "VERIFIED_READ_ONLY",
        "VERIFIED_READ_ONLY",
        True,
        True,
        "VERIFIED",
        1,
        stability_digest,
        [],
    )

    save_json(OUTPUT, output)

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("VERIFIED LAYERS: 1/1")
    print("STABILITY DIGEST:", stability_digest)
    print("ERROR COUNT: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
