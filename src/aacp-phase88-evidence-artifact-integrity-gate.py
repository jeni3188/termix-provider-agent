#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "provider-output" / "aacp-observer"

PHASE = 88
PREVIOUS_PHASE = 87

PHASE87_OUTPUT = (
    OUT / "phase87-evidence-chain-continuity-gate.json"
)

PHASE87_CHECKPOINT = (
    OUT / "phase87-evidence-chain-continuity-gate-checkpoint.json"
)


def fail(message):
    print(f"STATE: REJECTED_READ_ONLY")
    print("READY: False")
    print("VALID: False")
    print("CHECKPOINT: REJECTED")
    print(f"ERROR: {message}")
    sys.exit(1)


def load_json(path):
    if not path.exists():
        fail(f"missing artifact: {path}")

    try:
        return json.loads(path.read_text())
    except Exception as exc:
        fail(f"invalid JSON: {path}: {exc}")


def canonical_digest(obj):
    canonical = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


output = load_json(PHASE87_OUTPUT)
checkpoint = load_json(PHASE87_CHECKPOINT)

errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


check(
    str(output.get("phase")) == str(PREVIOUS_PHASE),
    "Phase87 output phase mismatch",
)
check(
    str(checkpoint.get("phase")) == str(PREVIOUS_PHASE),
    "Phase87 checkpoint phase mismatch",
)

check(
    output.get("state") == "VERIFIED_READ_ONLY",
    "Phase87 output state mismatch",
)

check(
    checkpoint.get("state") == "VERIFIED_READ_ONLY",
    "Phase87 checkpoint state mismatch",
)

check(output.get("ready") is True, "Phase87 output readiness mismatch")
check(checkpoint.get("ready") is True, "Phase87 checkpoint readiness mismatch")

check(output.get("valid") is True, "Phase87 output validity mismatch")
check(checkpoint.get("valid") is True, "Phase87 checkpoint validity mismatch")

check(
    checkpoint.get("checkpoint") == "VERIFIED",
    "Phase87 checkpoint status mismatch",
)

check(output.get("error_count") == 0, "Phase87 output error count mismatch")
check(
    checkpoint.get("error_count") == 0,
    "Phase87 checkpoint error count mismatch",
)

SAFETY_FIELDS = (
    "executionAuthorized",
    "networkAccess",
    "walletPresent",
    "signingEnabled",
    "broadcastEnabled",
    "submissionEnabled",
)

for field in SAFETY_FIELDS:
    check(
        output.get(field) is False,
        f"Phase87 output safety violation: {field}",
    )
    check(
        checkpoint.get(field) is False,
        f"Phase87 checkpoint safety violation: {field}",
    )

output_digest = output.get("continuity_digest", "")
checkpoint_digest = checkpoint.get("continuity_digest", "")

check(
    bool(output_digest),
    "Phase87 output continuity digest missing",
)

check(
    bool(checkpoint_digest),
    "Phase87 checkpoint continuity digest missing",
)

check(
    output_digest == checkpoint_digest,
    "Phase87 continuity digest mismatch",
)

expected_output_digest = canonical_digest(
    {
        key: value
        for key, value in output.items()
        if key != "continuity_digest"
    }
)

expected_checkpoint_digest = canonical_digest(
    {
        key: value
        for key, value in checkpoint.items()
        if key != "continuity_digest"
    }
)

artifact_digest = canonical_digest(
    {
        "phase": PREVIOUS_PHASE,
        "output_continuity_digest": output_digest,
        "checkpoint_continuity_digest": checkpoint_digest,
        "output_canonical_digest": expected_output_digest,
        "checkpoint_canonical_digest": expected_checkpoint_digest,
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
)

if errors:
    fail("; ".join(errors))

result = {
    "phase": PHASE,
    "previous_phase": PREVIOUS_PHASE,
    "state": "VERIFIED_READ_ONLY",
    "ready": True,
    "valid": True,
    "checkpoint": "VERIFIED",
    "error_count": 0,
    "phase87_continuity_digest": output_digest,
    "phase87_output_canonical_digest": expected_output_digest,
    "phase87_checkpoint_canonical_digest": expected_checkpoint_digest,
    "artifact_integrity_digest": artifact_digest,
    "executionAuthorized": False,
    "networkAccess": False,
    "walletPresent": False,
    "signingEnabled": False,
    "broadcastEnabled": False,
    "submissionEnabled": False,
}

checkpoint_result = {
    "phase": PHASE,
    "previous_phase": PREVIOUS_PHASE,
    "checkpoint": "VERIFIED",
    "state": "VERIFIED_READ_ONLY",
    "ready": True,
    "valid": True,
    "error_count": 0,
    "phase87_continuity_digest": output_digest,
    "artifact_integrity_digest": artifact_digest,
    "executionAuthorized": False,
    "networkAccess": False,
    "walletPresent": False,
    "signingEnabled": False,
    "broadcastEnabled": False,
    "submissionEnabled": False,
}

OUT.mkdir(parents=True, exist_ok=True)

(
    OUT / "phase88-evidence-artifact-integrity-gate.json"
).write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n"
)

(
    OUT / "phase88-evidence-artifact-integrity-gate-checkpoint.json"
).write_text(
    json.dumps(checkpoint_result, indent=2, sort_keys=True) + "\n"
)

print("STATE: VERIFIED_READ_ONLY")
print("READY: True")
print("VALID: True")
print("CHECKPOINT: VERIFIED")
print(f"PREVIOUS PHASE: {PREVIOUS_PHASE}")
print(f"PHASE87 CONTINUITY DIGEST: {output_digest}")
print(f"PHASE87 OUTPUT CANONICAL DIGEST: {expected_output_digest}")
print(f"PHASE87 CHECKPOINT CANONICAL DIGEST: {expected_checkpoint_digest}")
print(f"ARTIFACT INTEGRITY DIGEST: {artifact_digest}")
print("EXECUTION AUTHORIZED: False")
print("NETWORK ACCESS: False")
print("WALLET PRESENT: False")
print("SIGNING ENABLED: False")
print("BROADCAST ENABLED: False")
print("SUBMISSION ENABLED: False")
print("ERROR COUNT: 0")
