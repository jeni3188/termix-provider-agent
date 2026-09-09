#!/usr/bin/env python3

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE = Path("provider-output/aacp-observer")

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_IDENTITY_ATTESTATION"
VERSION = 1
MODE = "READ_ONLY"

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-cross-artifact-identity-attestation-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-cross-artifact-identity-attestation.json"
)

PHASE44_FILE = (
    "latest-aacp-evidence-chain-health-artifact-identity-verify.json"
)

PHASES = {
    31: (
        "latest-aacp-evidence-chain-health-audit-history-audit-history.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
    ),
    32: (
        "latest-aacp-evidence-chain-health-audit-history-audit-history-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
    ),
    33: (
        "latest-aacp-evidence-chain-health-cross-layer-integrity-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
    ),
    34: (
        "latest-aacp-evidence-chain-health-integrity-attestation.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION",
    ),
    35: (
        "latest-aacp-evidence-chain-health-attestation-consistency-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_ATTESTATION_CONSISTENCY_VERIFY",
    ),
    36: (
        "latest-aacp-evidence-chain-health-final-readiness.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_FINAL_READINESS",
    ),
    37: (
        "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_POST_READINESS_DRIFT_VERIFY",
    ),
    38: (
        "latest-aacp-evidence-chain-health-continuous-readiness-repeatability-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_CONTINUOUS_READINESS_REPEATABILITY_VERIFY",
    ),
    39: (
        "latest-aacp-evidence-chain-health-semantic-checkpoint-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_SEMANTIC_CHECKPOINT_VERIFY",
    ),
    40: (
        "latest-aacp-evidence-chain-health-snapshot-registry.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY",
    ),
    41: (
        "latest-aacp-evidence-chain-health-snapshot-registry-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY_VERIFY",
    ),
    42: (
        "latest-aacp-evidence-chain-health-snapshot-registry-continuity-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_SNAPSHOT_REGISTRY_CONTINUITY_VERIFY",
    ),
    43: (
        "latest-aacp-evidence-chain-health-temporal-continuity-verify.json",
        "AACP_EVIDENCE_CHAIN_HEALTH_TEMPORAL_CONTINUITY_VERIFY",
    ),
    44: (
        PHASE44_FILE,
        "AACP_EVIDENCE_CHAIN_HEALTH_ARTIFACT_IDENTITY_VERIFY",
    ),
}

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_file(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def digest(value):
    return sha256_text(canonical(value))


def now():
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(value):
    if not isinstance(value, str) or not value:
        raise ValueError("generatedAt must be a non-empty string")

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        raise ValueError("generatedAt must include timezone")

    return parsed.astimezone(timezone.utc)


def safety():
    return {
        "postPerformed": False,
        "walletUsed": False,
        "signingPerformed": False,
        "broadcastPerformed": False,
        "submissionPerformed": False,
    }


def side_effects():
    return {
        "network": False,
        "filesystemWrite": True,
        "wallet": False,
        "signing": False,
        "broadcast": False,
        "submission": False,
    }


def policy():
    return {
        "readOnly": True,
        "failClosed": True,
        "executionAuthorized": False,
        "networkAccess": False,
        "walletAccess": False,
        "signingAllowed": False,
        "broadcastAllowed": False,
        "submissionAllowed": False,
    }


def validate_safety(root, phase):
    if root.get("executionAuthorized") is not False:
        raise ValueError(
            f"phase{phase} execution authorization violation"
        )

    safety_obj = root.get("safety")

    if not isinstance(safety_obj, dict):
        raise ValueError(f"phase{phase} safety missing")

    for key in (
        "postPerformed",
        "walletUsed",
        "signingPerformed",
        "broadcastPerformed",
        "submissionPerformed",
    ):
        if safety_obj.get(key) is not False:
            raise ValueError(
                f"phase{phase} safety violation: {key}"
            )

    if root.get("errorCount") != 0:
        raise ValueError(
            f"phase{phase} errorCount violation"
        )

    if root.get("errors") != []:
        raise ValueError(
            f"phase{phase} errors violation"
        )


def load_json(path, label):
    if not path.exists():
        raise ValueError(f"{label} artifact missing")

    try:
        value = json.loads(path.read_text())
    except Exception as exc:
        raise ValueError(
            f"{label} JSON invalid: {exc}"
        )

    if not isinstance(value, dict):
        raise ValueError(
            f"{label} root must be object"
        )

    return value


def load_phase(phase):
    filename, expected_type = PHASES[phase]
    path = BASE / filename

    root = load_json(path, f"phase{phase}")

    if root.get("type") != expected_type:
        raise ValueError(
            f"phase{phase} type mismatch"
        )

    if root.get("mode") != MODE:
        raise ValueError(
            f"phase{phase} mode violation"
        )

    validate_safety(root, phase)

    generated = root.get("generatedAt")
    parse_timestamp(generated)

    return {
        "phase": phase,
        "type": root["type"],
        "path": str(path),
        "generatedAt": generated,
        "sha256": sha256_file(path),
    }


def validate_phase44(root):
    if root.get("type") != PHASES[44][1]:
        raise ValueError("phase44 type mismatch")

    if root.get("state") != "VERIFIED_READ_ONLY":
        raise ValueError(
            "phase44 state is not VERIFIED_READ_ONLY"
        )

    if root.get("sourceState") != "VERIFIED_READ_ONLY":
        raise ValueError(
            "phase44 sourceState is not VERIFIED_READ_ONLY"
        )

    if root.get("executionAuthorized") is not False:
        raise ValueError(
            "phase44 execution authorization violation"
        )

    readiness = root.get("readiness")

    if (
        not isinstance(readiness, dict)
        or readiness.get("ready") is not True
    ):
        raise ValueError(
            "phase44 readiness violation"
        )

    verification = root.get("verification")

    if not isinstance(verification, dict):
        raise ValueError(
            "phase44 verification missing"
        )

    if verification.get("valid") is not True:
        raise ValueError(
            "phase44 verification invalid"
        )

    if verification.get("requiredLayers") != 13:
        raise ValueError(
            "phase44 requiredLayers mismatch"
        )

    if verification.get("verifiedLayers") != 13:
        raise ValueError(
            "phase44 verifiedLayers mismatch"
        )

    if verification.get("checkpoint") != "VERIFIED":
        raise ValueError(
            "phase44 checkpoint is not VERIFIED"
        )

    identity = verification.get("identityDigest")

    if not isinstance(identity, str):
        raise ValueError(
            "phase44 identityDigest missing"
        )

    if not HEX64.fullmatch(identity):
        raise ValueError(
            "phase44 identityDigest invalid"
        )

    validate_safety(root, 44)


def build_attestation():
    records = [
        load_phase(phase)
        for phase in PHASES
    ]

    phase44 = load_json(
        BASE / PHASE44_FILE,
        "phase44",
    )

    validate_phase44(phase44)

    projection = {
        "version": VERSION,
        "type": TYPE,
        "mode": MODE,
        "artifacts": records,
    }

    attestation_digest = digest(projection)

    return projection, attestation_digest


def build_output():
    try:
        projection, attestation_digest = build_attestation()

        if CHECKPOINT.exists():
            checkpoint = load_json(
                CHECKPOINT,
                "checkpoint",
            )

            if checkpoint.get("type") != TYPE:
                raise ValueError(
                    "checkpoint type mismatch"
                )

            if checkpoint.get("version") != VERSION:
                raise ValueError(
                    "checkpoint version mismatch"
                )

            if checkpoint.get("attestationDigest") != attestation_digest:
                raise ValueError(
                    "cross-artifact attestation digest drift"
                )

            if checkpoint.get("attestationProjection") != projection:
                raise ValueError(
                    "cross-artifact attestation projection drift"
                )

            state = "VERIFIED_READ_ONLY"
            source_state = "VERIFIED_READ_ONLY"
            ready = True
            checkpoint_state = "VERIFIED"
            verified = 14

        else:
            state = "CHECKPOINT_ESTABLISHED"
            source_state = "CHECKPOINT_ESTABLISHED"
            ready = False
            checkpoint_state = "ESTABLISHED"
            verified = 0

        return {
            "version": VERSION,
            "type": TYPE,
            "generatedAt": now(),
            "mode": MODE,
            "state": state,
            "sourceState": source_state,
            "executionAuthorized": False,
            "safety": safety(),
            "sideEffects": side_effects(),
            "readiness": {
                "ready": ready,
                "reason": (
                    "ALL_REQUIRED_CROSS_ARTIFACT_IDENTITIES_ATTESTED"
                    if ready
                    else "CROSS_ARTIFACT_ATTESTATION_CHECKPOINT_ESTABLISHED"
                ),
            },
            "verification": {
                "valid": True,
                "requiredLayers": 14,
                "verifiedLayers": verified,
                "checkpoint": checkpoint_state,
                "attestationDigest": attestation_digest,
                "artifacts": projection["artifacts"],
            },
            "sources": projection["artifacts"],
            "errors": [],
            "errorCount": 0,
            "policy": policy(),
        }

    except Exception as exc:
        return {
            "version": VERSION,
            "type": TYPE,
            "generatedAt": now(),
            "mode": MODE,
            "state": "BLOCKED",
            "sourceState": "BLOCKED",
            "executionAuthorized": False,
            "safety": safety(),
            "sideEffects": side_effects(),
            "readiness": {
                "ready": False,
                "reason": "CROSS_ARTIFACT_ATTESTATION_VALIDATION_FAILED",
            },
            "verification": {
                "valid": False,
                "requiredLayers": 14,
                "verifiedLayers": 0,
                "checkpoint": "NOT_VERIFIED",
            },
            "sources": [],
            "errors": [str(exc)],
            "errorCount": 1,
            "policy": policy(),
        }


def main():
    BASE.mkdir(parents=True, exist_ok=True)

    result = build_output()

    if (
        result["state"] == "CHECKPOINT_ESTABLISHED"
        and result["verification"].get("attestationDigest")
    ):
        projection, attestation_digest = build_attestation()

        checkpoint = {
            "version": VERSION,
            "type": TYPE,
            "createdAt": now(),
            "attestationDigest": attestation_digest,
            "attestationProjection": projection,
        }

        CHECKPOINT.write_text(
            json.dumps(
                checkpoint,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )

    OUTPUT.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    print(f"STATE: {result['state']}")
    print(f"SOURCE STATE: {result['sourceState']}")
    print(
        f"READY: {result['readiness']['ready']}"
    )
    print(
        f"VALID: {result['verification']['valid']}"
    )
    print(
        f"CHECKPOINT: {result['verification']['checkpoint']}"
    )
    print(
        "VERIFIED LAYERS: "
        f"{result['verification']['verifiedLayers']}/"
        f"{result['verification']['requiredLayers']}"
    )

    if "attestationDigest" in result["verification"]:
        print(
            "ATTESTATION DIGEST: "
            f"{result['verification']['attestationDigest']}"
        )

    print(
        f"ERROR COUNT: {result['errorCount']}"
    )

    return (
        0
        if result["verification"]["valid"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
