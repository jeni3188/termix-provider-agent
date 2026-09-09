#!/usr/bin/env python3

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE = Path("provider-output/aacp-observer")

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_ARTIFACT_IDENTITY_VERIFY"
VERSION = 1
MODE = "READ_ONLY"

CHECKPOINT = BASE / "aacp-evidence-chain-health-artifact-identity-checkpoint.json"
OUTPUT = BASE / "latest-aacp-evidence-chain-health-artifact-identity-verify.json"

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
}

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


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    if not isinstance(value, str) or not value:
        raise ValueError("generatedAt must be a non-empty string")

    text = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)

    if dt.tzinfo is None:
        raise ValueError("generatedAt must include timezone")

    return dt.astimezone(timezone.utc)


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
        raise ValueError(f"phase{phase} errorCount violation")

    if root.get("errors") != []:
        raise ValueError(f"phase{phase} errors violation")


def load_phase(phase):
    filename, expected_type = PHASES[phase]
    path = BASE / filename

    if not path.exists():
        raise ValueError(f"phase{phase} artifact missing")

    try:
        root = json.loads(path.read_text())
    except Exception as exc:
        raise ValueError(
            f"phase{phase} JSON invalid: {exc}"
        )

    if not isinstance(root, dict):
        raise ValueError(f"phase{phase} root must be object")

    if root.get("type") != expected_type:
        raise ValueError(
            f"phase{phase} type mismatch: "
            f"{root.get('type')!r} != {expected_type!r}"
        )

    if root.get("mode") != MODE:
        raise ValueError(f"phase{phase} mode violation")

    validate_safety(root, phase)

    generated = root.get("generatedAt")
    parse_time(generated)

    return {
        "phase": phase,
        "type": root["type"],
        "path": str(path),
        "generatedAt": generated,
        "sha256": file_digest(path),
    }


def validate_phase43(root):
    if root.get("state") != "VERIFIED_READ_ONLY":
        raise ValueError(
            "phase43 state is not VERIFIED_READ_ONLY"
        )

    if root.get("sourceState") != "VERIFIED_READ_ONLY":
        raise ValueError(
            "phase43 sourceState is not VERIFIED_READ_ONLY"
        )

    readiness = root.get("readiness")

    if (
        not isinstance(readiness, dict)
        or readiness.get("ready") is not True
    ):
        raise ValueError("phase43 readiness violation")

    verification = root.get("verification")

    if not isinstance(verification, dict):
        raise ValueError("phase43 verification missing")

    if verification.get("valid") is not True:
        raise ValueError("phase43 verification invalid")

    if verification.get("requiredLayers") != 12:
        raise ValueError("phase43 requiredLayers mismatch")

    if verification.get("verifiedLayers") != 12:
        raise ValueError("phase43 verifiedLayers mismatch")

    if verification.get("checkpoint") != "VERIFIED":
        raise ValueError("phase43 checkpoint is not VERIFIED")

    semantic = verification.get("semanticDigest")

    if not isinstance(semantic, str) or not HEX64.fullmatch(semantic):
        raise ValueError("phase43 semanticDigest invalid")


def identity_projection(records):
    return {
        "version": VERSION,
        "type": TYPE,
        "mode": MODE,
        "artifacts": [
            {
                "phase": record["phase"],
                "type": record["type"],
                "path": record["path"],
                "generatedAt": record["generatedAt"],
                "sha256": record["sha256"],
            }
            for record in records
        ],
    }


def build_output():
    try:
        records = [
            load_phase(phase)
            for phase in PHASES
        ]

        phase43_path = BASE / PHASES[43][0]
        validate_phase43(json.loads(
            phase43_path.read_text()
        ))

        projection = identity_projection(records)
        identity_digest = digest(projection)

        if CHECKPOINT.exists():
            try:
                checkpoint = json.loads(
                    CHECKPOINT.read_text()
                )
            except Exception as exc:
                raise ValueError(
                    f"checkpoint invalid: {exc}"
                )

            if checkpoint.get("type") != TYPE:
                raise ValueError(
                    "checkpoint type mismatch"
                )

            if checkpoint.get("version") != VERSION:
                raise ValueError(
                    "checkpoint version mismatch"
                )

            if checkpoint.get("identityDigest") != identity_digest:
                raise ValueError(
                    "artifact identity digest drift"
                )

            if checkpoint.get("identityProjection") != projection:
                raise ValueError(
                    "artifact identity projection drift"
                )

            state = "VERIFIED_READ_ONLY"
            ready = True
            checkpoint_state = "VERIFIED"
            verified = 13

        else:
            state = "CHECKPOINT_ESTABLISHED"
            ready = False
            checkpoint_state = "ESTABLISHED"
            verified = 0

        return {
            "version": VERSION,
            "type": TYPE,
            "generatedAt": now(),
            "mode": MODE,
            "state": state,
            "sourceState": state,
            "executionAuthorized": False,
            "safety": safety(),
            "sideEffects": side_effects(),
            "readiness": {
                "ready": ready,
                "reason": (
                    "ALL_REQUIRED_ARTIFACT_IDENTITIES_VERIFIED"
                    if ready
                    else "ARTIFACT_IDENTITY_CHECKPOINT_ESTABLISHED"
                ),
            },
            "verification": {
                "valid": True,
                "requiredLayers": 13,
                "verifiedLayers": verified,
                "checkpoint": checkpoint_state,
                "identityDigest": identity_digest,
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
                "reason": "ARTIFACT_IDENTITY_VALIDATION_FAILED",
            },
            "verification": {
                "valid": False,
                "requiredLayers": 13,
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
        and result["verification"].get("identityDigest")
    ):
        records = [
            load_phase(phase)
            for phase in PHASES
        ]

        projection = identity_projection(records)

        checkpoint = {
            "version": VERSION,
            "type": TYPE,
            "createdAt": now(),
            "identityDigest": result["verification"][
                "identityDigest"
            ],
            "identityProjection": projection,
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
        f"CHECKPOINT: "
        f"{result['verification']['checkpoint']}"
    )
    print(
        "VERIFIED LAYERS: "
        f"{result['verification']['verifiedLayers']}/"
        f"{result['verification']['requiredLayers']}"
    )

    if "identityDigest" in result["verification"]:
        print(
            "IDENTITY DIGEST: "
            f"{result['verification']['identityDigest']}"
        )

    print(f"ERROR COUNT: {result['errorCount']}")

    return (
        0
        if result["verification"]["valid"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
