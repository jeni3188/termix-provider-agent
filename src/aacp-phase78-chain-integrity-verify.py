#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

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

P77 = BASE / "phase77-provenance.json"
P77_CP = BASE / "phase77-provenance-checkpoint.json"

TYPE = "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CROSS_PHASE_PROVENANCE_CHAIN_INTEGRITY_VERIFY"

def digest(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def load_path(path):
    if not path.exists():
        raise RuntimeError(f"missing:{path.name}")
    return json.loads(path.read_text(encoding="utf-8"))

def load_chain():
    return (
        load_path(P65),
        load_path(P65_CP),
        load_path(P74),
        load_path(P74_CP),
        load_path(P75),
        load_path(P75_CP),
        load_path(P76),
        load_path(P76_CP),
        load_path(P77),
        load_path(P77_CP),
    )

def main():
    errors = []

    try:
        (
            p65,
            p65_cp,
            p74,
            p74_cp,
            p75,
            p75_cp,
            p76,
            p76_cp,
            p77,
            p77_cp,
        ) = load_chain()
    except Exception as exc:
        errors.append(f"load:{exc}")
        p65 = p65_cp = p74 = p74_cp = {}
        p75 = p75_cp = {}
        p76 = p76_cp = {}
        p77 = p77_cp = {}

    for label, obj in (
        ("phase65", p65),
        ("phase74", p74),
        ("phase75", p75),
        ("phase76", p76),
        ("phase77", p77),
    ):
        if obj.get("state") != "VERIFIED_READ_ONLY":
            errors.append(f"{label}:state")
        if obj.get("sourceState") != "VERIFIED_READ_ONLY":
            errors.append(f"{label}:sourceState")
        if obj.get("executionAuthorized") is not False:
            errors.append(f"{label}:executionAuthorized")

    expected = {
        "phase65": "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_STABILITY_HISTORY_INTEGRITY_VERIFY",
        "phase74": "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CONTINUITY_DRIFT_CONTINUITY_STABILITY_HISTORY_CONTINUITY_SEMANTIC_CONTINUITY_STABILITY_HISTORY_INTEGRITY_CONTINUITY_STABILITY_HISTORY_DETERMINISM_INTEGRITY_CONTINUITY_STABILITY_HISTORY_INTEGRITY_VERIFY",
        "phase75": "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CROSS_PHASE_CONSISTENCY_VERIFY",
        "phase76": "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_DETERMINISTIC_EVIDENCE_CHAIN_RECONSTRUCTION_VERIFY",
        "phase77": "AACP_EVIDENCE_CHAIN_HEALTH_FINALITY_STABILITY_HISTORY_CROSS_PHASE_RECONSTRUCTION_PROVENANCE_VERIFY",
    }

    for label, obj in (
        ("phase65", p65),
        ("phase74", p74),
        ("phase75", p75),
        ("phase76", p76),
        ("phase77", p77),
    ):
        if obj.get("type") != expected[label]:
            errors.append(f"{label}:type")

    # Phase75 must reconstruct its Phase65 checkpoint ownership.
    if p75_cp.get("phase65CheckpointDigest") != digest(p65_cp):
        errors.append("phase75:phase65CheckpointDigest")

    # Phase76 must own Phase75 output/checkpoint.
    if p76_cp.get("phase75OutputDigest") != digest(p75):
        errors.append("phase76:phase75OutputDigest")
    if p76_cp.get("phase75CheckpointDigest") != digest(p75_cp):
        errors.append("phase76:phase75CheckpointDigest")

    # Phase76 reconstructed digest must agree with Phase75.
    p75_cross = p75.get("verification", {}).get("crossPhaseDigest")
    if p76_cp.get("phase75CrossPhaseDigest") != p75_cross:
        errors.append("phase76:crossPhaseDigest")

    if p76_cp.get("reconstructedCrossPhaseDigest") != p75_cross:
        errors.append("phase76:reconstructedDigest")

    # Phase77 owns the upstream Phase65–76 chain through its
    # canonical provenance digest. Phase77 checkpoint does not persist
    # the individual Phase65/Phase74 provenance fields.
    p77_ver = p77.get("verification", {})
    p77_cp_fields = p77_cp

    phase77_provenance = {
        "phase65OutputDigest": digest(p65),
        "phase65CheckpointDigest": digest(p65_cp),
        "phase74OutputDigest": digest(p74),
        "phase74CheckpointDigest": digest(p74_cp),
        "phase75OutputDigest": digest(p75),
        "phase75CheckpointDigest": digest(p75_cp),
        "phase76OutputDigest": digest(p76),
        "phase76CheckpointDigest": digest(p76_cp),
        "phase75CrossPhaseDigest": p75_cross,
        "phase76ReconstructedDigest": p76_cp.get(
            "reconstructedCrossPhaseDigest"
        ),
    }

    reconstructed_phase77_provenance_digest = digest(phase77_provenance)

    if p77_ver.get("provenanceDigest") != reconstructed_phase77_provenance_digest:
        errors.append("phase77:provenanceDigest")

    if p77_cp_fields.get("provenanceDigest") != reconstructed_phase77_provenance_digest:
        errors.append("phase77:checkpointProvenanceDigest")

    # Phase77 checkpoint must still own the persisted Phase75/76 chain.
    if p77_cp_fields.get("phase75OutputDigest") != digest(p75):
        errors.append("phase77:phase75OutputDigest")

    if p77_cp_fields.get("phase75CheckpointDigest") != digest(p75_cp):
        errors.append("phase77:phase75CheckpointDigest")

    if p77_cp_fields.get("phase76OutputDigest") != digest(p76):
        errors.append("phase77:phase76OutputDigest")

    if p77_cp_fields.get("phase76CheckpointDigest") != digest(p76_cp):
        errors.append("phase77:phase76CheckpointDigest")

    if p77_cp_fields.get("phase75CrossPhaseDigest") != p75_cross:
        errors.append("phase77:phase75CrossPhaseDigest")

    if p77_cp_fields.get("phase76ReconstructedDigest") != p76_cp.get(
        "reconstructedCrossPhaseDigest"
    ):
        errors.append("phase77:phase76ReconstructedDigest")

    # Phase78 canonical provenance chain projection.
    chain = {
        "phase65OutputDigest": digest(p65),
        "phase65CheckpointDigest": digest(p65_cp),
        "phase74OutputDigest": digest(p74),
        "phase74CheckpointDigest": digest(p74_cp),
        "phase75OutputDigest": digest(p75),
        "phase75CheckpointDigest": digest(p75_cp),
        "phase76OutputDigest": digest(p76),
        "phase76CheckpointDigest": digest(p76_cp),
        "phase77OutputDigest": digest(p77),
        "phase77CheckpointDigest": digest(p77_cp),
        "phase75CrossPhaseDigest": p75_cross,
        "phase76ReconstructedDigest": p76_cp.get("reconstructedCrossPhaseDigest"),
        "phase77ProvenanceDigest": p77_ver.get("provenanceDigest"),
    }

    chain_digest = digest(chain)

    result = {
        "version": 1,
        "type": TYPE,
        "generatedAt": datetime.now(timezone.utc).astimezone().isoformat(),
        "mode": "READ_ONLY",
        "state": "VERIFIED_READ_ONLY" if not errors else "REJECTED_READ_ONLY",
        "sourceState": "VERIFIED_READ_ONLY",
        "executionAuthorized": False,
        "readiness": {
            "ready": not errors,
            "observations": 3,
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
        "verification": {
            "checkpoint": "VERIFIED" if not errors else "REJECTED",
            "chainDigest": chain_digest,
            "valid": not errors,
        },
        "errorCount": len(errors),
        "errors": errors,
    }

    print(f"STATE: {result['state']}")
    print(f"SOURCE STATE: {result['sourceState']}")
    print(f"READY: {result['readiness']['ready']}")
    print(f"VALID: {result['verification']['valid']}")
    print(f"CHECKPOINT: {result['verification']['checkpoint']}")
    print(f"OBSERVATIONS: {result['readiness']['observations']}")
    print(f"CHAIN DIGEST: {chain_digest}")
    print(f"ERROR COUNT: {len(errors)}")

    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
