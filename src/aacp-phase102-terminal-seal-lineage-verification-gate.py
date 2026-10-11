#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "provider-output" / "aacp-observer"

P100_SOURCE = ROOT / "src/aacp-phase100-terminal-seal-continuity-gate.py"
P100_OUTPUT = OUTDIR / "phase100-terminal-seal-continuity-gate.json"
P100_CHECKPOINT = OUTDIR / "phase100-terminal-seal-continuity-gate-checkpoint.json"

P101_SOURCE = ROOT / "src/aacp-phase101-terminal-seal-chain-integrity-gate.py"
P101_OUTPUT = OUTDIR / "phase101-terminal-seal-chain-integrity-gate.json"
P101_CHECKPOINT = OUTDIR / "phase101-terminal-seal-chain-integrity-gate-checkpoint.json"

OUTPUT = OUTDIR / "phase102-terminal-seal-lineage-verification-gate.json"
CHECKPOINT = OUTDIR / "phase102-terminal-seal-lineage-verification-gate-checkpoint.json"

EXPECTED = {
    "p100_source": "9d09c9a83f19168e99c755666321850151f95e93df0b939fad4bf4ba8dbdc068",
    "p100_artifact": "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71",
    "p101_source": "fe711c887239036f7d9d67c5cf9ab8a405a0be8f86e98ae7a9db6730bb7c0c4b",
    "p101_artifact": "0cb44297a08d238210fb19a851426d7248c56e1c8cc4132e6038898827807f19",
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
    require(path.is_file(), f"Missing required file: {path.name}")
    return path.read_bytes()


def parse(data, label):
    try:
        value = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GateError(f"Invalid JSON in {label}: {exc}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def main():
    try:
        p100_source = read(P100_SOURCE)
        p100_output = read(P100_OUTPUT)
        p100_checkpoint = read(P100_CHECKPOINT)
        p101_source = read(P101_SOURCE)
        p101_output = read(P101_OUTPUT)
        p101_checkpoint = read(P101_CHECKPOINT)

        hashes = {
            "p100_source": sha(p100_source),
            "p100_output": sha(p100_output),
            "p100_checkpoint": sha(p100_checkpoint),
            "p101_source": sha(p101_source),
            "p101_output": sha(p101_output),
            "p101_checkpoint": sha(p101_checkpoint),
        }

        require(hashes['p100_source'] == EXPECTED["p100_source"],
                "Phase100 source SHA-256 mismatch")
        require(hashes['p100_output'] == EXPECTED["p100_artifact"],
                "Phase100 output SHA-256 mismatch")
        require(hashes["p100_checkpoint"] == EXPECTED["p100_artifact"],
                "Phase100 checkpoint SHA-256 mismatch")
        require(p100_output == p100_checkpoint,
                "Phase100 output/checkpoint are not byte-identical")

        require(hashes['p101_source'] == EXPECTED["p101_source"],
                "Phase101 source SHA-256 mismatch")
        require(hashes['p101_output'] == EXPECTED["p101_artifact"],
                "Phase101 output SHA-256 mismatch")
        require(hashes["p101_checkpoint"] == EXPECTED["p101_artifact"],
                "Phase101 checkpoint SHA-256 mismatch")
        require(p101_output == p101_checkpoint,
                "Phase101 output/checkpoint are not byte-identical")

        p100 = parse(p100_output, "Phase100")
        p101 = parse(p101_output, "Phase101")

        for label, item, phase in (
            ("Phase100", p100, 99),
            ("Phase101", p101, 100),
        ):
            require(item.get("state") == "VERIFIED_READ_ONLY",
                    f"{label} state is not VERIFIED_READ_ONLY")
            require(item.get("ready") is True, f"{label} is not ready")
            require(item.get("valid") is True, f"{label} is not valid")
            require(item.get("checkpoint") == "VERIFIED",
                    f"{label} checkpoint is not VERIFIED")
            require(item.get("previous_phase") == phase,
                    f"{label} previous_phase mismatch")
            require(item.get("error_count") == 0,
                    f"{label} error_count is not zero")
            for field in SAFETY_FIELDS:
                require(item.get(field) is False,
                        f"{label} safety invariant violated: {field}")

        require(p101.get("phase100_source_sha256") == hashes['p100_source'],
                "Phase101 Phase100 source anchor mismatch")
        require(p101.get("phase100_output_sha256") == hashes['p100_output'],
                "Phase101 Phase100 output anchor mismatch")
        require(p101.get("phase100_checkpoint_sha256") == hashes["p100_checkpoint"],
                "Phase101 Phase100 checkpoint anchor mismatch")
        require(p101.get("phase100_output_checkpoint_identical") is True,
                "Phase101 does not attest Phase100 byte identity")

        result = {
            "state": "VERIFIED_READ_ONLY",
            "phase": 102,
            "gate": "Terminal Seal Lineage Verification Gate",
            "previous_phase": 101,
            "ready": True,
            "valid": True,
            "checkpoint": "VERIFIED",
            "error_count": 0,
            "phase100_source_sha256": hashes['p100_source'],
            "phase100_output_sha256": hashes['p100_output'],
            "phase100_checkpoint_sha256": hashes["p100_checkpoint"],
            "phase100_output_checkpoint_identical": True,
            "phase101_source_sha256": hashes['p101_source'],
            "phase101_output_sha256": hashes['p101_output'],
            "phase101_checkpoint_sha256": hashes["p101_checkpoint"],
            "phase101_output_checkpoint_identical": True,
            "lineage_100_to_101_verified": True,
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
        print("PHASE: 102")
        print("READY: True")
        print("VALID: True")
        print("CHECKPOINT: VERIFIED")
        print("PREVIOUS PHASE: 101")
        print(f"PHASE100 SOURCE SHA256: {hashes['p100_source']}")
        print(f"PHASE100 ARTIFACT SHA256: {hashes['p100_output']}")
        print(f"PHASE101 SOURCE SHA256: {hashes['p101_source']}")
        print(f"PHASE101 ARTIFACT SHA256: {hashes['p101_output']}")
        print("LINEAGE 100 -> 101: VERIFIED")
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
