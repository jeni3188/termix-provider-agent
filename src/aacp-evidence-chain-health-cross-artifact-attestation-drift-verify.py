#!/usr/bin/env python3

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

BASE = Path("provider-output/aacp-observer")

PHASE46 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-consistency-verify.json"
)

PHASE45 = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-identity-attestation.json"
)

CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-cross-artifact-attestation-drift-checkpoint.json"
)

OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-"
    "cross-artifact-attestation-drift-verify.json"
)

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_DRIFT_VERIFY"
PHASE45_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_IDENTITY_ATTESTATION"
PHASE46_TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_ARTIFACT_ATTESTATION_CONSISTENCY_VERIFY"

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def read_json(path):
    return json.loads(path.read_text())


def digest(obj):
    raw = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def valid_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
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

    for value in safety.values():
        if isinstance(value, bool) and value is True:
            return False

    if obj.get("errorCount") != 0:
        return False

    if obj.get("errors") != []:
        return False

    return True


def build_output(
    state,
    source_state,
    ready,
    valid,
    checkpoint_state,
    verified_layers,
    drift_digest,
    errors,
):
    return {
        "version": 1,
        "type": TYPE,
        "generatedAt": datetime.now().astimezone().isoformat(),
        "mode": "READ_ONLY",
        "state": state,
        "sourceState": source_state,
        "executionAuthorized": False,
        "safety": {
            "walletAccessed": False,
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
                "CROSS_ARTIFACT_ATTESTATION_DRIFT_FREE"
                if ready
                else (
                    "CHECKPOINT_ESTABLISHED"
                    if checkpoint_state == "ESTABLISHED"
                    else "CROSS_ARTIFACT_ATTESTATION_DRIFT_DETECTED"
                )
            ),
        },
        "verification": {
            "valid": valid,
            "requiredLayers": 14,
            "verifiedLayers": verified_layers,
            "checkpoint": checkpoint_state,
            "driftDigest": drift_digest,
        },
        "sources": {
            "phase45": str(PHASE45),
            "phase46": str(PHASE46),
            "checkpoint": str(CHECKPOINT),
        },
        "errors": errors,
        "errorCount": len(errors),
        "policy": {
            "failClosed": True,
            "readOnly": True,
        },
    }


