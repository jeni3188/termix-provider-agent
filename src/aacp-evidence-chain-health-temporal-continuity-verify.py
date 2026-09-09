#!/usr/bin/env python3

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


BASE = Path("provider-output/aacp-observer")

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_TEMPORAL_CONTINUITY_VERIFY"
VERSION = 1
MODE = "READ_ONLY"

CHECKPOINT = BASE / "aacp-evidence-chain-health-temporal-continuity-checkpoint.json"
OUTPUT = BASE / "latest-aacp-evidence-chain-health-temporal-continuity-verify.json"

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
}

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


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


def load_phase(phase):
    filename, expected_type = PHASES[phase]
    path = BASE / filename

    if not path.exists():
        raise ValueError(f"phase{phase} artifact missing")

    try:
        root = json.loads(path.read_text())
    except Exception as exc:
        raise ValueError(f"phase{phase} JSON invalid: {exc}")

    if not isinstance(root, dict):
        raise ValueError(f"phase{phase} root must be object")

    if root.get("type") != expected_type:
        raise ValueError(
            f"phase{phase} type mismatch: "
            f"{root.get('type')!r} != {expected_type!r}"
        )

    if root.get("mode") != "READ_ONLY":
        raise ValueError(f"phase{phase} mode violation")

    if root.get("executionAuthorized") is not False:
        raise ValueError(f"phase{phase} execution authorization violation")

    s = root.get("safety")
    if not isinstance(s, dict):
        raise ValueError(f"phase{phase} safety missing")

    for key in (
        "postPerformed",
        "walletUsed",
        "signingPerformed",
        "broadcastPerformed",
        "submissionPerformed",
    ):
        if s.get(key) is not False:
            raise ValueError(f"phase{phase} safety violation: {key}")

    if root.get("errorCount") != 0:
        raise ValueError(f"phase{phase} errorCount violation")

    if root.get("errors") != []:
        raise ValueError(f"phase{phase} errors violation")

    generated = root.get("generatedAt")
    dt = parse_time(generated)

    return {
        "phase": phase,
        "type": root["type"],
        "path": str(path),
        "generatedAt": generated,
        "timestamp": dt,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def validate_phase42(root):
    if root.get("state") != "VERIFIED_READ_ONLY":
        raise ValueError("phase42 state is not VERIFIED_READ_ONLY")

    if root.get("sourceState") != "VERIFIED_READ_ONLY":
        raise ValueError("phase42 sourceState is not VERIFIED_READ_ONLY")

    if root.get("executionAuthorized") is not False:
        raise ValueError("phase42 execution authorization violation")

    readiness = root.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("ready") is not True:
        raise ValueError("phase42 readiness violation")

    verification = root.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("phase42 verification missing")

    if verification.get("valid") is not True:
        raise ValueError("phase42 verification invalid")

    if verification.get("requiredLayers") != 9:
        raise ValueError("phase42 requiredLayers mismatch")

    if verification.get("verifiedLayers") != 9:
        raise ValueError("phase42 verifiedLayers mismatch")

    if verification.get("checkpoint") != "VERIFIED":
        raise ValueError("phase42 checkpoint is not VERIFIED")

    digest = verification.get("semanticDigest")
    if not isinstance(digest, str) or not HEX64.fullmatch(digest):
        raise ValueError("phase42 semanticDigest invalid")


def semantic_projection(records):
    return {
        "version": VERSION,
        "type": TYPE,
        "mode": MODE,
        "phases": [
            {
                "phase": r["phase"],
                "type": r["type"],
                "path": r["path"],
                "generatedAt": r["generatedAt"],
                "sha256": r["sha256"],
            }
            for r in records
        ],
    }


def build_output():
    errors = []

    try:
        records = [load_phase(p) for p in PHASES]

        validate_phase42(json.loads(
            (BASE / PHASES[42][0]).read_text()
        ))

        for previous, current in zip(records, records[1:]):
            if current["timestamp"] < previous["timestamp"]:
                raise ValueError(
                    f"temporal regression: phase{current['phase']} "
                    f"precedes phase{previous['phase']}"
                )

        projection = semantic_projection(records)
        digest = sha256(projection)

        if CHECKPOINT.exists():
            try:
                checkpoint = json.loads(CHECKPOINT.read_text())
            except Exception as exc:
                raise ValueError(f"checkpoint invalid: {exc}")

            if checkpoint.get("type") != TYPE:
                raise ValueError("checkpoint type mismatch")

            if checkpoint.get("version") != VERSION:
                raise ValueError("checkpoint version mismatch")

            if checkpoint.get("semanticDigest") != digest:
                raise ValueError("temporal semantic digest drift")

            if checkpoint.get("semanticProjection") != projection:
                raise ValueError("temporal semantic projection drift")

            state = "VERIFIED_READ_ONLY"
            ready = True
            checkpoint_state = "VERIFIED"
            verified = 12
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
                    "ALL_REQUIRED_TEMPORAL_LAYERS_VERIFIED"
                    if ready
                    else "TEMPORAL_CHECKPOINT_ESTABLISHED"
                ),
            },
            "verification": {
                "valid": True,
                "requiredLayers": 12,
                "verifiedLayers": verified,
                "checkpoint": checkpoint_state,
                "semanticDigest": digest,
                "phases": {
                    f"phase{r['phase']}": r["generatedAt"]
                    for r in records
                },
            },
            "sources": projection["phases"],
            "errors": [],
            "errorCount": 0,
            "policy": policy(),
        }

    except Exception as exc:
        errors.append(str(exc))

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
                "reason": "TEMPORAL_CONTINUITY_VALIDATION_FAILED",
            },
            "verification": {
                "valid": False,
                "requiredLayers": 12,
                "verifiedLayers": 0,
                "checkpoint": "NOT_VERIFIED",
            },
            "sources": [],
            "errors": errors,
            "errorCount": len(errors),
            "policy": policy(),
        }


def main():
    BASE.mkdir(parents=True, exist_ok=True)

    result = build_output()

    if (
        result["state"] == "CHECKPOINT_ESTABLISHED"
        and result["verification"].get("semanticDigest")
    ):
        records = [load_phase(p) for p in PHASES]
        projection = semantic_projection(records)

        checkpoint = {
            "version": VERSION,
            "type": TYPE,
            "createdAt": now(),
            "semanticDigest": result["verification"]["semanticDigest"],
            "semanticProjection": projection,
        }

        CHECKPOINT.write_text(
            json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n"
        )

    OUTPUT.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    )

    print(f"STATE: {result['state']}")
    print(f"SOURCE STATE: {result['sourceState']}")
    print(f"READY: {result['readiness']['ready']}")
    print(f"VALID: {result['verification']['valid']}")
    print(f"CHECKPOINT: {result['verification']['checkpoint']}")
    print(
        "VERIFIED LAYERS: "
        f"{result['verification']['verifiedLayers']}/"
        f"{result['verification']['requiredLayers']}"
    )

    if "semanticDigest" in result["verification"]:
        print(
            "SEMANTIC DIGEST: "
            f"{result['verification']['semanticDigest']}"
        )

    print(f"ERROR COUNT: {result['errorCount']}")

    return 0 if result["verification"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
