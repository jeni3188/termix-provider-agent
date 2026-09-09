#!/usr/bin/env python3

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OBSERVER_DIR = BASE_DIR / "provider-output" / "aacp-observer"

PHASE38_FILE = (
    OBSERVER_DIR
    / "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json"
)

CHECKPOINT_FILE = (
    OBSERVER_DIR
    / "aacp-evidence-chain-health-semantic-checkpoint.json"
)

OUTPUT_FILE = (
    OBSERVER_DIR
    / "latest-aacp-evidence-chain-health-semantic-checkpoint-verify.json"
)

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_SEMANTIC_CHECKPOINT_VERIFY"
CHECKPOINT_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_SEMANTIC_CHECKPOINT"

SEMANTIC_FIELDS = (
    "version",
    "type",
    "mode",
    "state",
    "sourceState",
    "executionAuthorized",
    "safety",
    "sideEffects",
    "readiness",
    "verification",
    "sources",
    "errors",
    "errorCount",
    "policy",
)


def now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def semantic_projection(data):
    return {
        key: data.get(key)
        for key in SEMANTIC_FIELDS
    }


def semantic_digest(data):
    canonical = canonical_json(semantic_projection(data))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_phase38(data):
    errors = []

    if not isinstance(data, dict):
        return ["phase38 output is not an object"]

    expected_type = (
        "AACP_EVIDENCE_CHAIN_HEALTH_CONTINUOUS_READINESS_REPEATABILITY_VERIFY"
    )

    if data.get("type") != expected_type:
        errors.append("phase38 type mismatch")

    if data.get("mode") != "READ_ONLY":
        errors.append("phase38 mode is not READ_ONLY")

    if data.get("executionAuthorized") is not False:
        errors.append("phase38 executionAuthorized must be false")

    if data.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase38 state is not VERIFIED_READ_ONLY")

    if data.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase38 sourceState is not VERIFIED_READ_ONLY")

    readiness = data.get("readiness")
    if not isinstance(readiness, dict):
        errors.append("phase38 readiness missing")
    elif readiness.get("ready") is not True:
        errors.append("phase38 readiness.ready must be true")

    verification = data.get("verification")
    if not isinstance(verification, dict):
        errors.append("phase38 verification missing")
    else:
        if verification.get("valid") is not True:
            errors.append("phase38 verification.valid must be true")
        if verification.get("requiredLayers") != 5:
            errors.append("phase38 requiredLayers must be 5")
        if verification.get("verifiedLayers") != 5:
            errors.append("phase38 verifiedLayers must be 5")

    if data.get("errorCount") != 0:
        errors.append("phase38 errorCount must be zero")

    if data.get("errors") != []:
        errors.append("phase38 errors must be empty")

    safety = data.get("safety")
    if not isinstance(safety, dict):
        errors.append("phase38 safety missing")
    else:
        for key in (
            "postPerformed",
            "walletUsed",
            "signingPerformed",
            "broadcastPerformed",
            "submissionPerformed",
        ):
            if safety.get(key) is not False:
                errors.append(f"phase38 safety.{key} must be false")

    side_effects = data.get("sideEffects")
    if not isinstance(side_effects, dict):
        errors.append("phase38 sideEffects missing")
    else:
        for key in (
            "network",
            "wallet",
            "signing",
            "broadcast",
            "submission",
        ):
            if side_effects.get(key) is not False:
                errors.append(f"phase38 sideEffects.{key} must be false")

    policy = data.get("policy")
    if not isinstance(policy, dict):
        errors.append("phase38 policy missing")
    else:
        expected_false = (
            "networkAccess",
            "walletAccess",
            "signingAllowed",
            "broadcastAllowed",
            "submissionAllowed",
        )

        for key in expected_false:
            if policy.get(key) is not False:
                errors.append(f"phase38 policy.{key} must be false")

        if policy.get("readOnly") is not True:
            errors.append("phase38 policy.readOnly must be true")

        if policy.get("failClosed") is not True:
            errors.append("phase38 policy.failClosed must be true")

    return errors


