#!/usr/bin/env python3

import hashlib
import json
import os
import tempfile
from datetime import datetime


TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_"
    "STABILITY_VERIFY"
)

PHASE60_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_"
    "DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_VERIFY"
)

BASE = "provider-output/aacp-observer"

PHASE60_PATH = os.path.join(
    BASE,
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-verify.json",
)

CHECKPOINT_PATH = os.path.join(
    BASE,
    "aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-checkpoint.json",
)

OUTPUT_PATH = os.path.join(
    BASE,
    "latest-aacp-evidence-chain-health-finality-stability-history-"
    "continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-verify.json",
)

# Phase61 must never overwrite Phase60 artifacts.
if OUTPUT_PATH == PHASE60_PATH:
    raise RuntimeError("PHASE61_OUTPUT_PATH_COLLIDES_WITH_PHASE60")

if CHECKPOINT_PATH == PHASE60_PATH:
    raise RuntimeError("PHASE61_CHECKPOINT_PATH_COLLIDES_WITH_PHASE60")


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def timezone_valid(value):
    if not isinstance(value, str):
        return False

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except (TypeError, ValueError):
        return False


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return True, json.load(handle), []
    except FileNotFoundError:
        return False, None, ["FILE_NOT_FOUND"]
    except (OSError, json.JSONDecodeError):
        return False, None, ["FILE_READ_INVALID"]


