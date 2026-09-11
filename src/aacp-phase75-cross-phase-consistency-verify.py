from pathlib import Path
from hashlib import sha256
from datetime import datetime
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

PHASE65_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY"
    "_CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_"
    "SEMANTIC_CONTINUITY_STABILITY_HISTORY_INTEGRITY_VERIFY"
)

PHASE74_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY"
    "_CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_"
    "SEMANTIC_CONTINUITY_STABILITY_HISTORY_INTEGRITY_"
    "CONTINUITY_STABILITY_HISTORY_DETERMINISM_INTEGRITY_"
    "CONTINUITY_STABILITY_HISTORY_INTEGRITY_VERIFY"
)

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CROSS_PHASE_CONSISTENCY_VERIFY"

P65_OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify.json"
)

P65_CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify-checkpoint.json"
)

P74_OUTPUT = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "phase74-determinism-integrity-history.json"
)

P74_CHECKPOINT = BASE / (
    "aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "phase74-determinism-integrity-history-checkpoint.json"
)

OUTPUT = BASE / "phase75-cross-phase-consistency.json"
CHECKPOINT = BASE / "phase75-cross-phase-consistency-checkpoint.json"


def load(path):
    if not path.exists():
        raise ValueError(f"missing:{path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return sha256(raw).hexdigest()


def valid_hex_digest(value):
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def validate_phase65(p65, cp):
    errors = []

    if p65.get("type") != PHASE65_TYPE:
        errors.append("phase65_type_invalid")

    if p65.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase65_state_invalid")

    if p65.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase65_source_state_invalid")

    if p65.get("executionAuthorized") is not False:
        errors.append("phase65_execution_authorized_invalid")

    readiness = p65.get("readiness")
    verification = p65.get("verification")
    safety = p65.get("safety")
    effects = p65.get("sideEffects")

    if not isinstance(readiness, dict):
        errors.append("phase65_readiness_invalid")
    else:
        if readiness.get("ready") is not True:
            errors.append("phase65_ready_invalid")
        if readiness.get("observations") != 3:
            errors.append("phase65_observations_invalid")
        if readiness.get("requiredObservations") != 3:
            errors.append("phase65_required_observations_invalid")

    if not isinstance(verification, dict):
        errors.append("phase65_verification_invalid")
    else:
        if verification.get("valid") is not True:
            errors.append("phase65_valid_invalid")
        if verification.get("checkpoint") != "VERIFIED":
            errors.append("phase65_checkpoint_invalid")

        for field in (
            "historyDigest",
            "evolutionDigest",
            "integrityDigest",
        ):
            if not valid_hex_digest(verification.get(field)):
                errors.append(f"phase65_{field}_invalid")

    if not isinstance(safety, dict):
        errors.append("phase65_safety_invalid")
    else:
        for field in (
            "signingPerformed",
            "broadcastPerformed",
            "submissionPerformed",
        ):
            if safety.get(field) is not False:
                errors.append(f"phase65_{field}_invalid")

    if not isinstance(effects, dict):
        errors.append("phase65_side_effects_invalid")
    else:
        if effects.get("networkAccess") is not False:
            errors.append("phase65_network_access_invalid")
        if effects.get("walletAccess") is not False:
            errors.append("phase65_wallet_access_invalid")

    if cp.get("version") != 1:
        errors.append("phase65_checkpoint_version_invalid")

    if cp.get("type") != PHASE65_TYPE:
        errors.append("phase65_checkpoint_type_invalid")

    if cp.get("observationCount") != 3:
        errors.append("phase65_checkpoint_observations_invalid")

    if not isinstance(verification, dict):
        return errors

    for field in (
        "historyDigest",
        "evolutionDigest",
        "integrityDigest",
    ):
        if cp.get(field) != verification.get(field):
            errors.append(f"phase65_checkpoint_{field}_mismatch")

    return errors


def validate_phase74(p74, cp74, cp65):
    errors = []

    if p74.get("type") != PHASE74_TYPE:
        errors.append("phase74_type_invalid")

    if p74.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase74_state_invalid")

    if p74.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase74_source_state_invalid")

    if p74.get("executionAuthorized") is not False:
        errors.append("phase74_execution_authorized_invalid")

    readiness = p74.get("readiness")
    verification = p74.get("verification")
    safety = p74.get("safety")
    effects = p74.get("sideEffects")

    if not isinstance(readiness, dict):
        errors.append("phase74_readiness_invalid")
    else:
        if readiness.get("ready") is not True:
            errors.append("phase74_ready_invalid")
        if readiness.get("observations") != 3:
            errors.append("phase74_observations_invalid")

    if not isinstance(verification, dict):
        errors.append("phase74_verification_invalid")
    else:
        if verification.get("valid") is not True:
            errors.append("phase74_valid_invalid")
        if verification.get("checkpoint") != "VERIFIED":
            errors.append("phase74_checkpoint_invalid")

        for field in (
            "integrityDigest",
            "continuityDigest",
        ):
            if not valid_hex_digest(verification.get(field)):
                errors.append(f"phase74_{field}_invalid")

    if not isinstance(safety, dict):
        errors.append("phase74_safety_invalid")
    else:
        for field in (
            "signingPerformed",
            "broadcastPerformed",
            "submissionPerformed",
        ):
            if safety.get(field) is not False:
                errors.append(f"phase74_{field}_invalid")

    if not isinstance(effects, dict):
        errors.append("phase74_side_effects_invalid")
    else:
        if effects.get("networkAccess") is not False:
            errors.append("phase74_network_access_invalid")
        if effects.get("walletAccess") is not False:
            errors.append("phase74_wallet_access_invalid")

    if cp74.get("version") != 1:
        errors.append("phase74_checkpoint_version_invalid")

    if cp74.get("type") != PHASE74_TYPE:
        errors.append("phase74_checkpoint_type_invalid")

    if cp74.get("observationCount") != 3:
        errors.append("phase74_checkpoint_observations_invalid")

    if cp74.get("integrityDigest") != cp65.get("integrityDigest"):
        errors.append("cross_phase_integrity_digest_mismatch")

    if (
        isinstance(verification, dict)
        and cp74.get("integrityDigest") != verification.get("integrityDigest")
    ):
        errors.append("phase74_checkpoint_integrity_mismatch")

    if (
        isinstance(verification, dict)
        and cp74.get("continuityDigest") != verification.get("continuityDigest")
    ):
        errors.append("phase74_checkpoint_continuity_mismatch")

    expected_p65_checkpoint = digest(cp65)

    if cp74.get("phase65CheckpointDigest") != expected_p65_checkpoint:
        errors.append("phase65_checkpoint_linkage_mismatch")

    return errors


def main():
    errors = []

    try:
        p65 = load(P65_OUTPUT)
        cp65 = load(P65_CHECKPOINT)
        p74 = load(P74_OUTPUT)
        cp74 = load(P74_CHECKPOINT)
    except ValueError as exc:
        errors.append(str(exc))
        p65 = cp65 = p74 = cp74 = {}

    if not errors:
        errors.extend(validate_phase65(p65, cp65))
        errors.extend(validate_phase74(p74, cp74, cp65))

    evidence = {
        "phase65Type": p65.get("type"),
        "phase74Type": p74.get("type"),
        "phase65IntegrityDigest": p65.get("verification", {}).get(
            "integrityDigest"
        ),
        "phase74IntegrityDigest": p74.get("verification", {}).get(
            "integrityDigest"
        ),
        "phase74ContinuityDigest": p74.get("verification", {}).get(
            "continuityDigest"
        ),
        "phase65ObservationCount": p65.get("readiness", {}).get(
            "observations"
        ),
        "phase74ObservationCount": p74.get("readiness", {}).get(
            "observations"
        ),
        "phase65CheckpointDigest": digest(cp65) if cp65 else "",
    }

    cross_digest = digest(evidence)

    result = {
        "type": TYPE,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY" if not errors else "INVALID",
        "sourceState": "VERIFIED_READ_ONLY" if not errors else "INVALID",
        "generatedAt": datetime.now().astimezone().isoformat(),
        "executionAuthorized": False,
        "readiness": {
            "ready": not errors,
            "observations": 3 if not errors else 0,
            "requiredObservations": 3,
        },
        "verification": {
            "valid": not errors,
            "checkpoint": "VERIFIED" if not errors else "FAILED",
            "crossPhaseDigest": cross_digest,
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

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    CHECKPOINT.write_text(
        json.dumps(
            {
                "version": 1,
                "type": TYPE,
                "observationCount": result["readiness"]["observations"],
                "crossPhaseDigest": cross_digest,
                "phase65CheckpointDigest": digest(cp65) if cp65 else "",
                "phase74CheckpointDigest": digest(cp74) if cp74 else "",
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STATE:", result["state"])
    print("SOURCE STATE:", result["sourceState"])
    print("READY:", result["readiness"]["ready"])
    print("VALID:", result["verification"]["valid"])
    print("CHECKPOINT:", result["verification"]["checkpoint"])
    print("OBSERVATIONS:", result["readiness"]["observations"])
    print("CROSS-PHASE DIGEST:", cross_digest)
    print("ERROR COUNT:", len(errors))

    if errors:
        for error in errors:
            print("ERROR:", error)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
