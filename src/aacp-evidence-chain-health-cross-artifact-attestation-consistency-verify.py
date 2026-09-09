#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "provider-output" / "aacp-observer"

PHASES = list(range(31, 45))

ARTIFACTS = {
    31: ("AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
         "latest-aacp-evidence-chain-health-audit-history-audit-history.json"),
    32: ("AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
         "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json"),
    33: ("AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
         "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json"),
    34: ("AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION",
         "latest-aacp-evidence-chain-health-integrity-attestation.json"),
    35: ("AACP_EVIDENCE_CHAIN_HEALTH_ATTESTATION_CONSISTENCY_VERIFY",
         "latest-aacp-evidence-chain-health-attestation-consistency-verify.json"),
    36: ("AACP_EVIDENCE_CHAIN_HEALTH_FINAL_READINESS",
         "latest-aacp-evidence-chain-health-final-readiness.json"),
    37: ("AACP_EVIDENCE_CHAIN_HEALTH_POST_READINESS_DRIFT_VERIFY",
         "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json"),
    38: ("AACP_EVIDENCE_CHAIN_HEALTH_CONTINUOUS_READINESS_REPEATABILITY_VERIFY",
         "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json"),
    39: ("AACP_EVIDENCE_CHAIN_HEALTH_SEMANTIC_CHECKPOINT_VERIFY",
         "latest-aacp-evidence-chain-health-semantic-checkpoint-verify.json"),
    40: ("AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY",
         "latest-aacp-evidence-chain-health-snapshot-registry.json"),
    41: ("AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY_VERIFY",
         "latest-aacp-evidence-chain-health-snapshot-registry-verify.json"),
    42: ("AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY_CONTINUITY_VERIFY",
         "latest-aacp-evidence-chain-health-snapshot-registry-continuity-verify.json"),
    43: ("AACP_EVIDENCE_CHAIN_HEALTH_TEMPORAL_CONTINUITY_VERIFY",
         "latest-aacp-evidence-chain-health-temporal-continuity-verify.json"),
    44: ("AACP_EVIDENCE_CHAIN_HEALTH_ARTIFACT_IDENTITY_VERIFY",
         "latest-aacp-evidence-chain-health-artifact-identity-verify.json"),
}

PHASE45_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_IDENTITY_ATTESTATION"
PHASE46_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_CONSISTENCY_VERIFY"

PHASE45_PATH = OUT_DIR / "latest-aacp-evidence-chain-health-cross-artifact-identity-attestation.json"
CHECKPOINT = OUT_DIR / "aacp-evidence-chain-health-cross-artifact-identity-attestation-checkpoint.json"
OUTPUT = OUT_DIR / "latest-aacp-evidence-chain-health-cross-artifact-attestation-consistency-verify.json"

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def valid_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.tzinfo is not None
    except Exception:
        return False


def safety_ok(obj):
    if obj.get("mode") != "READ_ONLY":
        return False

    if obj.get("executionAuthorized") is not False:
        return False

    safety = obj.get("safety")
    if not isinstance(safety, dict):
        return False

    # Phase31-45 use slightly different safety schemas.
    # Fail closed only when a declared safety/execution flag is true.
    for key, value in safety.items():
        if isinstance(value, bool) and value is True:
            return False

    errors = obj.get("errors")
    if obj.get("errorCount") != 0:
        return False

    if errors != []:
        return False

    return True


