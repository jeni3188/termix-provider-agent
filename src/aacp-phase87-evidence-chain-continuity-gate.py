#!/usr/bin/env python3

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "provider-output" / "aacp-observer"
import os
import subprocess
import sys

PHASE = "87"
PREVIOUS_PHASE = "86"

EXPECTED_PHASE86_DIGEST = (
    "cfd0cd2c9f68c738d26c53b2d401f9264fc339708006ed4d70646d05a8136816"
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHASE86 = os.path.join(
    ROOT, "src", "aacp-phase86-attestation-integrity-gate.py"
)

EXECUTION_AUTHORIZED = False
NETWORK_ACCESS = False
WALLET_PRESENT = False
SIGNING_ENABLED = False
BROADCAST_ENABLED = False
SUBMISSION_ENABLED = False


def fail(message):
    print(f"ERROR: {message}")
    print("STATE: VERIFIED_READ_ONLY")
    print("READY: False")
    print("VALID: False")
    print("CHECKPOINT: FAILED")
    sys.exit(1)


def parse_phase86(output):
    values = {}

    for line in output.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()

    return values


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


if not os.path.isfile(PHASE86):
    fail("Phase86 source missing")

# Phase87 must remain strictly local/read-only.
if any([
    EXECUTION_AUTHORIZED,
    NETWORK_ACCESS,
    WALLET_PRESENT,
    SIGNING_ENABLED,
    BROADCAST_ENABLED,
    SUBMISSION_ENABLED,
]):
    fail("unsafe capability detected")

try:
    result = subprocess.run(
        [sys.executable, PHASE86],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
except Exception as exc:
    fail(f"Phase86 execution failed: {exc}")

if result.returncode != 0:
    fail("Phase86 returned non-zero status")

phase86 = parse_phase86(result.stdout)

if phase86.get("STATE") != "VERIFIED_READ_ONLY":
    fail("Phase86 state continuity failed")

if phase86.get("READY") != "True":
    fail("Phase86 readiness continuity failed")

if phase86.get("VALID") != "True":
    fail("Phase86 validity continuity failed")

if phase86.get("CHECKPOINT") != "VERIFIED":
    fail("Phase86 checkpoint continuity failed")

if phase86.get("ERROR COUNT") != "0":
    fail("Phase86 error-count continuity failed")

phase86_digest = phase86.get("INTEGRITY DIGEST", "")

if phase86_digest != EXPECTED_PHASE86_DIGEST:
    fail(
        "Phase86 integrity digest mismatch: "
        f"expected={EXPECTED_PHASE86_DIGEST} "
        f"actual={phase86_digest}"
    )

phase86_source_digest = sha256_file(PHASE86)

evidence = {
    "phase": PHASE,
    "previous_phase": PREVIOUS_PHASE,
    "previous_integrity_digest": phase86_digest,
    "previous_source_digest": phase86_source_digest,
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

canonical = json.dumps(
    evidence,
    sort_keys=True,
    separators=(",", ":"),
).encode()

continuity_digest = hashlib.sha256(canonical).hexdigest()

# ---------------------------------------------------------------------------
# PHASE87 ARTIFACT PERSISTENCE
# READ-ONLY / FAIL-CLOSED / NO NETWORK / NO WALLET / NO SIGNING / NO SUBMIT
# ---------------------------------------------------------------------------

OUT = Path(ROOT) / "provider-output" / "aacp-observer"
OUT.mkdir(parents=True, exist_ok=True)

evidence["continuity_digest"] = continuity_digest

checkpoint = {
    "phase": PHASE,
    "checkpoint": "VERIFIED",
    "state": "VERIFIED_READ_ONLY",
    "ready": True,
    "valid": True,
    "previous_phase": PREVIOUS_PHASE,
    "previous_integrity_digest": phase86_digest,
    "previous_source_digest": phase86_source_digest,
    "continuity_digest": continuity_digest,
    "error_count": 0,
    "executionAuthorized": False,
    "networkAccess": False,
    "walletPresent": False,
    "signingEnabled": False,
    "broadcastEnabled": False,
    "submissionEnabled": False,
}

(OUT / "phase87-evidence-chain-continuity-gate.json").write_text(
    json.dumps(evidence, indent=2, sort_keys=True) + "\n"
)

(
    OUT / "phase87-evidence-chain-continuity-gate-checkpoint.json"
).write_text(
    json.dumps(checkpoint, indent=2, sort_keys=True) + "\n"
)

print("STATE: VERIFIED_READ_ONLY")
print("READY: True")
print("VALID: True")
print("CHECKPOINT: VERIFIED")
print(f"PREVIOUS PHASE: {PREVIOUS_PHASE}")
print(f"PHASE86 INTEGRITY DIGEST: {phase86_digest}")
print(f"PHASE86 SOURCE DIGEST: {phase86_source_digest}")
print(f"CONTINUITY DIGEST: {continuity_digest}")
print("EXECUTION AUTHORIZED: False")
print("NETWORK ACCESS: False")
print("WALLET PRESENT: False")
print("SIGNING ENABLED: False")
print("BROADCAST ENABLED: False")
print("SUBMISSION ENABLED: False")
print("ERROR COUNT: 0")
