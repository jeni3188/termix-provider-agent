#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path


PHASE = 95
PREVIOUS_PHASE = 94

BASE = Path(__file__).resolve().parent.parent
OBSERVER = BASE / "provider-output" / "aacp-observer"

PHASE94_SOURCE = (
    BASE
    / "src"
    / "aacp-phase94-evidence-snapshot-continuity-terminal-anchor-gate.py"
)

PHASE94_OUTPUT = (
    OBSERVER
    / "phase94-evidence-snapshot-continuity-terminal-anchor-gate.json"
)

PHASE94_CHECKPOINT = (
    OBSERVER
    / "phase94-evidence-snapshot-continuity-terminal-anchor-gate-checkpoint.json"
)

OUTPUT = (
    OBSERVER
    / "phase95-evidence-chain-terminal-finality-gate.json"
)

CHECKPOINT = (
    OBSERVER
    / "phase95-evidence-chain-terminal-finality-gate-checkpoint.json"
)

EXPECTED_PHASE94_SOURCE_DIGEST = (
    "aee0ed86dd187d33171efe5eaa9389a70fbe348d91ba25f22f29857075bf3950"
)

EXPECTED_PHASE94_TERMINAL_ANCHOR_DIGEST = (
    "b5cb7868a45421e99bbec2da35747a01d05e842ce6ca730f4b4bbbd2dfa9a7f8"
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


phase94_output = validate_artifact(
    PHASE94_OUTPUT,
    "Phase94 output",
)

phase94_checkpoint = validate_artifact(
    PHASE94_CHECKPOINT,
    "Phase94 checkpoint",
)

require(
    PHASE94_SOURCE.is_file(),
    "Phase94 source missing",
)

actual_phase94_source_digest = None

if PHASE94_SOURCE.is_file():
    actual_phase94_source_digest = sha256_file(PHASE94_SOURCE)

require(
    actual_phase94_source_digest == EXPECTED_PHASE94_SOURCE_DIGEST,
    "Phase94 source digest mismatch",
)


if phase94_output is not None:
    require(
        phase94_output.get("phase") == 94,
        "Phase94 output phase mismatch",
    )

    require(
        phase94_output.get("previous_phase") == 93,
        "Phase94 output previous_phase mismatch",
    )

    require(
        phase94_output.get("state") == "VERIFIED_READ_ONLY",
        "Phase94 output state mismatch",
    )

    require(
        phase94_output.get("ready") is True,
        "Phase94 output ready mismatch",
    )

    require(
        phase94_output.get("valid") is True,
        "Phase94 output valid mismatch",
    )

    require(
        phase94_output.get("checkpoint") == "VERIFIED",
        "Phase94 output checkpoint status mismatch",
    )

    require(
        phase94_output.get("error_count") == 0,
        "Phase94 output error_count mismatch",
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
            phase94_output.get(flag) is False,
            f"Phase94 safety flag {flag} is not false",
        )

    require(
        phase94_output.get("phase93_source_digest")
        == (
            "067dc6ba5c3e219c28594290f3ab233adb2ecfcd2292c8ec0428436bef25d5cd"
        ),
        "Phase94 Phase93 source anchor mismatch",
    )

    require(
        isinstance(
            phase94_output.get("terminal_anchor_digest"),
            str,
        )
        and len(phase94_output["terminal_anchor_digest"]) == 64,
        "Phase94 terminal anchor digest invalid",
    )

    require(
        phase94_output.get("terminal_anchor_digest")
        == EXPECTED_PHASE94_TERMINAL_ANCHOR_DIGEST,
        "Phase94 terminal anchor digest mismatch",
    )


if phase94_checkpoint is not None:
    require(
        phase94_checkpoint.get("phase") == 94,
        "Phase94 checkpoint phase mismatch",
    )

    require(
        phase94_checkpoint.get("previous_phase") == 93,
        "Phase94 checkpoint previous_phase mismatch",
    )

    require(
        phase94_checkpoint.get("state") == "VERIFIED_READ_ONLY",
        "Phase94 checkpoint state mismatch",
    )

    require(
        phase94_checkpoint.get("ready") is True,
        "Phase94 checkpoint ready mismatch",
    )

    require(
        phase94_checkpoint.get("valid") is True,
        "Phase94 checkpoint valid mismatch",
    )

    require(
        phase94_checkpoint.get("checkpoint") == "VERIFIED",
        "Phase94 checkpoint status mismatch",
    )

    require(
        phase94_checkpoint.get("error_count") == 0,
        "Phase94 checkpoint error_count mismatch",
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
            phase94_checkpoint.get(flag) is False,
            f"Phase94 checkpoint safety flag {flag} is not false",
        )

    require(
        phase94_checkpoint.get("terminal_anchor_digest")
        == EXPECTED_PHASE94_TERMINAL_ANCHOR_DIGEST,
        "Phase94 checkpoint terminal anchor mismatch",
    )


if phase94_output is not None and phase94_checkpoint is not None:
    output_digest = canonical_digest(phase94_output)
    checkpoint_digest = canonical_digest(phase94_checkpoint)

    require(
        output_digest == checkpoint_digest,
        "Phase94 output/checkpoint canonical digest mismatch",
    )

    require(
        phase94_output.get("terminal_anchor_digest")
        == phase94_checkpoint.get("terminal_anchor_digest"),
        "Phase94 terminal anchor cross-artifact mismatch",
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


phase94_output_digest = canonical_digest(phase94_output)
phase94_checkpoint_digest = canonical_digest(phase94_checkpoint)

terminal_finality_payload = {
    "phase": PHASE,
    "previous_phase": PREVIOUS_PHASE,
    "state": "VERIFIED_READ_ONLY",
    "ready": True,
    "valid": True,
    "checkpoint": "VERIFIED",
    "phase94_source_digest": actual_phase94_source_digest,
    "phase94_output_canonical_digest": phase94_output_digest,
    "phase94_checkpoint_canonical_digest": phase94_checkpoint_digest,
    "phase94_terminal_anchor_digest": (
        phase94_output["terminal_anchor_digest"]
    ),
    "executionAuthorized": False,
    "networkAccess": False,
    "walletPresent": False,
    "signingEnabled": False,
    "broadcastEnabled": False,
    "submissionEnabled": False,
    "error_count": 0,
}

terminal_finality_digest = canonical_digest(
    terminal_finality_payload
)

terminal_finality_payload["terminal_finality_digest"] = (
    terminal_finality_digest
)


with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(
        terminal_finality_payload,
        f,
        indent=2,
        sort_keys=True,
    )
    f.write("\n")


with open(CHECKPOINT, "w", encoding="utf-8") as f:
    json.dump(
        terminal_finality_payload,
        f,
        indent=2,
        sort_keys=True,
    )
    f.write("\n")


print("STATE: VERIFIED_READ_ONLY")
print("READY: True")
print("VALID: True")
print("CHECKPOINT: VERIFIED")
print("PREVIOUS PHASE: 94")
print(f"PHASE94 SOURCE DIGEST: {actual_phase94_source_digest}")
print(
    f"PHASE94 OUTPUT CANONICAL DIGEST: "
    f"{phase94_output_digest}"
)
print(
    f"PHASE94 CHECKPOINT CANONICAL DIGEST: "
    f"{phase94_checkpoint_digest}"
)
print(
    f"PHASE94 TERMINAL ANCHOR DIGEST: "
    f"{phase94_output['terminal_anchor_digest']}"
)
print(
    f"TERMINAL FINALITY DIGEST: "
    f"{terminal_finality_digest}"
)
print("EXECUTION AUTHORIZED: False")
print("NETWORK ACCESS: False")
print("WALLET PRESENT: False")
print("SIGNING ENABLED: False")
print("BROADCAST ENABLED: False")
print("SUBMISSION ENABLED: False")
print("ERROR COUNT: 0")
