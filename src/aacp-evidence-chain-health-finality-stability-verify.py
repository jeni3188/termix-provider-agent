#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "provider-output" / "aacp-observer"

PHASE51_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_"
    "CHAIN_FINALITY_CONTINUITY_VERIFY"
)

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_VERIFY"

PHASE51_PATH = (
    OUT_DIR
    / "latest-aacp-evidence-chain-health-cross-artifact-attestation-"
      "chain-finality-continuity-verify.json"
)

CHECKPOINT_PATH = (
    OUT_DIR
    / "aacp-evidence-chain-health-finality-stability-checkpoint.json"
)

OUTPUT_PATH = (
    OUT_DIR
    / "latest-aacp-evidence-chain-health-finality-stability-verify.json"
)

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


def build_projection(phase51):
    verification = phase51["verification"]

    return {
        "version": phase51.get("version"),
        "type": PHASE51_TYPE,
        "mode": phase51.get("mode"),
        "state": phase51.get("state"),
        "sourceState": phase51.get("sourceState"),
        "executionAuthorized": phase51.get("executionAuthorized"),
        "safety": phase51.get("safety"),
        "sideEffects": phase51.get("sideEffects"),
        "readiness": phase51.get("readiness"),
        "verification": {
            "valid": verification.get("valid"),
            "requiredLayers": verification.get("requiredLayers"),
            "verifiedLayers": verification.get("verifiedLayers"),
            "checkpoint": verification.get("checkpoint"),
            "continuityDigest": verification.get("continuityDigest"),
        },
        "errors": phase51.get("errors"),
        "errorCount": phase51.get("errorCount"),
        "policy": phase51.get("policy"),
    }


def validate_phase51(obj):
    errors = []

    if not isinstance(obj, dict):
        return False, ["phase51_invalid_json"]

    if obj.get("type") != PHASE51_TYPE:
        errors.append("phase51_type_mismatch")

    if obj.get("mode") != "READ_ONLY":
        errors.append("phase51_mode_violation")

    if obj.get("executionAuthorized") is not False:
        errors.append("phase51_execution_authorized")

    if not safety_ok(obj):
        errors.append("phase51_safety_violation")

    if obj.get("errorCount") != 0:
        errors.append("phase51_error_count")

    if obj.get("errors") != []:
        errors.append("phase51_errors_not_empty")

    if not timestamp_ok(obj.get("generatedAt")):
        errors.append("phase51_generated_at_invalid")

    if obj.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase51_state")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase51_source_state")

    readiness = obj.get("readiness")

    if not isinstance(readiness, dict):
        errors.append("phase51_readiness_missing")
    elif readiness.get("ready") is not True:
        errors.append("phase51_not_ready")

    verification = obj.get("verification")

    if not isinstance(verification, dict):
        errors.append("phase51_verification_missing")
        return False, errors

    if verification.get("valid") is not True:
        errors.append("phase51_invalid")

    if verification.get("requiredLayers") != 1:
        errors.append("phase51_required_layers")

    if verification.get("verifiedLayers") != 1:
        errors.append("phase51_verified_layers")

    if verification.get("checkpoint") != "VERIFIED":
        errors.append("phase51_checkpoint")

    continuity_digest = verification.get("continuityDigest")

    if (
        not isinstance(continuity_digest, str)
        or not HEX64.fullmatch(continuity_digest)
    ):
        errors.append("phase51_continuity_digest_invalid")

    return not errors, errors


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint,
    verified_layers,
    stability_digest,
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
                "FINALITY_STABILITY_VERIFIED"
                if ready
                else "CHECKPOINT_ESTABLISHED"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 1,
            "verifiedLayers": verified_layers,
            "checkpoint": checkpoint,
            "stabilityDigest": stability_digest,
        },
        "sources": {
            "phase51": str(PHASE51_PATH.relative_to(BASE)),
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "readOnly": True,
            "failClosed": True,
            "executionAuthorized": False,
        },
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    phase51 = load_json(PHASE51_PATH)
    valid_phase51, phase51_errors = validate_phase51(phase51)

    if not valid_phase51:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "INVALID",
            0,
            "",
            phase51_errors,
        )

        OUTPUT_PATH.write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: INVALID")
        print("VERIFIED LAYERS: 0/1")
        print("STABILITY DIGEST:")
        print(f"ERROR COUNT: {len(phase51_errors)}")
        return 1

    projection = build_projection(phase51)
    stability_digest = digest(projection)

    checkpoint = load_json(CHECKPOINT_PATH)

    if checkpoint is None:
        output = build_output(
            "CHECKPOINT_ESTABLISHED",
            "CHECKPOINT_ESTABLISHED",
            False,
            True,
            "ESTABLISHED",
            0,
            stability_digest,
            [],
        )

        checkpoint_payload = {
            "version": 1,
            "type": TYPE,
            "createdAt": now(),
            "stabilityDigest": stability_digest,
            "stabilityProjection": projection,
        }

        OUTPUT_PATH.write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        CHECKPOINT_PATH.write_text(
            json.dumps(
                checkpoint_payload,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        print("STATE: CHECKPOINT_ESTABLISHED")
        print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
        print("READY: False")
        print("VALID: True")
        print("CHECKPOINT: ESTABLISHED")
        print("VERIFIED LAYERS: 0/1")
        print(f"STABILITY DIGEST: {stability_digest}")
        print("ERROR COUNT: 0")
        return 0

    errors = []

    if not isinstance(checkpoint, dict):
        errors.append("checkpoint_invalid")
    else:
        if checkpoint.get("type") != TYPE:
            errors.append("checkpoint_type_mismatch")

        checkpoint_digest = checkpoint.get("stabilityDigest")

        if checkpoint_digest != stability_digest:
            errors.append("stability_digest_mismatch")

        checkpoint_projection = checkpoint.get(
            "stabilityProjection"
        )

        if checkpoint_projection != projection:
            errors.append("stability_projection_mismatch")

        if digest(checkpoint_projection) != checkpoint_digest:
            errors.append(
                "checkpoint_projection_digest_mismatch"
            )

    if errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "INVALID",
            0,
            stability_digest,
            errors,
        )

        OUTPUT_PATH.write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: INVALID")
        print("VERIFIED LAYERS: 0/1")
        print(f"STABILITY DIGEST: {stability_digest}")
        print(f"ERROR COUNT: {len(errors)}")
        return 1

    output = build_output(
        "VERIFIED_READ_ONLY",
        "VERIFIED_READ_ONLY",
        True,
        True,
        "VERIFIED",
        1,
        stability_digest,
        [],
    )

    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("VERIFIED LAYERS: 1/1")
    print(f"STABILITY DIGEST: {stability_digest}")
    print("ERROR COUNT: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
