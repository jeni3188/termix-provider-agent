#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "provider-output" / "aacp-observer"

PHASE = 92
PREVIOUS_PHASE = 91

EXPECTED_PHASE91_SOURCE_DIGEST = (
    "b37a1423e91f22574ebe9b7edb6df9c0960e3b04adde9a7d368fd1850a7adbe7"
)

EXPECTED_PHASE90_SOURCE_DIGEST = (
    "4620589389747124b1d0bd22c45133be9ea5f503625f732d008349e4fdd8f7a2"
)

PHASE89_OUTPUT = (
    OUT / "phase89-evidence-artifact-integrity-continuity-gate.json"
)

PHASE89_CHECKPOINT = (
    OUT / "phase89-evidence-artifact-integrity-continuity-gate-checkpoint.json"
)

PHASE90_OUTPUT = (
    OUT / "phase90-evidence-artifact-chain-finality-gate.json"
)

PHASE90_CHECKPOINT = (
    OUT / "phase90-evidence-artifact-chain-finality-gate-checkpoint.json"
)

PHASE91_OUTPUT = (
    OUT / "phase91-evidence-artifact-chain-consistency-gate.json"
)

PHASE91_CHECKPOINT = (
    OUT / "phase91-evidence-artifact-chain-consistency-gate-checkpoint.json"
)

PHASE91_SOURCE = (
    ROOT / "src" /
    "aacp-phase91-evidence-artifact-chain-consistency-gate.py"
)

SAFETY_FLAGS = (
    "executionAuthorized",
    "networkAccess",
    "walletPresent",
    "signingEnabled",
    "broadcastEnabled",
    "submissionEnabled",
)


def fail(message):
    print(f"ERROR: {message}")
    print("STATE: REJECTED_READ_ONLY")
    print("READY: False")
    print("VALID: False")
    print("CHECKPOINT: REJECTED")
    sys.exit(1)


def check(condition, message):
    if not condition:
        fail(message)


def load_json(path):
    check(path.exists(), f"Missing artifact: {path.name}")

    try:
        return json.loads(path.read_text())
    except Exception as exc:
        fail(f"Invalid JSON: {path.name}: {exc}")


def sha256_file(path):
    check(path.exists(), f"Missing source: {path}")

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def canonical_digest(data):
    payload = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()

    return hashlib.sha256(payload).hexdigest()


def require_read_only(data, label):
    check(
        data.get("state") == "VERIFIED_READ_ONLY",
        f"{label} state mismatch",
    )

    check(
        data.get("ready") is True,
        f"{label} ready mismatch",
    )

    check(
        data.get("valid") is True,
        f"{label} valid mismatch",
    )

    check(
        data.get("checkpoint") == "VERIFIED",
        f"{label} checkpoint mismatch",
    )

    check(
        data.get("error_count") == 0,
        f"{label} error_count mismatch",
    )

    for flag in SAFETY_FLAGS:
        check(
            data.get(flag) is False,
            f"{label} safety flag enabled: {flag}",
        )


