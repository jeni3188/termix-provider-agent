#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "provider-output" / "aacp-observer"

PHASE50_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_CHAIN_FINALITY_VERIFY"
TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_CHAIN_FINALITY_CONTINUITY_VERIFY"

PHASE50_PATH = (
    OUT_DIR
    / "latest-aacp-evidence-chain-health-cross-artifact-attestation-chain-finality-verify.json"
)

CHECKPOINT_PATH = (
    OUT_DIR
    / "aacp-evidence-chain-health-cross-artifact-attestation-chain-finality-continuity-checkpoint.json"
)

OUTPUT_PATH = (
    OUT_DIR
    / "latest-aacp-evidence-chain-health-cross-artifact-attestation-chain-finality-continuity-verify.json"
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
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def now():
    return datetime.now().astimezone().isoformat()


def timestamp_ok(value):
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
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


def validate_phase50(obj):
    errors = []

    if not isinstance(obj, dict):
        return False, ["phase50_invalid_json"]

    if obj.get("type") != PHASE50_TYPE:
        errors.append("phase50_type_mismatch")

    if obj.get("mode") != "READ_ONLY":
        errors.append("phase50_mode_violation")

    if obj.get("executionAuthorized") is not False:
        errors.append("phase50_execution_authorized")

    if not safety_ok(obj):
        errors.append("phase50_safety_violation")

    if obj.get("errorCount") != 0:
        errors.append("phase50_error_count")

    if obj.get("errors") != []:
        errors.append("phase50_errors_not_empty")

    if not timestamp_ok(obj.get("generatedAt")):
        errors.append("phase50_generated_at_invalid")

    verification = obj.get("verification")
    if not isinstance(verification, dict):
        errors.append("phase50_verification_missing")
        return False, errors

    if verification.get("valid") is not True:
        errors.append("phase50_invalid")

    if verification.get("requiredLayers") != 5:
        errors.append("phase50_required_layers")

    if verification.get("verifiedLayers") != 5:
        errors.append("phase50_verified_layers")

    if verification.get("checkpoint") != "VERIFIED":
        errors.append("phase50_checkpoint")

    finality_digest = verification.get("finalityDigest")
    if not isinstance(finality_digest, str) or not HEX64.fullmatch(finality_digest):
        errors.append("phase50_finality_digest_invalid")

    readiness = obj.get("readiness")
    if not isinstance(readiness, dict):
        errors.append("phase50_readiness_missing")
    else:
        if readiness.get("ready") is not True:
            errors.append("phase50_not_ready")

    if obj.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase50_state")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase50_source_state")

    return not errors, errors


def build_projection(phase50):
    verification = phase50["verification"]

    return {
        "version": phase50.get("version"),
        "type": PHASE50_TYPE,
        "mode": phase50.get("mode"),
        "state": phase50.get("state"),
        "sourceState": phase50.get("sourceState"),
        "executionAuthorized": phase50.get("executionAuthorized"),
        "safety": phase50.get("safety"),
        "sideEffects": phase50.get("sideEffects"),
        "readiness": phase50.get("readiness"),
        "verification": verification,
        "sources": phase50.get("sources"),
        "errors": phase50.get("errors"),
        "errorCount": phase50.get("errorCount"),
        "policy": phase50.get("policy"),
    }


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint,
    verified_layers,
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
                "FINALITY_CONTINUITY_VERIFIED"
                if ready
                else "CHECKPOINT_ESTABLISHED"
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 1,
            "verifiedLayers": verified_layers,
            "checkpoint": checkpoint,
            "continuityDigest": continuity_digest,
        },
        "sources": {
            "phase50": str(PHASE50_PATH.relative_to(BASE)),
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

    phase50 = load_json(PHASE50_PATH)

    valid_phase50, phase50_errors = validate_phase50(phase50)

    if not valid_phase50:
        errors = phase50_errors
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
        print("CONTINUITY DIGEST:")
        print(f"ERROR COUNT: {len(errors)}")
        return 1

    projection = build_projection(phase50)
    continuity_digest = digest(projection)

    checkpoint = load_json(CHECKPOINT_PATH)

    if checkpoint is None:
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

        checkpoint_payload = {
            "version": 1,
            "type": TYPE,
            "createdAt": now(),
            "continuityDigest": continuity_digest,
            "continuityProjection": projection,
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
        print(f"CONTINUITY DIGEST: {continuity_digest}")
        print("ERROR COUNT: 0")
        return 0

    errors = []

    if not isinstance(checkpoint, dict):
        errors.append("checkpoint_invalid")
    else:
        if checkpoint.get("type") != TYPE:
            errors.append("checkpoint_type_mismatch")

        checkpoint_digest = checkpoint.get("continuityDigest")
        if checkpoint_digest != continuity_digest:
            errors.append("continuity_digest_mismatch")

        checkpoint_projection = checkpoint.get("continuityProjection")
        if checkpoint_projection != projection:
            errors.append("continuity_projection_mismatch")

        if digest(checkpoint_projection) != checkpoint_digest:
            errors.append("checkpoint_projection_digest_mismatch")

    if errors:
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
        print(f"CONTINUITY DIGEST: {continuity_digest}")
        print(f"ERROR COUNT: {len(errors)}")
        return 1

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
    print(f"CONTINUITY DIGEST: {continuity_digest}")
    print("ERROR COUNT: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
