#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path


PHASE = 93
PREVIOUS_PHASE = 92

BASE = Path(__file__).resolve().parent.parent
OBSERVER = BASE / "provider-output" / "aacp-observer"

PHASE92_SOURCE = (
    BASE
    / "src"
    / "aacp-phase92-evidence-chain-cross-artifact-verification-gate.py"
)

PHASE92_OUTPUT = (
    OBSERVER
    / "phase92-evidence-chain-cross-artifact-verification-gate.json"
)

PHASE92_CHECKPOINT = (
    OBSERVER
    / "phase92-evidence-chain-cross-artifact-verification-gate-checkpoint.json"
)

OUTPUT = (
    OBSERVER
    / "phase93-terminal-evidence-snapshot-integrity-gate.json"
)

CHECKPOINT = (
    OBSERVER
    / "phase93-terminal-evidence-snapshot-integrity-gate-checkpoint.json"
)

EXPECTED_PHASE92_SOURCE_DIGEST = (
    "4ffc336aa24672a2e5908ba66f28b019ad31ac4f3f26e9f3594a31dd06f4b40c"
)

SAFETY_FLAGS = (
    "executionAuthorized",
    "networkAccess",
    "walletPresent",
    "signingEnabled",
    "broadcastEnabled",
    "submissionEnabled",
)


def canonical_digest(value):
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


def load_json(path, label):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        errors.append(f"{label} load failure: {exc}")
        return {}


if not PHASE92_SOURCE.is_file():
    errors.append("Phase92 source missing")

if not PHASE92_OUTPUT.is_file():
    errors.append("Phase92 output missing")

if not PHASE92_CHECKPOINT.is_file():
    errors.append("Phase92 checkpoint missing")

if not errors:
    phase92_source_digest = sha256_file(PHASE92_SOURCE)

    phase92_output = load_json(
        PHASE92_OUTPUT,
        "Phase92 output",
    )

    phase92_checkpoint = load_json(
        PHASE92_CHECKPOINT,
        "Phase92 checkpoint",
    )

    check(
        phase92_source_digest == EXPECTED_PHASE92_SOURCE_DIGEST,
        "Phase92 source digest mismatch",
    )

    for artifact, label in (
        (phase92_output, "Phase92 output"),
        (phase92_checkpoint, "Phase92 checkpoint"),
    ):
        check(
            str(artifact.get("phase")) == "92",
            f"{label} phase mismatch",
        )

        check(
            str(artifact.get("previous_phase")) == "91",
            f"{label} previous_phase mismatch",
        )

        check(
            artifact.get("state") == "VERIFIED_READ_ONLY",
            f"{label} state mismatch",
        )

        check(
            artifact.get("ready") is True,
            f"{label} ready mismatch",
        )

        check(
            artifact.get("valid") is True,
            f"{label} valid mismatch",
        )

        check(
            artifact.get("checkpoint") == "VERIFIED",
            f"{label} checkpoint mismatch",
        )

        check(
            artifact.get("error_count") == 0,
            f"{label} error_count mismatch",
        )

        for flag in SAFETY_FLAGS:
            check(
                artifact.get(flag) is False,
                f"{label} {flag} must be false",
            )

    output_digest = canonical_digest(phase92_output)
    checkpoint_digest = canonical_digest(phase92_checkpoint)

    check(
        output_digest == checkpoint_digest,
        "Phase92 output/checkpoint canonical digest mismatch",
    )

    cross_artifact_digest = phase92_output.get(
        "cross_artifact_digest"
    )

    check(
        isinstance(cross_artifact_digest, str)
        and len(cross_artifact_digest) == 64,
        "Phase92 cross_artifact_digest invalid",
    )

    check(
        phase92_checkpoint.get("cross_artifact_digest")
        == cross_artifact_digest,
        "Phase92 checkpoint cross_artifact_digest mismatch",
    )

    snapshot = {
        "phase": PHASE,
        "previous_phase": PREVIOUS_PHASE,
        "state": "VERIFIED_READ_ONLY",
        "ready": True,
        "valid": True,
        "checkpoint": "VERIFIED",
        "previous_source_digest": EXPECTED_PHASE92_SOURCE_DIGEST,
        "phase92_source_digest": phase92_source_digest,
        "phase92_output_canonical_digest": output_digest,
        "phase92_checkpoint_canonical_digest": checkpoint_digest,
        "phase92_cross_artifact_digest": cross_artifact_digest,
        "executionAuthorized": False,
        "networkAccess": False,
        "walletPresent": False,
        "signingEnabled": False,
        "broadcastEnabled": False,
        "submissionEnabled": False,
        "error_count": 0,
    }

    terminal_snapshot_digest = canonical_digest(snapshot)

    snapshot["terminal_snapshot_digest"] = terminal_snapshot_digest

    if errors:
        state = {
            "state": "REJECTED_READ_ONLY",
            "ready": False,
            "valid": False,
            "checkpoint": "REJECTED",
            "error_count": len(errors),
            "errors": errors,
        }

        print("STATE: REJECTED_READ_ONLY")
        print("READY: False")
        print("VALID: False")
        print("CHECKPOINT: REJECTED")

        for error in errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    for path in (OUTPUT, CHECKPOINT):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, sort_keys=True)
            f.write("\n")

    print("STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("PREVIOUS PHASE: 92")
    print(f"PHASE92 SOURCE DIGEST: {phase92_source_digest}")
    print(f"PHASE92 OUTPUT CANONICAL DIGEST: {output_digest}")
    print(f"PHASE92 CHECKPOINT CANONICAL DIGEST: {checkpoint_digest}")
    print(f"PHASE92 CROSS ARTIFACT DIGEST: {cross_artifact_digest}")
    print(f"TERMINAL SNAPSHOT DIGEST: {terminal_snapshot_digest}")
    print("EXECUTION AUTHORIZED: False")
    print("NETWORK ACCESS: False")
    print("WALLET PRESENT: False")
    print("SIGNING ENABLED: False")
    print("BROADCAST ENABLED: False")
    print("SUBMISSION ENABLED: False")
    print("ERROR COUNT: 0")