def main():
    phase89_output = load_json(PHASE89_OUTPUT)
    phase89_checkpoint = load_json(PHASE89_CHECKPOINT)

    phase90_output = load_json(PHASE90_OUTPUT)
    phase90_checkpoint = load_json(PHASE90_CHECKPOINT)

    phase91_output = load_json(PHASE91_OUTPUT)
    phase91_checkpoint = load_json(PHASE91_CHECKPOINT)

    source_digest = sha256_file(PHASE91_SOURCE)

    check(
        source_digest == EXPECTED_PHASE91_SOURCE_DIGEST,
        "Phase91 source digest mismatch",
    )

    # Phase89 baseline integrity
    require_read_only(phase89_output, "Phase89 output")
    require_read_only(phase89_checkpoint, "Phase89 checkpoint")

    check(
        str(phase89_output.get("phase")) == "89",
        "Phase89 output phase mismatch",
    )

    check(
        str(phase89_checkpoint.get("phase")) == "89",
        "Phase89 checkpoint phase mismatch",
    )

    check(
        phase89_output.get("previous_phase") == 88,
        "Phase89 output previous_phase mismatch",
    )

    check(
        phase89_checkpoint.get("previous_phase") == 88,
        "Phase89 checkpoint previous_phase mismatch",
    )

    # Phase90 baseline integrity
    require_read_only(phase90_output, "Phase90 output")
    require_read_only(phase90_checkpoint, "Phase90 checkpoint")

    check(
        str(phase90_output.get("phase")) == "90",
        "Phase90 output phase mismatch",
    )

    check(
        str(phase90_checkpoint.get("phase")) == "90",
        "Phase90 checkpoint phase mismatch",
    )

    check(
        phase90_output.get("previous_phase") == 89,
        "Phase90 output previous_phase mismatch",
    )

    check(
        phase90_checkpoint.get("previous_phase") == 89,
        "Phase90 checkpoint previous_phase mismatch",
    )

    # Phase91 baseline integrity
    require_read_only(phase91_output, "Phase91 output")
    require_read_only(phase91_checkpoint, "Phase91 checkpoint")

    check(
        str(phase91_output.get("phase")) == str(PREVIOUS_PHASE),
        "Phase91 output phase mismatch",
    )

    check(
        str(phase91_checkpoint.get("phase")) == str(PREVIOUS_PHASE),
        "Phase91 checkpoint phase mismatch",
    )

    check(
        phase91_output.get("previous_phase") == 90,
        "Phase91 output previous_phase mismatch",
    )

    check(
        phase91_checkpoint.get("previous_phase") == 90,
        "Phase91 checkpoint previous_phase mismatch",
    )

    # Cross-artifact canonical digests
    phase89_output_digest = canonical_digest(phase89_output)
    phase89_checkpoint_digest = canonical_digest(phase89_checkpoint)

    phase90_output_digest = canonical_digest(phase90_output)
    phase90_checkpoint_digest = canonical_digest(phase90_checkpoint)

    phase91_output_digest = canonical_digest(phase91_output)
    phase91_checkpoint_digest = canonical_digest(phase91_checkpoint)

    check(
        phase89_output.get("continuity_digest")
        == phase89_checkpoint.get("continuity_digest"),
        "Phase89 continuity digest mismatch",
    )

    check(
        phase90_output.get("phase89_continuity_digest")
        == phase89_output.get("continuity_digest"),
        "Phase89 to Phase90 continuity mismatch",
    )

    check(
        phase90_checkpoint.get("phase89_continuity_digest")
        == phase89_output.get("continuity_digest"),
        "Phase90 checkpoint continuity mismatch",
    )

    check(
        phase91_output.get("phase90_finality_digest")
        == phase90_output.get("finality_digest"),
        "Phase90 to Phase91 finality mismatch",
    )

    check(
        phase91_checkpoint.get("phase90_finality_digest")
        == phase90_output.get("finality_digest"),
        "Phase91 checkpoint finality mismatch",
    )

    check(
        phase91_output.get("phase90_output_canonical_digest")
        == phase90_output_digest,
        "Phase91 Phase90 output digest mismatch",
    )

    check(
        phase91_output.get("phase90_checkpoint_canonical_digest")
        == phase90_checkpoint_digest,
        "Phase91 Phase90 checkpoint digest mismatch",
    )

    check(
        phase91_checkpoint.get("phase90_output_canonical_digest")
        == phase90_output_digest,
        "Phase91 checkpoint Phase90 output digest mismatch",
    )

    check(
        phase91_checkpoint.get("phase90_checkpoint_canonical_digest")
        == phase90_checkpoint_digest,
        "Phase91 checkpoint Phase90 checkpoint digest mismatch",
    )

    check(
        phase91_output.get("previous_source_digest")
        == EXPECTED_PHASE90_SOURCE_DIGEST,
        "Phase91 previous_source_digest mismatch",
    )

    check(
        phase91_checkpoint.get("previous_source_digest")
        == EXPECTED_PHASE90_SOURCE_DIGEST,
        "Phase91 checkpoint previous_source_digest mismatch",
    )

    # Phase91 output/checkpoint must be canonical-identical.
    check(
        phase91_output_digest == phase91_checkpoint_digest,
        "Phase91 output/checkpoint canonical digest mismatch",
    )

    evidence = {
        "phase": PHASE,
        "previous_phase": PREVIOUS_PHASE,
        "phase91_source_digest": source_digest,
        "phase89_continuity_digest": phase89_output.get(
            "continuity_digest"
        ),
        "phase90_finality_digest": phase90_output.get(
            "finality_digest"
        ),
        "phase89_output_canonical_digest": phase89_output_digest,
        "phase89_checkpoint_canonical_digest": phase89_checkpoint_digest,
        "phase90_output_canonical_digest": phase90_output_digest,
        "phase90_checkpoint_canonical_digest": phase90_checkpoint_digest,
        "phase91_output_canonical_digest": phase91_output_digest,
        "phase91_checkpoint_canonical_digest": phase91_checkpoint_digest,
        "state": "VERIFIED_READ_ONLY",
        "ready": True,
        "valid": True,
        "checkpoint": "VERIFIED",
        "error_count": 0,
        "executionAuthorized": False,
        "networkAccess": False,
        "walletPresent": False,
        "signingEnabled": False,
        "broadcastEnabled": False,
        "submissionEnabled": False,
    }

    cross_artifact_digest = canonical_digest(evidence)
    evidence["cross_artifact_digest"] = cross_artifact_digest

    OUT.mkdir(parents=True, exist_ok=True)

    output_path = (
        OUT /
        "phase92-evidence-chain-cross-artifact-verification-gate.json"
    )

    checkpoint_path = (
        OUT /
        "phase92-evidence-chain-cross-artifact-verification-gate-checkpoint.json"
    )

    payload = json.dumps(
        evidence,
        indent=2,
        sort_keys=True,
    ) + "\n"

    output_path.write_text(payload)
    checkpoint_path.write_text(payload)

    print("STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("PREVIOUS PHASE: 91")
    print(f"PHASE91 SOURCE DIGEST: {source_digest}")
    print(
        f"PHASE89 CONTINUITY DIGEST: "
        f"{phase89_output.get('continuity_digest')}"
    )
    print(
        f"PHASE90 FINALITY DIGEST: "
        f"{phase90_output.get('finality_digest')}"
    )
    print(
        f"PHASE89 OUTPUT CANONICAL DIGEST: "
        f"{phase89_output_digest}"
    )
    print(
        f"PHASE89 CHECKPOINT CANONICAL DIGEST: "
        f"{phase89_checkpoint_digest}"
    )
    print(
        f"PHASE90 OUTPUT CANONICAL DIGEST: "
        f"{phase90_output_digest}"
    )
    print(
        f"PHASE90 CHECKPOINT CANONICAL DIGEST: "
        f"{phase90_checkpoint_digest}"
    )
    print(
        f"PHASE91 OUTPUT CANONICAL DIGEST: "
        f"{phase91_output_digest}"
    )
    print(
        f"PHASE91 CHECKPOINT CANONICAL DIGEST: "
        f"{phase91_checkpoint_digest}"
    )
    print(f"CROSS ARTIFACT DIGEST: {cross_artifact_digest}")
    print("EXECUTION AUTHORIZED: False")
    print("NETWORK ACCESS: False")
    print("WALLET PRESENT: False")
    print("SIGNING ENABLED: False")
    print("BROADCAST ENABLED: False")
    print("SUBMISSION ENABLED: False")
    print("ERROR COUNT: 0")


if __name__ == "__main__":
    main()
