#!/usr/bin/env python3

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OBSERVER_DIR = BASE_DIR / "provider-output" / "aacp-observer"

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY_VERIFY"

REGISTRY_FILE = (
    OBSERVER_DIR
    / "latest-aacp-evidence-chain-health-snapshot-registry.json"
)

OUTPUT_FILE = (
    OBSERVER_DIR
    / "latest-aacp-evidence-chain-health-snapshot-registry-verify.json"
)

PHASE_FILES = {
    31: "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
    32: "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
    33: "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
    34: "latest-aacp-evidence-chain-health-integrity-attestation.json",
    35: "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
    36: "latest-aacp-evidence-chain-health-final-readiness.json",
    37: "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json",
    38: "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json",
    39: "latest-aacp-evidence-chain-health-semantic-checkpoint-verify.json",
}

EXPECTED_TYPES = {
    31: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
    32: "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
    33: "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
    34: "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION",
    35: "AACP_EVIDENCE_CHAIN_HEALTH_ATTESTATION_CONSISTENCY_VERIFY",
    36: "AACP_EVIDENCE_CHAIN_HEALTH_FINAL_READINESS",
    37: "AACP_EVIDENCE_CHAIN_HEALTH_POST_READINESS_DRIFT_VERIFY",
    38: "AACP_EVIDENCE_CHAIN_HEALTH_CONTINUOUS_READINESS_REPEATABILITY_VERIFY",
    39: "AACP_EVIDENCE_CHAIN_HEALTH_SEMANTIC_CHECKPOINT_VERIFY",
}


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


def sha256_file(path):
    return sha256_bytes(path.read_bytes())


def relative_path(path):
    return str(path.relative_to(BASE_DIR))


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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


def phase_valid(phase, data):
    if not isinstance(data, dict):
        return False

    if data.get("type") != EXPECTED_TYPES[phase]:
        return False

    if data.get("executionAuthorized") is not False:
        return False

    if not safety_ok(data):
        return False

    if data.get("errorCount") != 0:
        return False

    if data.get("errors") != []:
        return False

    if phase == 31:
        return data.get("state") == "INCOMPLETE"

    if phase == 32:
        verification = data.get("verification")
        return (
            data.get("state") == "INCOMPLETE"
            and isinstance(verification, dict)
            and verification.get("valid") is True
        )

    if phase in (33, 34, 35):
        verification = data.get("verification")
        return (
            data.get("state") == "VERIFIED_READ_ONLY"
            and data.get("sourceState") == "VERIFIED_READ_ONLY"
            and isinstance(verification, dict)
            and verification.get("valid") is True
        )

    if phase in (36, 37, 38, 39):
        verification = data.get("verification")
        readiness = data.get("readiness")

        return (
            data.get("state") == "VERIFIED_READ_ONLY"
            and data.get("sourceState") == "VERIFIED_READ_ONLY"
            and isinstance(readiness, dict)
            and readiness.get("ready") is True
            and isinstance(verification, dict)
            and verification.get("valid") is True
        )

    return False