def validate_checkpoint(data):
    errors = []

    if not isinstance(data, dict):
        return ["checkpoint is not an object"]

    if data.get("type") != CHECKPOINT_TYPE:
        errors.append("checkpoint type mismatch")

    if data.get("mode") != "READ_ONLY":
        errors.append("checkpoint mode is not READ_ONLY")

    if data.get("executionAuthorized") is not False:
        errors.append("checkpoint executionAuthorized must be false")

    digest = data.get("semanticDigest")
    if not isinstance(digest, str) or len(digest) != 64:
        errors.append("checkpoint semanticDigest invalid")

    projection = data.get("semanticProjection")
    if not isinstance(projection, dict):
        errors.append("checkpoint semanticProjection missing")

    return errors


def build_output(
    state,
    source_state,
    ready,
    valid,
    digest,
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
        },
        "sideEffects": {
            "network": False,
            "filesystemWrite": True,
            "wallet": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "readiness": {
            "ready": ready,
            "reason": (
                "SEMANTIC_CHECKPOINT_VERIFIED"
                if ready
                else "SEMANTIC_CHECKPOINT_BLOCKED"
            ),
        },
        "verification": {
            "valid": valid,
            "checkpointEstablished": (
                CHECKPOINT_FILE.exists()
                and not errors
            ),
            "semanticDigest": digest,
            "algorithm": "SHA-256",
        },
        "sources": {
            "phase38": str(
                PHASE38_FILE.relative_to(BASE_DIR)
            ),
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "readOnly": True,
            "failClosed": True,
            "networkAccess": False,
            "walletAccess": False,
            "signingAllowed": False,
            "broadcastAllowed": False,
            "submissionAllowed": False,
        },
    }


def write_output(output):
    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    OBSERVER_DIR.mkdir(parents=True, exist_ok=True)

    errors = []

    phase38, phase38_error = load_json(PHASE38_FILE)

    if phase38_error:
        errors.append(f"phase38 unavailable: {phase38_error}")
    else:
        errors.extend(validate_phase38(phase38))

    if errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            None,
            errors,
        )
        write_output(output)

        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: BLOCKED")
        print(f"ERROR COUNT: {len(errors)}")
        return 1

    digest = semantic_digest(phase38)

    if not CHECKPOINT_FILE.exists():
        checkpoint = {
            "version": 1,
            "type": CHECKPOINT_TYPE,
            "createdAt": now(),
            "mode": "READ_ONLY",
            "executionAuthorized": False,
            "algorithm": "SHA-256",
            "semanticDigest": digest,
            "semanticProjection": semantic_projection(phase38),
            "policy": {
                "readOnly": True,
                "failClosed": True,
                "networkAccess": False,
                "walletAccess": False,
                "signingAllowed": False,
                "broadcastAllowed": False,
                "submissionAllowed": False,
            },
        }

        CHECKPOINT_FILE.write_text(
            json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        output = build_output(
            "CHECKPOINT_ESTABLISHED",
            "CHECKPOINT_ESTABLISHED",
            False,
            True,
            digest,
            [],
        )
        write_output(output)

        print("STATE: CHECKPOINT_ESTABLISHED")
        print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
        print("READY: False")
        print("VALID: True")
        print("CHECKPOINT: ESTABLISHED")
        print(f"SEMANTIC DIGEST: {digest}")
        print("ERROR COUNT: 0")
        return 0

    checkpoint, checkpoint_error = load_json(CHECKPOINT_FILE)

    if checkpoint_error:
        errors.append(f"checkpoint unavailable: {checkpoint_error}")
    else:
        errors.extend(validate_checkpoint(checkpoint))

    if errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            digest,
            errors,
        )
        write_output(output)

        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: INVALID")
        print(f"ERROR COUNT: {len(errors)}")
        return 1

    if checkpoint.get("semanticDigest") != digest:
        errors.append("semantic digest drift detected")

    stored_projection = checkpoint.get("semanticProjection")

    if stored_projection != semantic_projection(phase38):
        errors.append("semantic projection drift detected")

    if errors:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            digest,
            errors,
        )
        write_output(output)

        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: DRIFT")
        print(f"SEMANTIC DIGEST: {digest}")
        print(f"ERROR COUNT: {len(errors)}")
        return 1

    output = build_output(
        "VERIFIED_READ_ONLY",
        "VERIFIED_READ_ONLY",
        True,
        True,
        digest,
        [],
    )
    write_output(output)

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print(f"SEMANTIC DIGEST: {digest}")
    print("ERROR COUNT: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
