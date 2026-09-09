#!/usr/bin/env python3

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OBSERVER_DIR = BASE_DIR / "provider-output" / "aacp-observer"

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY"
OUTPUT_FILE = (
    OBSERVER_DIR
    / "latest-aacp-evidence-chain-health-snapshot-registry.json"
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


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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
        return (
            data.get("state") == "INCOMPLETE"
            and data.get("verification", {}).get("valid") is True
        )

    if phase in (33, 34, 35):
        return (
            data.get("state") == "VERIFIED_READ_ONLY"
            and data.get("sourceState") == "VERIFIED_READ_ONLY"
            and data.get("verification", {}).get("valid") is True
        )

    if phase in (36, 37, 38, 39):
        return (
            data.get("state") == "VERIFIED_READ_ONLY"
            and data.get("sourceState") == "VERIFIED_READ_ONLY"
            and data.get("readiness", {}).get("ready") is True
            and data.get("verification", {}).get("valid") is True
        )

    return False


def build_registry():
    errors = []
    layers = {}

    for phase, filename in PHASE_FILES.items():
        path = OBSERVER_DIR / filename

        if not path.exists():
            errors.append(f"phase{phase} artifact is missing")
            continue

        data = load_json(path)

        if data is None:
            errors.append(f"phase{phase} artifact is invalid JSON")
            continue

        if not phase_valid(phase, data):
            errors.append(f"phase{phase} validation failed")
            continue

        layers[f"phase{phase}"] = {
            "type": data["type"],
            "path": relative_path(path),
            "state": data.get("state"),
            "sourceState": data.get("sourceState"),
            "executionAuthorized": data.get("executionAuthorized"),
            "sha256": sha256_file(path),
        }

    if errors:
        return None, errors

    registry_core = {
        "version": 1,
        "type": TYPE,
        "mode": "READ_ONLY",
        "layers": layers,
        "layerCount": len(layers),
    }

    registry_digest = sha256_bytes(
        canonical_json(registry_core).encode("utf-8")
    )

    return {
        **registry_core,
        "registryDigest": registry_digest,
    }, []


def build_output():
    registry, errors = build_registry()

    valid = not errors
    state = "VERIFIED_READ_ONLY" if valid else "BLOCKED"
    source_state = state

    output = {
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
        "registry": registry if registry is not None else {},
        "verification": {
            "valid": valid,
            "requiredLayers": len(PHASE_FILES),
            "verifiedLayers": len(registry["layers"]) if registry else 0,
        },
        "sources": {
            f"phase{phase}": relative_path(
                OBSERVER_DIR / filename
            )
            for phase, filename in PHASE_FILES.items()
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

    return output


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
        f"{output.get('registry', {}).get('registryDigest', 'NONE')}"
    )
    print(f"ERROR COUNT: {output['errorCount']}")

    return 0 if output["verification"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
