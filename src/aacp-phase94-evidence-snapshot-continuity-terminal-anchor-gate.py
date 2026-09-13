#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path


PHASE = 94
PREVIOUS_PHASE = 93

BASE = Path(__file__).resolve().parent.parent
OBSERVER = BASE / "provider-output" / "aacp-observer"

PHASE93_SOURCE = (
    BASE
    / "src"
    / "aacp-phase93-terminal-evidence-snapshot-integrity-gate.py"
)

PHASE93_OUTPUT = (
    OBSERVER
    / "phase93-terminal-evidence-snapshot-integrity-gate.json"
)

PHASE93_CHECKPOINT = (
    OBSERVER
    / "phase93-terminal-evidence-snapshot-integrity-gate-checkpoint.json"
)

OUTPUT = (
    OBSERVER
    / "phase94-evidence-snapshot-continuity-terminal-anchor-gate.json"
)

CHECKPOINT = (
    OBSERVER
    / "phase94-evidence-snapshot-continuity-terminal-anchor-gate-checkpoint.json"
)

EXPECTED_PHASE93_SOURCE_DIGEST = (
    "067dc6ba5c3e219c28594290f3ab233adb2ecfcd2292c8ec0428436bef25d5cd"
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


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


errors = []


def require(condition, message):
    if not condition:
        errors.append(message)


def validate_artifact(path, label):
    require(path.is_file(), f"{label} missing: {path}")
    if not path.is_file():
        return None

    try:
        return load_json(path)
    except Exception as exc:
        errors.append(f"{label} invalid JSON: {exc}")
        return None


phase93_output = validate_artifact(PHASE93_OUTPUT, "Phase93 output")
phase93_checkpoint = validate_artifact(PHASE93_CHECKPOINT, "Phase93 checkpoint")

require(PHASE93_SOURCE.is_file(), "Phase93 source missing")

actual_phase93_source_digest = None
if PHASE93_SOURCE.is_file():
    actual_phase93_source_digest = sha256_file(PHASE93_SOURCE)

require(
    actual_phase93_source_digest == EXPECTED_PHASE93_SOURCE_DIGEST,
    "Phase93 source digest mismatch",
)

if phase93_output is not None:
    require(phase93_output.get("phase") == 93, "Phase93 output phase mismatch")
    require(
        phase93_output.get("previous_phase") == 92,
        "Phase93 previous_phase mismatch",
    )
    require(
        phase93_output.get("state") == "VERIFIED_READ_ONLY",
        "Phase93 state mismatch",
    )
    require(phase93_output.get("ready") is True, "Phase93 ready mismatch")
    require(phase93_output.get("valid") is True, "Phase93 valid mismatch")
    require(
        phase93_output.get("checkpoint") == "VERIFIED",
        "Phase93 checkpoint status mismatch",
    )
    require(
        phase93_output.get("error_count") == 0,
        "Phase93 error_count mismatch",
    )

    for flag in (
        "executionAuthorized",
        "networkAccess",
        "walletPresent",
        "signingEnabled",
        "broadcastEnabled",
        "submissionEnabled",
    ):
        require(
            phase93_output.get(flag) is False,
            f"Phase93 safety flag {flag} is not false",
        )

    require(
        isinstance(
            phase93_output.get("terminal_snapshot_digest"),
            str,
        )
        and len(phase93_output["terminal_snapshot_digest"]) == 64,
        "Phase93 terminal snapshot digest invalid",
    )

if phase93_checkpoint is not None:
    require(
        phase93_checkpoint.get("phase") == 93,
        "Phase93 checkpoint phase mismatch",
    )
    require(
        phase93_checkpoint.get("previous_phase") == 92,
        "Phase93 checkpoint previous_phase mismatch",
    )
    require(
        phase93_checkpoint.get("state") == "VERIFIED_READ_ONLY",
        "Phase93 checkpoint state mismatch",
    )
    require(
        phase93_checkpoint.get("ready") is True,
        "Phase93 checkpoint ready mismatch",
    )
    require(
        phase93_checkpoint.get("valid") is True,
        "Phase93 checkpoint valid mismatch",
    )
    require(
        phase93_checkpoint.get("checkpoint") == "VERIFIED",
        "Phase93 checkpoint status mismatch",
    )
    require(
        phase93_checkpoint.get("error_count") == 0,
        "Phase93 checkpoint error_count mismatch",
    )

    for flag in (
        "executionAuthorized",
        "networkAccess",
        "walletPresent",
        "signingEnabled",
        "broadcastEnabled",
        "submissionEnabled",
    ):
        require(
            phase93_checkpoint.get(flag) is False,
            f"Phase93 checkpoint safety flag {flag} is not false",
        )

if phase93_output is not None and phase93_checkpoint is not None:
    output_digest = canonical_digest(phase93_output)
    checkpoint_digest = canonical_digest(phase93_checkpoint)

    require(
        output_digest == checkpoint_digest,
        "Phase93 output/checkpoint canonical digest mismatch",
    )

    require(
        phase93_output.get("terminal_snapshot_digest")
        == phase93_checkpoint.get("terminal_snapshot_digest"),
        "Phase93 terminal snapshot digest mismatch",
    )

    require(
        phase93_output.get("phase92_source_digest")
        == phase93_checkpoint.get("phase92_source_digest"),
        "Phase93 Phase92 source anchor mismatch",
    )

    require(
        phase93_output.get("phase92_cross_artifact_digest")
        == phase93_checkpoint.get("phase92_cross_artifact_digest"),
        "Phase93 Phase92 cross-artifact anchor mismatch",
    )


if errors:
    print("STATE: REJECTED_READ_ONLY")
    print("READY: False")
    print("VALID: False")
    print("CHECKPOINT: REJECTED")
    print(f"ERROR COUNT: {len(errors)}")
    for error in errors:
        print(f"ERROR: {error}")
    sys.exit(1)


phase93_output_digest = canonical_digest(phase93_output)
phase93_checkpoint_digest = canonical_digest(phase93_checkpoint)
phase93_terminal_snapshot_digest = phase93_output["terminal_snapshot_digest"]

anchor_payload = {
    "phase": PHASE,
    "previous_phase": PREVIOUS_PHASE,
    "state": "VERIFIED_READ_ONLY",
    "ready": True,
    "valid": True,
    "checkpoint": "VERIFIED",
    "phase93_source_digest": actual_phase93_source_digest,
    "phase93_output_canonical_digest": phase93_output_digest,
    "phase93_checkpoint_canonical_digest": phase93_checkpoint_digest,
    "phase93_terminal_snapshot_digest": phase93_terminal_snapshot_digest,
    "executionAuthorized": False,
    "networkAccess": False,
    "walletPresent": False,
    "signingEnabled": False,
    "broadcastEnabled": False,
    "submissionEnabled": False,
    "error_count": 0,
}

terminal_anchor_digest = canonical_digest(anchor_payload)
anchor_payload["terminal_anchor_digest"] = terminal_anchor_digest


with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(anchor_payload, f, indent=2, sort_keys=True)
    f.write("\n")

with open(CHECKPOINT, "w", encoding="utf-8") as f:
    json.dump(anchor_payload, f, indent=2, sort_keys=True)
    f.write("\n")


print("STATE: VERIFIED_READ_ONLY")
print("READY: True")
print("VALID: True")
print("CHECKPOINT: VERIFIED")
print("PREVIOUS PHASE: 93")
print(f"PHASE93 SOURCE DIGEST: {actual_phase93_source_digest}")
print(f"PHASE93 OUTPUT CANONICAL DIGEST: {phase93_output_digest}")
print(f"PHASE93 CHECKPOINT CANONICAL DIGEST: {phase93_checkpoint_digest}")
print(f"PHASE93 TERMINAL SNAPSHOT DIGEST: {phase93_terminal_snapshot_digest}")
print(f"TERMINAL ANCHOR DIGEST: {terminal_anchor_digest}")
print("EXECUTION AUTHORIZED: False")
print("NETWORK ACCESS: False")
print("WALLET PRESENT: False")
print("SIGNING ENABLED: False")
print("BROADCAST ENABLED: False")
print("SUBMISSION ENABLED: False")
print("ERROR COUNT: 0")
