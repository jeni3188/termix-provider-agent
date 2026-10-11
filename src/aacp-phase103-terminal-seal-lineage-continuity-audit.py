#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "provider-output" / "aacp-observer"

FILES = {
    "p100_source": ROOT / "src/aacp-phase100-terminal-seal-continuity-gate.py",
    "p100_output": OUTDIR / "phase100-terminal-seal-continuity-gate.json",
    "p100_checkpoint": OUTDIR / "phase100-terminal-seal-continuity-gate-checkpoint.json",
    "p101_source": ROOT / "src/aacp-phase101-terminal-seal-chain-integrity-gate.py",
    "p101_output": OUTDIR / "phase101-terminal-seal-chain-integrity-gate.json",
    "p101_checkpoint": OUTDIR / "phase101-terminal-seal-chain-integrity-gate-checkpoint.json",
    "p102_source": ROOT / "src/aacp-phase102-terminal-seal-lineage-verification-gate.py",
    "p102_regression": ROOT / "tests/aacp-phase102-terminal-seal-lineage-verification-regression.py",
    "p102_output": OUTDIR / "phase102-terminal-seal-lineage-verification-gate.json",
    "p102_checkpoint": OUTDIR / "phase102-terminal-seal-lineage-verification-gate-checkpoint.json",
}

OUTPUT = OUTDIR / "phase103-terminal-seal-lineage-continuity-audit.json"
CHECKPOINT = OUTDIR / "phase103-terminal-seal-lineage-continuity-audit-checkpoint.json"

EXPECTED = {
    "p100_source": "9d09c9a83f19168e99c755666321850151f95e93df0b939fad4bf4ba8dbdc068",
    "p100_output": "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71",
    "p101_source": "fe711c887239036f7d9d67c5cf9ab8a405a0be8f86e98ae7a9db6730bb7c0c4b",
    "p101_output": "0cb44297a08d238210fb19a851426d7248c56e1c8cc4132e6038898827807f19",
    "p102_source": "c65b37cd80a5db0e044666cfe88038dfbe353e5477f67ad1fb588f39abc8bb28",
    "p102_regression": "b035f6c744283e45bc264856547e5720aa25f4ebea2dd2eb7fb951a7b2538f96",
    "p102_output": "982511f968a4599be5df89bd22b8e6c76a59190db68b3fe594ec093e06f510fe",
}

SAFETY_FIELDS = (
    "executionAuthorized", "networkAccess", "walletPresent",
    "signingEnabled", "broadcastEnabled", "submissionEnabled",
)


class GateError(Exception):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise GateError(message)


def read(path):
    require(path.is_file(), f"Missing required file: {path}")
    return path.read_bytes()


