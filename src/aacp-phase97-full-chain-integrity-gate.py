#!/usr/bin/env python3

import hashlib
import json
import sys
from pathlib import Path

PHASE = 97
PREVIOUS_PHASE = 96

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "src"
OBSERVER = BASE / "provider-output" / "aacp-observer"

EXPECTED_SOURCES = {
    92: "4ffc336aa24672a2e5908ba66f28b019ad31ac4f3f26e9f3594a31dd06f4b40c",
    93: "067dc6ba5c3e219c28594290f3ab233adb2ecfcd2292c8ec0428436bef25d5cd",
    94: "aee0ed86dd187d33171efe5eaa9389a70fbe348d91ba25f22f29857075bf3950",
    95: "ebe3dffdfd5abc1a3b7410bcaa2faa1c022e4a15b97faef5da2967646cd8b372",
    96: "24ca8e2a4a1630d1738d05e0e93a40d7a2e335c40a5826ca9e66b9f716aea766",
}

EXPECTED_PHASE95_FINALITY = (
    "b5927dc10dccad322dbfb39dd21e34e9deb00f64e533742aee3b3d74f85f9470"
)

EXPECTED_PHASE96_POST_FINALITY = (
    "91657f94ffbd858530b8b2b6881661b0fc5877ca99d6dac893f63eb029451dd0"
)

PHASE_FILES = {
    92: (
        SRC / "aacp-phase92-evidence-chain-cross-artifact-verification-gate.py",
        OBSERVER / "phase92-evidence-chain-cross-artifact-verification-gate.json",
        OBSERVER / "phase92-evidence-chain-cross-artifact-verification-gate-checkpoint.json",
    ),
    93: (
        SRC / "aacp-phase93-terminal-evidence-snapshot-integrity-gate.py",
        OBSERVER / "phase93-terminal-evidence-snapshot-integrity-gate.json",
        OBSERVER / "phase93-terminal-evidence-snapshot-integrity-gate-checkpoint.json",
    ),
    94: (
        SRC / "aacp-phase94-evidence-snapshot-continuity-terminal-anchor-gate.py",
        OBSERVER / "phase94-evidence-snapshot-continuity-terminal-anchor-gate.json",
        OBSERVER / "phase94-evidence-snapshot-continuity-terminal-anchor-gate-checkpoint.json",
    ),
    95: (
        SRC / "aacp-phase95-evidence-chain-terminal-finality-gate.py",
        OBSERVER / "phase95-evidence-chain-terminal-finality-gate.json",
        OBSERVER / "phase95-evidence-chain-terminal-finality-gate-checkpoint.json",
    ),
    96: (
        SRC / "aacp-phase96-post-finality-verification-gate.py",
        OBSERVER / "phase96-post-finality-verification-gate.json",
        OBSERVER / "phase96-post-finality-verification-gate-checkpoint.json",
    ),
}

OUTPUT = OBSERVER / "phase97-full-chain-integrity-gate.json"
CHECKPOINT = OBSERVER / "phase97-full-chain-integrity-gate-checkpoint.json"

errors = []


def require(condition, message):
    if not condition:
        errors.append(message)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_digest(value):
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path, label):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        errors.append(f"{label} unreadable: {exc}")
        return None


def validate_common(data, phase):
    if data is None:
        return

    require(data.get("phase") == phase, f"Phase{phase} phase mismatch")
    require(
        data.get("previous_phase") == phase - 1,
        f"Phase{phase} previous_phase mismatch",
    )
    require(
        data.get("state") == "VERIFIED_READ_ONLY",
        f"Phase{phase} state mismatch",
    )
    require(data.get("ready") is True, f"Phase{phase} ready mismatch")
    require(data.get("valid") is True, f"Phase{phase} valid mismatch")
    require(
        data.get("checkpoint") == "VERIFIED",
        f"Phase{phase} checkpoint mismatch",
    )
    require(
        data.get("error_count") == 0,
        f"Phase{phase} error_count mismatch",
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
            data.get(flag) is False,
            f"Phase{phase} safety flag {flag} is not false",
        )


artifacts = {}