def artifact_identity(phase, obj, path):
    return {
        "phase": phase,
        "type": obj.get("type"),
        "path": str(path.relative_to(ROOT)),
        "generatedAt": obj.get("generatedAt"),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build_projection(identities):
    return {
        "version": "1",
        "type": PHASE46_TYPE,
        "mode": "READ_ONLY",
        "artifacts": identities,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    errors = []
    identities = []

    for phase in PHASES:
        expected_type, filename = ARTIFACTS[phase]
        path = OUT_DIR / filename

        if not path.exists():
            errors.append(f"phase{phase}: missing artifact")
            continue

        try:
            obj = read_json(path)
        except Exception:
            errors.append(f"phase{phase}: corrupt JSON")
            continue

        if obj.get("type") != expected_type:
            errors.append(f"phase{phase}: type mismatch")

        if not safety_ok(obj):
            errors.append(f"phase{phase}: safety violation")

        if not valid_timestamp(obj.get("generatedAt")):
            errors.append(f"phase{phase}: invalid generatedAt")

        identities.append(artifact_identity(phase, obj, path))

    phase45 = None
    if not PHASE45_PATH.exists():
        errors.append("phase45: missing artifact")
    else:
        try:
            phase45 = read_json(PHASE45_PATH)
        except Exception:
            errors.append("phase45: corrupt JSON")

    if phase45 is not None:
        if phase45.get("type") != PHASE45_TYPE:
            errors.append("phase45: type mismatch")

        if not safety_ok(phase45):
            errors.append("phase45: safety violation")

        readiness = phase45.get("readiness", {})
        verification = phase45.get("verification", {})

        if phase45.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase45: state violation")
        if phase45.get("sourceState") != "VERIFIED_READ_ONLY":
            errors.append("phase45: sourceState violation")
        if readiness.get("ready") is not True:
            errors.append("phase45: readiness violation")
        if verification.get("valid") is not True:
            errors.append("phase45: validity violation")
        if verification.get("requiredLayers") != 14:
            errors.append("phase45: requiredLayers violation")
        if verification.get("verifiedLayers") != 14:
            errors.append("phase45: verifiedLayers violation")

        attestation = {
            "version": phase45.get("version"),
            "type": PHASE45_TYPE,
            "mode": phase45.get("mode"),
            "artifacts": verification.get("artifacts"),
        }

        expected_digest = digest(attestation)

        phase45_attestation_digest = verification.get("attestationDigest")

        if phase45_attestation_digest != expected_digest:
            errors.append("phase45: attestation digest mismatch")

        phase45_artifacts = verification.get("artifacts")
        if phase45_artifacts != identities:
            errors.append("phase45: artifact identity mismatch")

        if not HEX64.fullmatch(str(phase45_attestation_digest or "")):
            errors.append("phase45: malformed attestation digest")

    checkpoint = None
    if not CHECKPOINT.exists():
        errors.append("phase45 checkpoint: missing")
    else:
        try:
            checkpoint = read_json(CHECKPOINT)
        except Exception:
            errors.append("phase45 checkpoint: corrupt JSON")

    if checkpoint is not None and phase45 is not None:
        if checkpoint.get("type") != PHASE45_TYPE:
            errors.append("phase45 checkpoint: type mismatch")

        checkpoint_digest = checkpoint.get("attestationDigest")
        phase45_attestation_digest = phase45.get("verification", {}).get("attestationDigest")

        if checkpoint_digest != phase45_attestation_digest:
            errors.append("phase45 checkpoint: digest mismatch")

        checkpoint_projection = checkpoint.get("attestationProjection")
        expected_projection = {
            "version": phase45.get("version"),
            "type": PHASE45_TYPE,
            "mode": phase45.get("mode"),
            "artifacts": identities,
        }

        if checkpoint_projection != expected_projection:
            errors.append("phase45 checkpoint: projection mismatch")

    if errors:
        output = {
            "version": "1",
            "type": PHASE46_TYPE,
            "generatedAt": datetime.now().astimezone().isoformat(),
            "mode": "READ_ONLY",
            "state": "BLOCKED",
            "sourceState": "BLOCKED",
            "executionAuthorized": False,
            "safety": {
                "walletAccessed": False,
                "signingPerformed": False,
                "broadcastPerformed": False,
                "submissionPerformed": False,
                "privateKeyAccessed": False,
            },
            "sideEffects": {
                "filesystemWrite": True,
                "networkAccess": False,
                "walletAccess": False,
                "signing": False,
                "broadcast": False,
                "submission": False,
            },
            "readiness": {
                "ready": False,
                "reason": "CONSISTENCY_VALIDATION_FAILED",
            },
            "verification": {
                "valid": False,
                "requiredLayers": 14,
                "verifiedLayers": 0,
            },
            "sources": {
                "phase45": str(PHASE45_PATH.relative_to(ROOT)),
                "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
            },
            "errors": errors,
            "errorCount": len(errors),
            "policy": {
                "failClosed": True,
                "readOnly": True,
            },
        }
        OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        print("STATE: BLOCKED")
        print("SOURCE STATE: BLOCKED")
        print("READY: False")
        print("VALID: False")
        print("VERIFIED LAYERS: 0/14")
        print(f"ERROR COUNT: {len(errors)}")
        return 1

    projection = build_projection(identities)
    consistency_digest = digest(projection)

    output = {
        "version": "1",
        "type": PHASE46_TYPE,
        "generatedAt": datetime.now().astimezone().isoformat(),
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "executionAuthorized": False,
        "safety": {
            "walletAccessed": False,
            "signingPerformed": False,
            "broadcastPerformed": False,
            "submissionPerformed": False,
            "privateKeyAccessed": False,
        },
        "sideEffects": {
            "filesystemWrite": True,
            "networkAccess": False,
            "walletAccess": False,
            "signing": False,
            "broadcast": False,
            "submission": False,
        },
        "readiness": {
            "ready": True,
            "reason": "CROSS_ARTIFACT_ATTESTATION_CONSISTENT",
        },
        "verification": {
            "valid": True,
            "requiredLayers": 14,
            "verifiedLayers": 14,
            "checkpoint": "VERIFIED",
            "consistencyDigest": consistency_digest,
        },
        "sources": {
            "phase45": str(PHASE45_PATH.relative_to(ROOT)),
            "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
        },
        "errors": [],
        "errorCount": 0,
        "policy": {
            "failClosed": True,
            "readOnly": True,
        },
    }

    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("VERIFIED LAYERS: 14/14")
    print(f"CONSISTENCY DIGEST: {consistency_digest}")
    print("ERROR COUNT: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