def parse(data, label):
    try:
        value = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GateError(f"Invalid JSON in {label}: {exc}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def verify_phase(item, label, phase, previous_phase):
    if phase is not None:
        require(item.get("phase") == phase, f"{label} phase mismatch")
    require(item.get("previous_phase") == previous_phase,
            f"{label} previous_phase mismatch")
    require(item.get("state") == "VERIFIED_READ_ONLY",
            f"{label} state mismatch")
    require(item.get("ready") is True, f"{label} not ready")
    require(item.get("valid") is True, f"{label} not valid")
    require(item.get("checkpoint") == "VERIFIED",
            f"{label} checkpoint mismatch")
    require(item.get("error_count") == 0, f"{label} error count mismatch")
    for field in SAFETY_FIELDS:
        require(item.get(field) is False,
                f"{label} safety invariant violated: {field}")


def main():
    try:
        raw = {name: read(path) for name, path in FILES.items()}
        hashes = {name: sha(data) for name, data in raw.items()}

        for name, expected in EXPECTED.items():
            require(hashes[name] == expected,
                    f"{name} SHA-256 anchor mismatch")

        for phase in (100, 101, 102):
            output = raw[f"p{phase}_output"]
            checkpoint = raw[f"p{phase}_checkpoint"]
            require(output == checkpoint,
                    f"Phase{phase} output/checkpoint not byte-identical")

        p100 = parse(raw["p100_output"], "Phase100")
        p101 = parse(raw["p101_output"], "Phase101")
        p102 = parse(raw["p102_output"], "Phase102")

        verify_phase(p100, "Phase100", None, 99)
        verify_phase(p101, "Phase101", None, 100)
        verify_phase(p102, "Phase102", 102, 101)

        require(p101.get("phase100_source_sha256") == hashes["p100_source"],
                "Phase101 Phase100 source lineage mismatch")
        require(p101.get("phase100_output_sha256") == hashes["p100_output"],
                "Phase101 Phase100 output lineage mismatch")
        require(p101.get("phase100_checkpoint_sha256") == hashes["p100_checkpoint"],
                "Phase101 Phase100 checkpoint lineage mismatch")
        require(p101.get("phase100_output_checkpoint_identical") is True,
                "Phase101 byte-identity attestation missing")

        require(p102.get("phase100_source_sha256") == hashes["p100_source"],
                "Phase102 Phase100 source lineage mismatch")
        require(p102.get("phase100_output_sha256") == hashes["p100_output"],
                "Phase102 Phase100 output lineage mismatch")
        require(p102.get("phase101_source_sha256") == hashes["p101_source"],
                "Phase102 Phase101 source lineage mismatch")
        require(p102.get("phase101_output_sha256") == hashes["p101_output"],
                "Phase102 Phase101 output lineage mismatch")
        require(p102.get("lineage_100_to_101_verified") is True,
                "Phase102 lineage attestation missing")
        require(p102.get("phase100_output_checkpoint_identical") is True,
                "Phase102 Phase100 identity attestation missing")
        require(p102.get("phase101_output_checkpoint_identical") is True,
                "Phase102 Phase101 identity attestation missing")

        result = {
            "state": "VERIFIED_READ_ONLY",
            "phase": 103,
            "gate": "Terminal Seal Lineage Continuity Audit",
            "previous_phase": 102,
            "ready": True,
            "valid": True,
            "checkpoint": "VERIFIED",
            "error_count": 0,
            "phase100_source_sha256": hashes["p100_source"],
            "phase100_output_sha256": hashes["p100_output"],
            "phase100_checkpoint_sha256": hashes["p100_checkpoint"],
            "phase100_output_checkpoint_identical": True,
            "phase101_source_sha256": hashes["p101_source"],
            "phase101_output_sha256": hashes["p101_output"],
            "phase101_checkpoint_sha256": hashes["p101_checkpoint"],
            "phase101_output_checkpoint_identical": True,
            "phase102_source_sha256": hashes["p102_source"],
            "phase102_regression_sha256": hashes["p102_regression"],
            "phase102_output_sha256": hashes["p102_output"],
            "phase102_checkpoint_sha256": hashes["p102_checkpoint"],
            "phase102_output_checkpoint_identical": True,
            "lineage_100_to_102_verified": True,
            "executionAuthorized": False,
            "networkAccess": False,
            "walletPresent": False,
            "signingEnabled": False,
            "broadcastEnabled": False,
            "submissionEnabled": False,
        }

        encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
        OUTDIR.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(encoded)
        CHECKPOINT.write_bytes(encoded)

        print("STATE: VERIFIED_READ_ONLY")
        print("PHASE: 103")
        print("READY: True")
        print("VALID: True")
        print("CHECKPOINT: VERIFIED")
        print("PREVIOUS PHASE: 102")
        print("LINEAGE 100 -> 102: VERIFIED")
        print("OUTPUT/CHECKPOINT: BYTE_IDENTICAL")
        for field in SAFETY_FIELDS:
            print(f"{field}: False")
        print("ERROR COUNT: 0")
        return 0

    except (GateError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
