#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "provider-output" / "aacp-observer"

PHASE97_SOURCE = SRC / "aacp-phase97-full-chain-integrity-gate.py"
PHASE97_OUTPUT = OUT / "phase97-full-chain-integrity-gate.json"
PHASE97_CHECKPOINT = OUT / "phase97-full-chain-integrity-gate-checkpoint.json"

OUTPUT = OUT / "phase98-terminal-manifest-gate.json"
CHECKPOINT = OUT / "phase98-terminal-manifest-gate-checkpoint.json"

EXPECTED_PHASE97_SOURCE = (
    "77b270b467e3bef47e8dde9d82d785afb1a2934601c8d0764fda16145f1d54ae"
)

EXPECTED_PHASE97_FULL_CHAIN = (
    "57f85081af9b8e592a961ec66c6bf387fc7098cf2a00296b1e167f217e5f4d74"
)


def fail(message):
    print(f"ERROR: {message}")
    print("STATE: REJECTED_READ_ONLY")
    print("READY: False")
    print("VALID: False")
    sys.exit(1)


def canonical_digest(obj):
    payload = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def load_json(path):
    if not path.exists():
        fail(f"missing artifact: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        fail(f"invalid JSON {path}: {exc}")


def source_digest(path):
    if not path.exists():
        fail(f"missing source: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        fail(message)


def main():
    require(not False, "internal gate failure")

    phase97_source_digest = source_digest(PHASE97_SOURCE)
    require(
        phase97_source_digest == EXPECTED_PHASE97_SOURCE,
        "Phase97 source digest mismatch",
    )

    output = load_json(PHASE97_OUTPUT)
    checkpoint = load_json(PHASE97_CHECKPOINT)

    require(output == checkpoint, "Phase97 output/checkpoint mismatch")

    require(
        output.get("state") == "VERIFIED_READ_ONLY",
        "Phase97 state mismatch",
    )
    require(output.get("ready") is True, "Phase97 ready flag mismatch")
    require(output.get("valid") is True, "Phase97 valid flag mismatch")
    require(
        output.get("executionAuthorized") is False,
        "execution authorization must be false",
    )
    require(
        output.get("networkAccess") is False,
        "network access must be false",
    )
    require(
        output.get("walletPresent") is False,
        "wallet presence must be false",
    )
    require(
        output.get("signingEnabled") is False,
        "signing must be disabled",
    )
    require(
        output.get("broadcastEnabled") is False,
        "broadcast must be disabled",
    )
    require(
        output.get("submissionEnabled") is False,
        "submission must be disabled",
    )
    require(output.get("error_count") == 0, "Phase97 error count must be zero")

    require(
        output.get("full_chain_integrity_digest") == EXPECTED_PHASE97_FULL_CHAIN,
        "Phase97 full-chain integrity digest mismatch",
    )

    manifest_payload = {
        "phase": 98,
        "name": "terminal_manifest_gate",
        "previous_phase": 97,
        "phase97_source_digest": phase97_source_digest,
        "phase97_full_chain_integrity_digest":
            output["full_chain_integrity_digest"],
        "phase97_output_canonical_digest": canonical_digest(output),
        "phase97_checkpoint_canonical_digest": canonical_digest(checkpoint),
        "executionAuthorized": False,
        "networkAccess": False,
        "walletPresent": False,
        "signingEnabled": False,
        "broadcastEnabled": False,
        "submissionEnabled": False,
        "error_count": 0,
    }

    terminal_manifest_digest = canonical_digest(manifest_payload)

    result = {
        "state": "VERIFIED_READ_ONLY",
        "ready": True,
        "valid": True,
        "checkpoint": "VERIFIED",
        "previous_phase": 97,
        "phase97_source_digest": phase97_source_digest,
        "phase97_full_chain_integrity_digest":
            output["full_chain_integrity_digest"],
        "phase97_output_canonical_digest":
            manifest_payload["phase97_output_canonical_digest"],
        "phase97_checkpoint_canonical_digest":
            manifest_payload["phase97_checkpoint_canonical_digest"],
        "terminal_manifest_digest": terminal_manifest_digest,
        "executionAuthorized": False,
        "networkAccess": False,
        "walletPresent": False,
        "signingEnabled": False,
        "broadcastEnabled": False,
        "submissionEnabled": False,
        "error_count": 0,
    }

    OUT.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")

    with CHECKPOINT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print("STATE: VERIFIED_READ_ONLY")
    print("READY: True")
    print("VALID: True")
    print("CHECKPOINT: VERIFIED")
    print("PREVIOUS PHASE: 97")
    print(f"PHASE97 SOURCE DIGEST: {phase97_source_digest}")
    print(
        "PHASE97 FULL CHAIN INTEGRITY DIGEST: "
        f"{output['full_chain_integrity_digest']}"
    )
    print(
        "PHASE97 OUTPUT CANONICAL DIGEST: "
        f"{manifest_payload['phase97_output_canonical_digest']}"
    )
    print(
        "PHASE97 CHECKPOINT CANONICAL DIGEST: "
        f"{manifest_payload['phase97_checkpoint_canonical_digest']}"
    )
    print(f"TERMINAL MANIFEST DIGEST: {terminal_manifest_digest}")
    print("EXECUTION AUTHORIZED: False")
    print("NETWORK ACCESS: False")
    print("WALLET PRESENT: False")
    print("SIGNING ENABLED: False")
    print("BROADCAST ENABLED: False")
    print("SUBMISSION ENABLED: False")
    print("ERROR COUNT: 0")


if __name__ == "__main__":
    main()