for phase in range(92, 97):
    source, output_path, checkpoint_path = PHASE_FILES[phase]

    require(
        source.is_file(),
        f"Phase{phase} source missing",
    )

    if source.is_file():
        actual = sha256_file(source)
        require(
            actual == EXPECTED_SOURCES[phase],
            f"Phase{phase} source digest mismatch",
        )

    output = load_json(output_path, f"Phase{phase} output")
    checkpoint = load_json(checkpoint_path, f"Phase{phase} checkpoint")

    validate_common(output, phase)
    validate_common(checkpoint, phase)

    if output is not None and checkpoint is not None:
        output_digest = canonical_digest(output)
        checkpoint_digest = canonical_digest(checkpoint)

        require(
            output_digest == checkpoint_digest,
            f"Phase{phase} output/checkpoint canonical digest mismatch",
        )
        require(
            output == checkpoint,
            f"Phase{phase} output/checkpoint semantic mismatch",
        )

        artifacts[phase] = {
            "output": output,
            "checkpoint": checkpoint,
            "canonical_digest": output_digest,
        }


for phase in range(93, 97):
    previous = artifacts.get(phase - 1)
    current = artifacts.get(phase)

    if previous and current:
        require(
            current["output"].get("previous_phase") == phase - 1,
            f"Phase{phase} chain predecessor mismatch",
        )

        predecessor_digest = current["output"].get(
            f"phase{phase - 1}_output_canonical_digest"
        )

        if predecessor_digest is not None:
            require(
                predecessor_digest == previous["canonical_digest"],
                f"Phase{phase} predecessor canonical digest mismatch",
            )


phase95 = artifacts.get(95)
if phase95:
    require(
        phase95["output"].get("terminal_finality_digest")
        == EXPECTED_PHASE95_FINALITY,
        "Phase95 terminal finality anchor mismatch",
    )


phase96 = artifacts.get(96)
if phase96:
    require(
        phase96["output"].get("phase95_terminal_finality_digest")
        == EXPECTED_PHASE95_FINALITY,
        "Phase96 Phase95 finality anchor mismatch",
    )
    require(
        phase96["output"].get("post_finality_verification_digest")
        == EXPECTED_PHASE96_POST_FINALITY,
        "Phase96 post-finality anchor mismatch",
    )

    payload = dict(phase96["output"])
    stored = payload.pop("post_finality_verification_digest", None)

    require(
        canonical_digest(payload) == stored,
        "Phase96 post-finality digest recomputation mismatch",
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


chain_payload = {
    "phase": PHASE,
    "previous_phase": PREVIOUS_PHASE,
    "state": "VERIFIED_READ_ONLY",
    "ready": True,
    "valid": True,
    "checkpoint": "VERIFIED",
    "phase92_source_digest": EXPECTED_SOURCES[92],
    "phase93_source_digest": EXPECTED_SOURCES[93],
    "phase94_source_digest": EXPECTED_SOURCES[94],
    "phase95_source_digest": EXPECTED_SOURCES[95],
    "phase96_source_digest": EXPECTED_SOURCES[96],
    "phase92_output_canonical_digest": artifacts[92]["canonical_digest"],
    "phase93_output_canonical_digest": artifacts[93]["canonical_digest"],
    "phase94_output_canonical_digest": artifacts[94]["canonical_digest"],
    "phase95_output_canonical_digest": artifacts[95]["canonical_digest"],
    "phase96_output_canonical_digest": artifacts[96]["canonical_digest"],
    "phase95_terminal_finality_digest": EXPECTED_PHASE95_FINALITY,
    "phase96_post_finality_verification_digest": EXPECTED_PHASE96_POST_FINALITY,
    "executionAuthorized": False,
    "networkAccess": False,
    "walletPresent": False,
    "signingEnabled": False,
    "broadcastEnabled": False,
    "submissionEnabled": False,
    "error_count": 0,
}

full_chain_integrity_digest = canonical_digest(chain_payload)
chain_payload["full_chain_integrity_digest"] = full_chain_integrity_digest

for path in (OUTPUT, CHECKPOINT):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chain_payload, f, indent=2, sort_keys=True)
        f.write("\n")

print("STATE: VERIFIED_READ_ONLY")
print("READY: True")
print("VALID: True")
print("CHECKPOINT: VERIFIED")
print("PREVIOUS PHASE: 96")
print(f"PHASE96 SOURCE DIGEST: {EXPECTED_SOURCES[96]}")
print(f"PHASE95 TERMINAL FINALITY DIGEST: {EXPECTED_PHASE95_FINALITY}")
print(f"PHASE96 POST-FINALITY DIGEST: {EXPECTED_PHASE96_POST_FINALITY}")
print(
    f"FULL CHAIN INTEGRITY DIGEST: "
    f"{full_chain_integrity_digest}"
)
print("EXECUTION AUTHORIZED: False")
print("NETWORK ACCESS: False")
print("WALLET PRESENT: False")
print("SIGNING ENABLED: False")
print("BROADCAST ENABLED: False")
print("SUBMISSION ENABLED: False")
print("ERROR COUNT: 0")
