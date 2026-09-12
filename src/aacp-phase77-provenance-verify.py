from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provider-output" / "aacp-observer"

P65 = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify.json"
)

P65_CP = BASE / (
    "aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "semantic-continuity-stability-history-integrity-verify-checkpoint.json"
)

P74 = BASE / (
    "latest-aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "phase74-determinism-integrity-history.json"
)

P74_CP = BASE / (
    "aacp-evidence-chain-health-finality-stability-history"
    "-continuity-drift-continuity-stability-history-continuity-"
    "phase74-determinism-integrity-history-checkpoint.json"
)

P75 = BASE / "phase75-cross-phase-consistency.json"
P75_CP = BASE / "phase75-cross-phase-consistency-checkpoint.json"

P76 = BASE / "phase76-evidence-reconstruction.json"
P76_CP = BASE / "phase76-evidence-reconstruction-checkpoint.json"

OUTPUT = BASE / "phase77-provenance.json"
CHECKPOINT = BASE / "phase77-provenance-checkpoint.json"

TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CROSS_PHASE_RECONSTRUCTION_PROVENANCE_VERIFY"
)

PHASE75_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "CROSS_PHASE_CONSISTENCY_VERIFY"
)

PHASE76_TYPE = (
    "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
    "DETERMINISTIC_EVIDENCE_CHAIN_RECONSTRUCTION_VERIFY"
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def require(condition, errors, message):
    if not condition:
        errors.append(message)


def main():
    errors = []

    paths = (
        P65,
        P65_CP,
        P74,
        P74_CP,
        P75,
        P75_CP,
        P76,
        P76_CP,
    )

    for path in paths:
        if not path.exists():
            errors.append(f"missing:{path.name}")

    if errors:
        print("STATE: INVALID")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    p65 = load(P65)
    cp65 = load(P65_CP)
    p74 = load(P74)
    cp74 = load(P74_CP)
    p75 = load(P75)
    cp75 = load(P75_CP)
    p76 = load(P76)
    cp76 = load(P76_CP)

    # Phase65 provenance.
    require(
        p65.get("state") == "VERIFIED_READ_ONLY",
        errors,
        "phase65_state_invalid",
    )
    require(
        p65.get("sourceState") == "VERIFIED_READ_ONLY",
        errors,
        "phase65_source_state_invalid",
    )
    require(
        p65.get("executionAuthorized") is False,
        errors,
        "phase65_execution_authorized",
    )
    require(
        p65.get("type")
        == (
            "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_"
            "CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_"
            "SEMANTIC_CONTINUITY_STABILITY_HISTORY_INTEGRITY_VERIFY"
        ),
        errors,
        "phase65_type_invalid",
    )

    # Phase74 provenance.
    require(
        p74.get("state") == "VERIFIED_READ_ONLY",
        errors,
        "phase74_state_invalid",
    )
    require(
        p74.get("sourceState") == "VERIFIED_READ_ONLY",
        errors,
        "phase74_source_state_invalid",
    )
    require(
        p74.get("executionAuthorized") is False,
        errors,
        "phase74_execution_authorized",
    )

    # Phase75 provenance.
    require(
        p75.get("state") == "VERIFIED_READ_ONLY",
        errors,
        "phase75_state_invalid",
    )
    require(
        p75.get("sourceState") == "VERIFIED_READ_ONLY",
        errors,
        "phase75_source_state_invalid",
    )
    require(
        p75.get("executionAuthorized") is False,
        errors,
        "phase75_execution_authorized",
    )
    require(
        p75.get("type") == PHASE75_TYPE,
        errors,
        "phase75_type_invalid",
    )
    require(
        p75.get("verification", {}).get("valid") is True,
        errors,
        "phase75_verification_invalid",
    )

    # Phase76 provenance.
    require(
        p76.get("state") == "VERIFIED_READ_ONLY",
        errors,
        "phase76_state_invalid",
    )
    require(
        p76.get("sourceState") == "VERIFIED_READ_ONLY",
        errors,
        "phase76_source_state_invalid",
    )
    require(
        p76.get("executionAuthorized") is False,
        errors,
        "phase76_execution_authorized",
    )
    require(
        p76.get("type") == PHASE76_TYPE,
        errors,
        "phase76_type_invalid",
    )
    require(
        p76.get("verification", {}).get("valid") is True,
        errors,
        "phase76_verification_invalid",
    )

    # Checkpoint ownership/linkage.
    require(
        cp75.get("phase65CheckpointDigest") == digest(cp65),
        errors,
        "phase75_phase65_linkage_invalid",
    )

    require(
        cp76.get("phase75OutputDigest") == digest(p75),
        errors,
        "phase76_phase75_output_linkage_invalid",
    )

    require(
        cp76.get("phase75CheckpointDigest") == digest(cp75),
        errors,
        "phase76_phase75_checkpoint_linkage_invalid",
    )

    require(
        cp76.get("phase75CrossPhaseDigest")
        == p75.get("verification", {}).get("crossPhaseDigest"),
        errors,
        "phase76_cross_phase_linkage_invalid",
    )

    require(
        cp76.get("reconstructedCrossPhaseDigest")
        == p75.get("verification", {}).get("crossPhaseDigest"),
        errors,
        "phase76_reconstruction_linkage_invalid",
    )

    # Phase74 checkpoint must correspond to Phase74 output.
    require(
        cp74.get("type") == p74.get("type"),
        errors,
        "phase74_checkpoint_type_linkage_invalid",
    )

    require(
        cp74.get("integrityDigest")
        == p74.get("verification", {}).get("integrityDigest"),
        errors,
        "phase74_checkpoint_integrity_linkage_invalid",
    )

    # Build deterministic provenance projection.
    provenance = {
        "phase65OutputDigest": digest(p65),
        "phase65CheckpointDigest": digest(cp65),
        "phase74OutputDigest": digest(p74),
        "phase74CheckpointDigest": digest(cp74),
        "phase75OutputDigest": digest(p75),
        "phase75CheckpointDigest": digest(cp75),
        "phase76OutputDigest": digest(p76),
        "phase76CheckpointDigest": digest(cp76),
        "phase75CrossPhaseDigest": p75["verification"]["crossPhaseDigest"],
        "phase76ReconstructedDigest": cp76["reconstructedCrossPhaseDigest"],
    }

    provenance_digest = digest(provenance)

    if errors:
        output = {
            "state": "INVALID",
            "sourceState": "INVALID",
            "type": TYPE,
            "version": 1,
            "executionAuthorized": False,
            "readiness": {
                "observations": 0,
                "requiredObservations": 1,
                "ready": False,
            },
            "verification": {
                "checkpoint": "INVALID",
                "provenanceDigest": provenance_digest,
                "valid": False,
            },
            "safety": {
                "broadcastPerformed": False,
                "signingPerformed": False,
                "submissionPerformed": False,
            },
            "sideEffects": {
                "networkAccess": False,
                "walletAccess": False,
            },
            "errorCount": len(errors),
            "errors": errors,
        }
        OUTPUT.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("STATE: INVALID")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    checkpoint = {
        "version": 1,
        "type": TYPE,
        "observationCount": 3,
        "phase75OutputDigest": digest(p75),
        "phase75CheckpointDigest": digest(cp75),
        "phase76OutputDigest": digest(p76),
        "phase76CheckpointDigest": digest(cp76),
        "phase75CrossPhaseDigest": p75["verification"]["crossPhaseDigest"],
        "phase76ReconstructedDigest": cp76["reconstructedCrossPhaseDigest"],
        "provenanceDigest": provenance_digest,
    }

    output = {
        "errorCount": 0,
        "errors": [],
        "executionAuthorized": False,
        "mode": "READ_ONLY",
        "readiness": {
            "observations": 3,
            "ready": True,
            "requiredObservations": 3,
        },
        "safety": {
            "broadcastPerformed": False,
            "signingPerformed": False,
            "submissionPerformed": False,
        },
        "sideEffects": {
            "networkAccess": False,
            "walletAccess": False,
        },
        "sourceState": "VERIFIED_READ_ONLY",
        "state": "VERIFIED_READ_ONLY",
        "type": TYPE,
        "verification": {
            "checkpoint": "VERIFIED",
            "provenanceDigest": provenance_digest,
            "valid": True,
        },
        "version": 1,
    }

    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    CHECKPOINT.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STATE: VERIFIED_READ_ONLY")
    print("SOURCE STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("OBSERVATIONS: 3")
    print(f"PROVENANCE DIGEST: {provenance_digest}")
    print("ERROR COUNT: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