def write_json(path, value):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        prefix=".phase61-",
        suffix=".tmp",
        dir=directory,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(
                value,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            handle.write("\n")

        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def semantic_projection(obj):
    readiness = obj.get("readiness")
    verification = obj.get("verification")
    safety = obj.get("safety")
    side_effects = obj.get("sideEffects")

    if not isinstance(readiness, dict):
        readiness = {}
    if not isinstance(verification, dict):
        verification = {}
    if not isinstance(safety, dict):
        safety = {}
    if not isinstance(side_effects, dict):
        side_effects = {}

    return {
        "type": obj.get("type"),
        "version": obj.get("version"),
        "mode": obj.get("mode"),
        "state": obj.get("state"),
        "sourceState": obj.get("sourceState"),
        "ready": readiness.get("ready"),
        "valid": verification.get("valid"),
        "checkpoint": verification.get("checkpoint"),
        "continuityDigest": verification.get("continuityDigest"),
        "semanticDigest": verification.get("semanticDigest"),
        "executionAuthorized": obj.get("executionAuthorized"),
        "networkAccess": side_effects.get("networkAccess"),
        "walletAccess": side_effects.get("walletAccess"),
        "signingPerformed": safety.get("signingPerformed"),
        "broadcastPerformed": safety.get("broadcastPerformed"),
        "submissionPerformed": safety.get("submissionPerformed"),
        "errorCount": obj.get("errorCount"),
        "errors": obj.get("errors"),
    }


def semantic_digest(obj):
    return digest(semantic_projection(obj))


def validate_phase60(obj):
    errors = []

    if not isinstance(obj, dict):
        return ["PHASE60_NOT_OBJECT"]

    if obj.get("version") != 1:
        errors.append("PHASE60_VERSION_INVALID")

    if obj.get("type") != PHASE60_TYPE:
        errors.append("PHASE60_TYPE_INVALID")

    if obj.get("mode") != "READ_ONLY":
        errors.append("PHASE60_MODE_INVALID")

    if obj.get("executionAuthorized") is not False:
        errors.append("PHASE60_EXECUTION_AUTHORIZATION_VIOLATION")

    if obj.get("state") != "VERIFIED_READ_ONLY":
        errors.append("PHASE60_STATE_INVALID")

    if obj.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("PHASE60_SOURCE_STATE_INVALID")

    if not timezone_valid(obj.get("generatedAt")):
        errors.append("PHASE60_GENERATED_AT_INVALID")

    readiness = obj.get("readiness")
    if not isinstance(readiness, dict):
        errors.append("PHASE60_READINESS_INVALID")
    elif readiness.get("ready") is not True:
        errors.append("PHASE60_NOT_READY")

    verification = obj.get("verification")
    if not isinstance(verification, dict):
        errors.append("PHASE60_VERIFICATION_INVALID")
    else:
        if verification.get("valid") is not True:
            errors.append("PHASE60_VALIDITY_INVALID")

        if verification.get("checkpoint") != "VERIFIED":
            errors.append("PHASE60_CHECKPOINT_INVALID")

        for key in ("continuityDigest", "semanticDigest"):
            value = verification.get(key)
            if not isinstance(value, str) or len(value) != 64:
                errors.append(f"PHASE60_{key.upper()}_INVALID")
            else:
                try:
                    int(value, 16)
                except ValueError:
                    errors.append(f"PHASE60_{key.upper()}_NOT_HEX")

    safety = obj.get("safety")
    if not isinstance(safety, dict):
        errors.append("PHASE60_SAFETY_INVALID")
    else:
        for key in (
            "signingPerformed",
            "broadcastPerformed",
            "submissionPerformed",
        ):
            if safety.get(key) is not False:
                errors.append(f"PHASE60_SAFETY_{key.upper()}_VIOLATION")

    side = obj.get("sideEffects")
    if not isinstance(side, dict):
        errors.append("PHASE60_SIDE_EFFECTS_INVALID")
    else:
        if side.get("networkAccess") is not False:
            errors.append("PHASE60_NETWORK_ACCESS_VIOLATION")
        if side.get("walletAccess") is not False:
            errors.append("PHASE60_WALLET_ACCESS_VIOLATION")

    if obj.get("errorCount") != 0:
        errors.append("PHASE60_ERROR_COUNT_INVALID")

    if obj.get("errors") != []:
        errors.append("PHASE60_ERRORS_NOT_EMPTY")

    return errors


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint,
    continuity_digest,
    semantic_digest_value,
    errors,
):
    return {
        "version": 1,
        "type": TYPE,
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "generatedAt": datetime.now().astimezone().isoformat(),
        "executionAuthorized": False,
        "readiness": {
            "ready": ready,
        },
        "verification": {
            "valid": valid,
            "checkpoint": checkpoint,
            "continuityDigest": continuity_digest,
            "semanticDigest": semantic_digest_value,
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


def blocked_output(errors):
    return build_output(
        "UNVERIFIED_READ_ONLY",
        "UNVERIFIED_READ_ONLY",
        False,
        False,
        "BLOCKED",
        "",
        "",
        errors,
    )


def main():
    ok, phase60, load_errors = load_json(PHASE60_PATH)

    if not ok:
        output = blocked_output(
            ["PHASE60_GATE_FAILED"] + load_errors
        )
        write_json(OUTPUT_PATH, output)
        print("STATE:", output["state"])
        print("SOURCE STATE:", output["sourceState"])
        print("READY:", output["readiness"]["ready"])
        print("VALID:", output["verification"]["valid"])
        print("CHECKPOINT:", output["verification"]["checkpoint"])
        print("ERROR COUNT:", output["errorCount"])
        return 1

    phase60_errors = validate_phase60(phase60)

    if phase60_errors:
        output = blocked_output(
            ["PHASE60_CONTRACT_INVALID"] + phase60_errors
        )
        write_json(OUTPUT_PATH, output)
        print("STATE:", output["state"])
        print("SOURCE STATE:", output["sourceState"])
        print("READY:", output["readiness"]["ready"])
        print("VALID:", output["verification"]["valid"])
        print("CHECKPOINT:", output["verification"]["checkpoint"])
        print("ERROR COUNT:", output["errorCount"])
        return 1

    current_projection = semantic_projection(phase60)
    current_digest = digest(current_projection)
    current_semantic_digest = semantic_digest(phase60)

    checkpoint_ok, checkpoint, checkpoint_errors = load_json(
        CHECKPOINT_PATH
    )

    if not checkpoint_ok:
        checkpoint = {
            "version": 1,
            "type": TYPE,
            "semanticProjection": current_projection,
            "continuityDigest": current_digest,
            "semanticDigest": current_semantic_digest,
        }

        write_json(CHECKPOINT_PATH, checkpoint)

        output = build_output(
            "VERIFIED_READ_ONLY",
            "VERIFIED_READ_ONLY",
            False,
            True,
            "CHECKPOINT_ESTABLISHED",
            current_digest,
            current_semantic_digest,
            [],
        )

        write_json(OUTPUT_PATH, output)

        print("STATE:", output["state"])
        print("SOURCE STATE:", output["sourceState"])
        print("READY:", output["readiness"]["ready"])
        print("VALID:", output["verification"]["valid"])
        print("CHECKPOINT:", output["verification"]["checkpoint"])
        print("CONTINUITY DIGEST:", output["verification"]["continuityDigest"])
        print("SEMANTIC DIGEST:", output["verification"]["semanticDigest"])
        print("ERROR COUNT:", output["errorCount"])
        return 0

    errors = []

    if not isinstance(checkpoint, dict):
        errors.append("CHECKPOINT_NOT_OBJECT")
    else:
        if checkpoint.get("version") != 1:
            errors.append("CHECKPOINT_VERSION_INVALID")

        if checkpoint.get("type") != TYPE:
            errors.append("CHECKPOINT_TYPE_INVALID")

        if checkpoint.get("semanticProjection") != current_projection:
            errors.append("SEMANTIC_PROJECTION_MISMATCH")

        if checkpoint.get("continuityDigest") != current_digest:
            errors.append("CONTINUITY_DIGEST_MISMATCH")

        if checkpoint.get("semanticDigest") != current_semantic_digest:
            errors.append("SEMANTIC_DIGEST_MISMATCH")

    if checkpoint_errors:
        errors.extend(checkpoint_errors)

    if errors:
        output = blocked_output(
            ["PHASE61_CHECKPOINT_INVALID"] + errors
        )
        write_json(OUTPUT_PATH, output)
        print("STATE:", output["state"])
        print("SOURCE STATE:", output["sourceState"])
        print("READY:", output["readiness"]["ready"])
        print("VALID:", output["verification"]["valid"])
        print("CHECKPOINT:", output["verification"]["checkpoint"])
        print("ERROR COUNT:", output["errorCount"])
        for error in output["errors"]:
            print("ERROR:", error)
        return 1

    output = build_output(
        "VERIFIED_READ_ONLY",
        "VERIFIED_READ_ONLY",
        True,
        True,
        "VERIFIED",
        current_digest,
        current_semantic_digest,
        [],
    )

    write_json(OUTPUT_PATH, output)

    print("STATE:", output["state"])
    print("SOURCE STATE:", output["sourceState"])
    print("READY:", output["readiness"]["ready"])
    print("VALID:", output["verification"]["valid"])
    print("CHECKPOINT:", output["verification"]["checkpoint"])
    print("CONTINUITY DIGEST:", output["verification"]["continuityDigest"])
    print("SEMANTIC DIGEST:", output["verification"]["semanticDigest"])
    print("ERROR COUNT:", output["errorCount"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