def main():
    errors = []

    if not PHASE45.exists():
        errors.append("phase45: missing")
    if not PHASE46.exists():
        errors.append("phase46: missing")

    phase45 = None
    phase46 = None

    if PHASE45.exists():
        try:
            phase45 = read_json(PHASE45)
        except Exception:
            errors.append("phase45: corrupt JSON")

    if PHASE46.exists():
        try:
            phase46 = read_json(PHASE46)
        except Exception:
            errors.append("phase46: corrupt JSON")

    identities = None
    phase45_digest = None
    phase46_digest = None

    if phase45 is not None:
        if phase45.get("type") != PHASE45_TYPE:
            errors.append("phase45: type mismatch")

        if not safety_ok(phase45):
            errors.append("phase45: safety violation")

        verification = phase45.get("verification")
        if not isinstance(verification, dict):
            errors.append("phase45: verification missing")
        else:
            if verification.get("valid") is not True:
                errors.append("phase45: invalid")

            if verification.get("requiredLayers") != 14:
                errors.append("phase45: required layer mismatch")

            if verification.get("verifiedLayers") != 14:
                errors.append("phase45: verified layer mismatch")

            if verification.get("checkpoint") != "VERIFIED":
                errors.append("phase45: checkpoint violation")

            phase45_digest = verification.get("attestationDigest")

            if not HEX64.fullmatch(str(phase45_digest or "")):
                errors.append("phase45: malformed attestation digest")

            identities = verification.get("artifacts")

            if not isinstance(identities, list) or len(identities) != 14:
                errors.append("phase45: artifact identity list invalid")
            else:
                for item in identities:
                    if not isinstance(item, dict):
                        errors.append("phase45: malformed artifact identity")
                        break

                    for key in ("phase", "type", "path", "generatedAt", "sha256"):
                        if key not in item:
                            errors.append(
                                f"phase45: artifact identity missing {key}"
                            )
                            break

                    if not HEX64.fullmatch(str(item.get("sha256", ""))):
                        errors.append(
                            f"phase45: malformed artifact sha256 "
                            f"phase={item.get('phase')}"
                        )

                    if not valid_timestamp(item.get("generatedAt")):
                        errors.append(
                            f"phase45: malformed artifact timestamp "
                            f"phase={item.get('phase')}"
                        )

    if phase46 is not None:
        if phase46.get("type") != PHASE46_TYPE:
            errors.append("phase46: type mismatch")

        if not safety_ok(phase46):
            errors.append("phase46: safety violation")

        if phase46.get("state") != "VERIFIED_READ_ONLY":
            errors.append("phase46: state violation")

        if phase46.get("sourceState") != "VERIFIED_READ_ONLY":
            errors.append("phase46: source state violation")

        readiness = phase46.get("readiness")
        if not isinstance(readiness, dict) or readiness.get("ready") is not True:
            errors.append("phase46: readiness violation")

        verification = phase46.get("verification")
        if not isinstance(verification, dict):
            errors.append("phase46: verification missing")
        else:
            if verification.get("valid") is not True:
                errors.append("phase46: validity violation")

            if verification.get("requiredLayers") != 14:
                errors.append("phase46: required layer mismatch")

            if verification.get("verifiedLayers") != 14:
                errors.append("phase46: verified layer mismatch")

            if verification.get("checkpoint") != "VERIFIED":
                errors.append("phase46: checkpoint violation")

            phase46_digest = verification.get("consistencyDigest")

            if not HEX64.fullmatch(str(phase46_digest or "")):
                errors.append("phase46: malformed consistency digest")

    if identities is not None and not errors:
        current_identities = []

        for item in identities:
            phase = item["phase"]
            path = Path(item["path"])

            if not path.exists():
                errors.append(f"phase{phase}: artifact missing")
                continue

            try:
                current_sha = file_sha256(path)
            except Exception:
                errors.append(f"phase{phase}: artifact unreadable")
                continue

            current_identities.append(
                {
                    "phase": phase,
                    "type": item["type"],
                    "path": item["path"],
                    "generatedAt": item["generatedAt"],
                    "sha256": current_sha,
                }
            )

            if current_sha != item["sha256"]:
                errors.append(f"phase{phase}: artifact identity drift")

        if not errors:
            if current_identities != identities:
                errors.append("artifact identity projection drift")

    drift_projection = {
        "version": 1,
        "type": TYPE,
        "phase45AttestationDigest": phase45_digest,
        "phase46ConsistencyDigest": phase46_digest,
        "artifacts": identities,
    }

    drift_digest = digest(drift_projection)

    checkpoint = None

    if CHECKPOINT.exists():
        try:
            checkpoint = read_json(CHECKPOINT)
        except Exception:
            errors.append("checkpoint: corrupt JSON")

    if not errors and checkpoint is None:
        output = build_output(
            "CHECKPOINT_ESTABLISHED",
            "CHECKPOINT_ESTABLISHED",
            False,
            True,
            "ESTABLISHED",
            0,
            drift_digest,
            [],
        )

        checkpoint_payload = {
            "version": 1,
            "type": TYPE,
            "createdAt": datetime.now().astimezone().isoformat(),
            "driftDigest": drift_digest,
            "driftProjection": drift_projection,
        }

        OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
        CHECKPOINT.write_text(
            json.dumps(checkpoint_payload, indent=2, ensure_ascii=False) + "\n"
        )

        print("STATE: CHECKPOINT_ESTABLISHED")
        print("SOURCE STATE: CHECKPOINT_ESTABLISHED")
        print("READY: False")
        print("VALID: True")
        print("CHECKPOINT: ESTABLISHED")
        print("VERIFIED LAYERS: 0/14")
        print(f"DRIFT DIGEST: {drift_digest}")
        print("ERROR COUNT: 0")
        return 0

    if checkpoint is None:
        output = build_output(
            "BLOCKED",
            "BLOCKED",
            False,
            False,
            "BLOCKED",
            0,
            drift_digest,
            errors,
        )
    else:
        if checkpoint.get("type") != TYPE:
            errors.append("checkpoint: type mismatch")

        if checkpoint.get("driftDigest") != drift_digest:
            errors.append("checkpoint: drift detected")

        if checkpoint.get("driftProjection") != drift_projection:
            errors.append("checkpoint: projection drift")

        if errors:
            output = build_output(
                "BLOCKED",
                "BLOCKED",
                False,
                False,
                "BLOCKED",
                0,
                drift_digest,
                errors,
            )
        else:
            output = build_output(
                "VERIFIED_READ_ONLY",
                "VERIFIED_READ_ONLY",
                True,
                True,
                "VERIFIED",
                14,
                drift_digest,
                [],
            )

    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")

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
    print(f"DRIFT DIGEST: {drift_digest}")
    print(f"ERROR COUNT: {output['errorCount']}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
