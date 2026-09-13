#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path

PHASE = 96
PREVIOUS_PHASE = 95

BASE = Path(__file__).resolve().parent.parent
OBSERVER = BASE / "provider-output" / "aacp-observer"

PHASE95_SOURCE = (
    BASE
    / "src"
    / "aacp-phase95-evidence-chain-terminal-finality-gate.py"
)

PHASE95_OUTPUT = (
    OBSERVER
    / "phase95-evidence-chain-terminal-finality-gate.json"
)

PHASE95_CHECKPOINT = (
    OBSERVER
    / "phase95-evidence-chain-terminal-finality-gate-checkpoint.json"
)

OUTPUT = (
    OBSERVER
    / "phase96-post-finality-verification-gate.json"
)

CHECKPOINT = (
    OBSERVER
    / "phase96-post-finality-verification-gate-checkpoint.json"
)

EXPECTED_PHASE95_SOURCE_DIGEST = (
    "ebe3dffdfd5abc1a3b7410bcaa2faa1c022e4a15b97faef5da2967646cd8b372"
)

EXPECTED_PHASE95_TERMINAL_FINALITY_DIGEST = (
    "b5927dc10dccad322dbfb39dd21e34e9deb00f64e533742aee3b3d74f85f9470"
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


phase95_output = validate_artifact(
    PHASE95_OUTPUT,
    "Phase95 output",
)

phase95_checkpoint = validate_artifact(
    PHASE95_CHECKPOINT,
    "Phase95 checkpoint",
)

require(
    PHASE95_SOURCE.is_file(),
    "Phase95 source missing",
)

actual_phase95_source_digest = None

if PHASE95_SOURCE.is_file():
    actual_phase95_source_digest = sha256_file(PHASE95_SOURCE)

require(
    actual_phase95_source_digest == EXPECTED_PHASE95_SOURCE_DIGEST,
    "Phase95 source digest mismatch",
)


if phase95_output is not None:
    require(
        phase95_output.get("phase") == 95,
        "Phase95 output phase mismatch",
    )

    require(
        phase95_output.get("previous_phase") == 94,
        "Phase95 output previous_phase mismatch",
    )

    require(
        phase95_output.get("state") == "VERIFIED_READ_ONLY",
        "Phase95 output state mismatch",
    )

    require(
        phase95_output.get("ready") is True,
        "Phase95 output ready mismatch",
    )

    require(
        phase95_output.get("valid") is True,
        "Phase95 output valid mismatch",
    )

    require(
        phase95_output.get("checkpoint") == "VERIFIED",
        "Phase95 output checkpoint status mismatch",
    )

    require(
        phase95_output.get("error_count") == 0,
        "Phase95 output error_count mismatch",
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
            phase95_output.get(flag) is False,
            f"Phase95 safety flag {flag} is not false",
        )

    require(
        phase95_output.get("phase94_source_digest")
        == (
            "aee0ed86dd187d33171efe5eaa9389a70fbe348d91ba25f22f29857075bf3950"
        ),
        "Phase95 Phase94 source anchor mismatch",
    )

    require(
        phase95_output.get("phase94_terminal_anchor_digest")
        == (
            "b5cb7868a45421e99bbec2da35747a01d05e842ce6ca730f4b4bbbd2dfa9a7f8"
        ),
        "Phase95 Phase94 terminal anchor mismatch",
    )

    require(
        isinstance(
            phase95_output.get("terminal_finality_digest"),
            str,
        )
        and len(phase95_output["terminal_finality_digest"]) == 64,
        "Phase95 terminal finality digest invalid",
    )

    require(
        phase95_output.get("terminal_finality_digest")
        == EXPECTED_PHASE95_TERMINAL_FINALITY_DIGEST,
        "Phase95 terminal finality digest anchor mismatch",
    )


if phase95_checkpoint is not None:
    require(
        phase95_checkpoint.get("phase") == 95,
        "Phase95 checkpoint phase mismatch",
    )

    require(
        phase95_checkpoint.get("previous_phase") == 94,
        "Phase95 checkpoint previous_phase mismatch",
    )

    require(
        phase95_checkpoint.get("state") == "VERIFIED_READ_ONLY",
        "Phase95 checkpoint state mismatch",
    )

    require(
        phase95_checkpoint.get("ready") is True,
        "Phase95 checkpoint ready mismatch",
    )

    require(
        phase95_checkpoint.get("valid") is True,
        "Phase95 checkpoint valid mismatch",
    )

    require(
        phase95_checkpoint.get("checkpoint") == "VERIFIED",
        "Phase95 checkpoint status mismatch",
    )

    require(
        phase95_checkpoint.get("error_count") == 0,
        "Phase95 checkpoint error_count mismatch",
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
            phase95_checkpoint.get(flag) is False,
            f"Phase95 checkpoint safety flag {flag} is not false",
        )

    require(
        phase95_checkpoint.get("terminal_finality_digest")
        == EXPECTED_PHASE95_TERMINAL_FINALITY_DIGEST,
        "Phase95 checkpoint terminal finality mismatch",
    )


if phase95_output is not None and phase95_checkpoint is not None:
    output_digest = canonical_digest(phase95_output)
    checkpoint_digest = canonical_digest(phase95_checkpoint)

    require(
        output_digest == checkpoint_digest,
        "Phase95 output/checkpoint canonical digest mismatch",
    )

    require(
        phase95_output == phase95_checkpoint,
        "Phase95 output/checkpoint semantic mismatch",
    )


if not errors:
    phase95_payload_without_digest = dict(phase95_output)
    phase95_payload_without_digest.pop("terminal_finality_digest", None)

    recomputed_terminal_finality_digest = canonical_digest(
        phase95_payload_without_digest
    )

    require(
        recomputed_terminal_finality_digest
        == EXPECTED_PHASE95_TERMINAL_FINALITY_DIGEST,
        "Phase95 terminal finality recomputation mismatch",
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


phase95_output_digest = canonical_digest(phase95_output)
phase95_checkpoint_digest = canonical_digest(phase95_checkpoint)

post_finality_payload = {
    "phase": PHASE,
    "previous_phase": PREVIOUS_PHASE,
    "state": "VERIFIED_READ_ONLY",
    "ready": True,
    "valid": True,
    "checkpoint": "VERIFIED",
    "phase95_source_digest": actual_phase95_source_digest,
    "phase95_output_canonical_digest": phase95_output_digest,
    "phase95_checkpoint_canonical_digest": phase95_checkpoint_digest,
    "phase95_terminal_finality_digest": (
        phase95_output["terminal_finality_digest"]
    ),
    "executionAuthorized": False,
    "networkAccess": False,
    "walletPresent": False,
    "signingEnabled": False,
    "broadcastEnabled": False,
    "submissionEnabled": False,
    "error_count": 0,
}

post_finality_verification_digest = canonical_digest(
    post_finality_payload
)

post_finality_payload["post_finality_verification_digest"] = (
    post_finality_verification_digest
)


for path in (OUTPUT, CHECKPOINT):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            post_finality_payload,
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")


print("STATE: VERIFIED_READ_ONLY")
print("READY: True")
print("VALID: True")
print("CHECKPOINT: VERIFIED")
print("PREVIOUS PHASE: 95")
print(f"PHASE95 SOURCE DIGEST: {actual_phase95_source_digest}")
print(
    f"PHASE95 OUTPUT CANONICAL DIGEST: "
    f"{phase95_output_digest}"
)
print(
    f"PHASE95 CHECKPOINT CANONICAL DIGEST: "
    f"{phase95_checkpoint_digest}"
)
print(
    f"PHASE95 TERMINAL FINALITY DIGEST: "
    f"{phase95_output['terminal_finality_digest']}"
)
print(
    f"POST-FINALITY VERIFICATION DIGEST: "
    f"{post_finality_verification_digest}"
)
print("EXECUTION AUTHORIZED: False")
print("NETWORK ACCESS: False")
print("WALLET PRESENT: False")
print("SIGNING ENABLED: False")
print("BROADCAST ENABLED: False")
print("SUBMISSION ENABLED: False")
print("ERROR COUNT: 0")