def verify_registry():
    errors = []

    envelope = load_json(REGISTRY_FILE)

    if not isinstance(envelope, dict):
        return None, errors + ["registry artifact is invalid JSON"]

    if envelope.get("type") != "AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY":
        errors.append("registry envelope type mismatch")

    if envelope.get("executionAuthorized") is not False:
        errors.append("registry execution authorization violation")

    if not safety_ok(envelope):
        errors.append("registry safety violation")

    if envelope.get("errorCount") != 0:
        errors.append("registry error count violation")

    if envelope.get("errors") != []:
        errors.append("registry errors are not empty")

    registry = envelope.get("registry")

    if not isinstance(registry, dict):
        errors.append("registry payload is invalid")
        return None, errors

    if registry.get("type") != "AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY":
        errors.append("registry type mismatch")

    if registry.get("version") != 1:
        errors.append("registry version mismatch")

    if registry.get("mode") != "READ_ONLY":
        errors.append("registry mode violation")

    layers = registry.get("layers")

    if not isinstance(layers, dict):
        errors.append("registry layers are invalid")
        return None, errors

    if registry.get("layerCount") != len(PHASE_FILES):
        errors.append("registry layerCount mismatch")

    if len(layers) != len(PHASE_FILES):
        errors.append("registry layer set size mismatch")

    expected_core = {
        "version": registry.get("version"),
        "type": registry.get("type"),
        "mode": registry.get("mode"),
        "layers": layers,
        "layerCount": registry.get("layerCount"),
    }

    expected_digest = sha256_bytes(
        canonical_json(expected_core).encode("utf-8")
    )

    if registry.get("registryDigest") != expected_digest:
        errors.append("registry digest mismatch")

    verified = 0

    for phase, filename in PHASE_FILES.items():
        key = f"phase{phase}"
        entry = layers.get(key)

        if not isinstance(entry, dict):
            errors.append(f"{key} registry entry missing")
            continue

        path = OBSERVER_DIR / filename

        if not path.exists():
            errors.append(f"{key} artifact is missing")
            continue

        data = load_json(path)

        if not phase_valid(phase, data):
            errors.append(f"{key} artifact validation failed")
            continue

        expected_path = relative_path(path)
        expected_type = EXPECTED_TYPES[phase]
        expected_sha = sha256_file(path)

        if entry.get("path") != expected_path:
            errors.append(f"{key} path mismatch")

        if entry.get("type") != expected_type:
            errors.append(f"{key} type mismatch")

        if entry.get("state") != data.get("state"):
            errors.append(f"{key} state mismatch")

        if entry.get("sourceState") != data.get("sourceState"):
            errors.append(f"{key} sourceState mismatch")

        if entry.get("executionAuthorized") is not False:
            errors.append(f"{key} execution authorization violation")

        if entry.get("sha256") != expected_sha:
            errors.append(f"{key} sha256 mismatch")

        if (
            entry.get("path") == expected_path
            and entry.get("type") == expected_type
            and entry.get("state") == data.get("state")
            and entry.get("sourceState") == data.get("sourceState")
            and entry.get("executionAuthorized") is False
            and entry.get("sha256") == expected_sha
        ):
            verified += 1

    return {
        "registryDigest": registry.get("registryDigest"),
        "verifiedLayers": verified,
        "requiredLayers": len(PHASE_FILES),
    }, errors


def build_output():
    result, errors = verify_registry()

    valid = not errors
    state = "VERIFIED_READ_ONLY" if valid else "BLOCKED"

    return {
        "version": 1,
        "type": TYPE,
        "generatedAt": now(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": state,
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
        "verification": {
            "valid": valid,
            "requiredLayers": (
                result["requiredLayers"] if result else len(PHASE_FILES)
            ),
            "verifiedLayers": result["verifiedLayers"] if result else 0,
            "registryDigest": (
                result["registryDigest"] if result else None
            ),
        },
        "sources": {
            "registry": relative_path(REGISTRY_FILE),
            **{
                f"phase{phase}": relative_path(
                    OBSERVER_DIR / filename
                )
                for phase, filename in PHASE_FILES.items()
            },
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


def main():
    output = build_output()
    write_output(output)

    print(f"STATE: {output['state']}")
    print(f"SOURCE STATE: {output['sourceState']}")
    print(f"VALID: {output['verification']['valid']}")
    print(
        "VERIFIED LAYERS: "
        f"{output['verification']['verifiedLayers']}/"
        f"{output['verification']['requiredLayers']}"
    )
    print(
        "REGISTRY DIGEST: "
        f"{output['verification']['registryDigest'] or 'NONE'}"
    )
    print(f"ERROR COUNT: {output['errorCount']}")

    return 0 if output["verification"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
