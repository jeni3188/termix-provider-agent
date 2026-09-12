from pathlib import Path
from hashlib import sha256
from datetime import datetime
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "DETERMINISTIC_EVIDENCE_CHAIN_RECONSTRUCTION_VERIFY"
)

PHASE75_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CROSS_PHASE_CONSISTENCY_VERIFY"
)

P75_OUTPUT = BASE / "phase75-cross-phase-consistency.json"
P75_CHECKPOINT = BASE / "phase75-cross-phase-consistency-checkpoint.json"

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

OUTPUT = BASE / "phase76-evidence-reconstruction.json"
CHECKPOINT = BASE / "phase76-evidence-reconstruction-checkpoint.json"


def load(path):
    if not path.exists():
        raise ValueError(f"missing:{path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json:{path.name}:{exc.msg}")


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def valid_hex_digest(value):
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def validate_phase75(output, checkpoint):
    errors = []

    if output.get("type") != PHASE75_TYPE:
        errors.append("phase75_type_invalid")

    if output.get("version") != 1:
        errors.append("phase75_version_invalid")

    if output.get("mode") != "READ_ONLY":
        errors.append("phase75_mode_invalid")

    if output.get("state") != "VERIFIED_READ_ONLY":
        errors.append("phase75_state_invalid")

    if output.get("sourceState") != "VERIFIED_READ_ONLY":
        errors.append("phase75_source_state_invalid")

    if output.get("executionAuthorized") is not False:
        errors.append("phase75_execution_authorized_invalid")

    readiness = output.get("readiness")
    verification = output.get("verification")
    safety = output.get("safety")
    effects = output.get("sideEffects")

    if not isinstance(readiness, dict):
        errors.append("phase75_readiness_invalid")
    else:
        if readiness.get("ready") is not True:
            errors.append("phase75_ready_invalid")
        if readiness.get("observations") != 3:
            errors.append("phase75_observations_invalid")
        if readiness.get("requiredObservations") != 3:
            errors.append("phase75_required_observations_invalid")

    if not isinstance(verification, dict):
        errors.append("phase75_verification_invalid")
    else:
        if verification.get("valid") is not True:
            errors.append("phase75_valid_invalid")
        if verification.get("checkpoint") != "VERIFIED":
            errors.append("phase75_checkpoint_invalid")
        if not valid_hex_digest(
            verification.get("crossPhaseDigest")
        ):
            errors.append("phase75_cross_phase_digest_invalid")

    if not isinstance(safety, dict):
        errors.append("phase75_safety_invalid")
    else:
        for field in (
            "signingPerformed",
            "broadcastPerformed",
            "submissionPerformed",
        ):
            if safety.get(field) is not False:
                errors.append(f"phase75_{field}_invalid")

    if not isinstance(effects, dict):
        errors.append("phase75_side_effects_invalid")
    else:
        if effects.get("networkAccess") is not False:
            errors.append("phase75_network_access_invalid")
        if effects.get("walletAccess") is not False:
            errors.append("phase75_wallet_access_invalid")

    if checkpoint.get("version") != 1:
        errors.append("phase75_checkpoint_version_invalid")

    if checkpoint.get("type") != PHASE75_TYPE:
        errors.append("phase75_checkpoint_type_invalid")

    if checkpoint.get("observationCount") != 3:
        errors.append("phase75_checkpoint_observations_invalid")

    for field in (
        "crossPhaseDigest",
        "phase65CheckpointDigest",
        "phase74CheckpointDigest",
    ):
        if not valid_hex_digest(checkpoint.get(field)):
            errors.append(f"phase75_checkpoint_{field}_invalid")

    if isinstance(verification, dict):
        if (
            checkpoint.get("crossPhaseDigest")
            != verification.get("crossPhaseDigest")
        ):
            errors.append("phase75_checkpoint_digest_mismatch")

    return errors


def reconstruct_cross_phase_digest(p65, cp65, p74):
    p65_verification = p65.get("verification", {})
    p65_readiness = p65.get("readiness", {})
    p74_verification = p74.get("verification", {})
    p74_readiness = p74.get("readiness", {})

    evidence = {
        "phase65Type": p65.get("type"),
        "phase74Type": p74.get("type"),
        "phase65IntegrityDigest": p65_verification.get(
            "integrityDigest"
        ),
        "phase74IntegrityDigest": p74_verification.get(
            "integrityDigest"
        ),
        "phase74ContinuityDigest": p74_verification.get(
            "continuityDigest"
        ),
        "phase65ObservationCount": p65_readiness.get(
            "observations"
        ),
        "phase74ObservationCount": p74_readiness.get(
            "observations"
        ),
        "phase65CheckpointDigest": digest(cp65),
    }

    return digest(evidence), evidence


def main():
    errors = []

    try:
        p75 = load(P75_OUTPUT)
        cp75 = load(P75_CHECKPOINT)
        p65 = load(P65_OUTPUT)
        cp65 = load(P65_CHECKPOINT)
        p74 = load(P74_OUTPUT)
    except ValueError as exc:
        errors.append(str(exc))
        p75 = cp75 = p65 = cp65 = p74 = {}

    if not errors:
        errors.extend(validate_phase75(p75, cp75))

    reconstructed = ""
    reconstruction_evidence = {}

    if not errors:
        reconstructed, reconstruction_evidence = (
            reconstruct_cross_phase_digest(
                p65,
                cp65,
                p74,
            )
        )

        expected = p75["verification"]["crossPhaseDigest"]

        if reconstructed != expected:
            errors.append("cross_phase_digest_reconstruction_mismatch")

        if cp75.get("crossPhaseDigest") != reconstructed:
            errors.append("checkpoint_reconstruction_mismatch")

        expected_p65_checkpoint = digest(cp65)

        if (
            cp75.get("phase65CheckpointDigest")
            != expected_p65_checkpoint
        ):
            errors.append("phase65_checkpoint_linkage_invalid")

        if not valid_hex_digest(
            cp75.get("phase65CheckpointDigest")
        ):
            errors.append("phase65_checkpoint_digest_invalid")

        if not valid_hex_digest(
            cp75.get("phase74CheckpointDigest")
        ):
            errors.append("phase74_checkpoint_digest_invalid")

    result = {
        "type": TYPE,
        "version": 1,
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY" if not errors else "INVALID",
        "sourceState": (
            "VERIFIED_READ_ONLY" if not errors else "INVALID"
        ),
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
            "phase75CrossPhaseDigest": (
                p75.get("verification", {}).get("crossPhaseDigest")
            ),
            "reconstructedCrossPhaseDigest": reconstructed,
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
                "phase75OutputDigest": (
                    digest(p75) if p75 else ""
                ),
                "phase75CheckpointDigest": (
                    digest(cp75) if cp75 else ""
                ),
                "phase75CrossPhaseDigest": (
                    p75.get("verification", {}).get(
                        "crossPhaseDigest", ""
                    )
                ),
                "reconstructedCrossPhaseDigest": reconstructed,
                "reconstructionEvidenceDigest": (
                    digest(reconstruction_evidence)
                    if reconstruction_evidence
                    else ""
                ),
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
    print(
        "PHASE75 CROSS-PHASE DIGEST:",
        result["verification"]["phase75CrossPhaseDigest"],
    )
    print(
        "RECONSTRUCTED DIGEST:",
        result["verification"]["reconstructedCrossPhaseDigest"],
    )
    print("ERROR COUNT:", len(errors))

    if errors:
        for error in errors:
            print("ERROR:", error)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
