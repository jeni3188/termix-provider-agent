#!/usr/bin/env python3

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OBSERVER_DIR = BASE_DIR / "provider-output" / "aacp-observer"

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY_CONTINUITY_VERIFY"

PHASE41_FILE = (
    OBSERVER_DIR
    / "latest-aacp-evidence-chain-health-snapshot-registry-verify.json"
)

CHECKPOINT_FILE = (
    OBSERVER_DIR
    / "aacp-evidence-chain-health-snapshot-registry-continuity-checkpoint.json"
)

OUTPUT_FILE = (
    OBSERVER_DIR
    / "latest-aacp-evidence-chain-health-snapshot-registry-continuity-verify.json"
)


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def relative_path(path):
    return str(path.relative_to(BASE_DIR))


def safety_ok(data):
    safety = data.get("safety")

    if not isinstance(safety, dict):
        return False

    required = {
        "postPerformed": False,
        "walletUsed": False,
        "signingPerformed": False,
        "broadcastPerformed": False,
        "submissionPerformed": False,
    }

    return all(safety.get(k) is v for k, v in required.items())


def phase41_valid(data):
    if not isinstance(data, dict):
        return False

    if data.get("type") != (
        "AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY_VERIFY"
    ):
        return False

    if data.get("version") != 1:
        return False

    if data.get("mode") != "READ_ONLY":
        return False

    if data.get("state") != "VERIFIED_READ_ONLY":
        return False

    if data.get("sourceState") != "VERIFIED_READ_ONLY":
        return False

    if data.get("executionAuthorized") is not False:
        return False

    if not safety_ok(data):
        return False

    if data.get("errorCount") != 0:
        return False

    if data.get("errors") != []:
        return False

    verification = data.get("verification")

    if not isinstance(verification, dict):
        return False

    if verification.get("valid") is not True:
        return False

    if verification.get("requiredLayers") != 9:
        return False

    if verification.get("verifiedLayers") != 9:
        return False

    digest = verification.get("registryDigest")

    if not isinstance(digest, str) or len(digest) != 64:
        return False

    return True


def semantic_projection(data):
    return {
        "version": data.get("version"),
        "type": data.get("type"),
        "mode": data.get("mode"),
        "state": data.get("state"),
        "sourceState": data.get("sourceState"),
        "executionAuthorized": data.get("executionAuthorized"),
        "safety": data.get("safety"),
        "sideEffects": data.get("sideEffects"),
        "verification": data.get("verification"),
        "sources": data.get("sources"),
        "errors": data.get("errors"),
        "errorCount": data.get("errorCount"),
        "policy": data.get("policy"),
    }


def semantic_digest(data):
    projection = semantic_projection(data)
    return sha256_bytes(
        canonical_json(projection).encode("utf-8")
    )


def checkpoint_valid(checkpoint):
    if not isinstance(checkpoint, dict):
        return False

    if checkpoint.get("version") != 1:
        return False

    if checkpoint.get("type") != TYPE:
        return False

    digest = checkpoint.get("semanticDigest")

    if not isinstance(digest, str) or len(digest) != 64:
        return False

    projection = checkpoint.get("semanticProjection")

    if not isinstance(projection, dict):
        return False

    expected = sha256_bytes(
        canonical_json(projection).encode("utf-8")
    )

    return digest == expected


def verify_continuity():
    errors = []

    phase41 = load_json(PHASE41_FILE)

    if not isinstance(phase41, dict):
        return None, errors + ["phase41 artifact is invalid JSON"]

    if not phase41_valid(phase41):
        errors.append("phase41 artifact validation failed")
        return None, errors

    current_projection = semantic_projection(phase41)
    current_digest = semantic_digest(phase41)

    if not CHECKPOINT_FILE.exists():
        return {
            "state": "CHECKPOINT_ESTABLISHED",
            "ready": False,
            "valid": True,
            "verifiedLayers": 0,
            "requiredLayers": 9,
            "semanticDigest": current_digest,
            "checkpoint": "ESTABLISHED",
        }, errors

    checkpoint = load_json(CHECKPOINT_FILE)

    if not checkpoint_valid(checkpoint):
        errors.append("continuity checkpoint is invalid")
        return None, errors

    if checkpoint.get("semanticDigest") != current_digest:
        errors.append("semantic digest drift detected")

    if checkpoint.get("semanticProjection") != current_projection:
        errors.append("semantic projection drift detected")

    if errors:
        return {
            "state": "BLOCKED",
            "ready": False,
            "valid": False,
            "verifiedLayers": 0,
            "requiredLayers": 9,
            "semanticDigest": current_digest,
            "checkpoint": "DRIFT_DETECTED",
        }, errors

    return {
        "state": "VERIFIED_READ_ONLY",
        "ready": True,
        "valid": True,
        "verifiedLayers": 9,
        "requiredLayers": 9,
        "semanticDigest": current_digest,
        "checkpoint": "VERIFIED",
    }, errors


def build_output():
    result, errors = verify_continuity()

    if result is None:
        state = "BLOCKED"
        source_state = "BLOCKED"
        valid = False
        ready = False
        verified_layers = 0
        checkpoint = "INVALID"
        digest = None
    else:
        state = result["state"]
        source_state = result["state"]
        valid = result["valid"]
        ready = result["ready"]
        verified_layers = result["verifiedLayers"]
        checkpoint = result["checkpoint"]
        digest = result["semanticDigest"]

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
                "CONTINUITY_VERIFIED"
                if ready
                else (
                    "CHECKPOINT_ESTABLISHED"
                    if checkpoint == "ESTABLISHED"
                    else "CONTINUITY_BLOCKED"
                )
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 9,
            "verifiedLayers": verified_layers,
            "checkpoint": checkpoint,
            "semanticDigest": digest,
        },
        "sources": {
            "phase41": relative_path(PHASE41_FILE),
            "checkpoint": relative_path(CHECKPOINT_FILE),
        } if valid else {},
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
    OBSERVER_DIR.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_checkpoint(phase41):
    checkpoint = {
        "version": 1,
        "type": TYPE,
        "createdAt": now(),
        "semanticDigest": semantic_digest(phase41),
        "semanticProjection": semantic_projection(phase41),
    }

    CHECKPOINT_FILE.write_text(
        json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    output = build_output()

    if (
        output["verification"]["checkpoint"] == "ESTABLISHED"
        and output["verification"]["valid"] is True
    ):
        phase41 = load_json(PHASE41_FILE)

        if isinstance(phase41, dict) and phase41_valid(phase41):
            write_checkpoint(phase41)

    write_output(output)

    print(f"STATE: {output['state']}")
    print(f"SOURCE STATE: {output['sourceState']}")
    print(f"READY: {output['readiness']['ready']}")
    print(f"VALID: {output['verification']['valid']}")
    print(f"CHECKPOINT: {output['verification']['checkpoint']}")
    print(
        "VERIFIED LAYERS: "
        f"{output['verification']['verifiedLayers']}/"
        f"{output['verification']['requiredLayers']}"
    )
    print(
        "SEMANTIC DIGEST: "
        f"{output['verification']['semanticDigest'] or 'NONE'}"
    )
    print(f"ERROR COUNT: {output['errorCount']}")

    return 0 if output["verification"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
