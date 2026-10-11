#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "provider-output" / "aacp-observer"

PHASES = {
    100: {
        "source": ROOT / "src/aacp-phase100-terminal-seal-continuity-gate.py",
        "output": OUTDIR / "phase100-terminal-seal-continuity-gate.json",
        "checkpoint": OUTDIR / "phase100-terminal-seal-continuity-gate-checkpoint.json",
        "source_sha256": "9d09c9a83f19168e99c755666321850151f95e93df0b939fad4bf4ba8dbdc068",
        "output_sha256": "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71",
        "previous": 99,
    },
    101: {
        "source": ROOT / "src/aacp-phase101-terminal-seal-chain-integrity-gate.py",
        "output": OUTDIR / "phase101-terminal-seal-chain-integrity-gate.json",
        "checkpoint": OUTDIR / "phase101-terminal-seal-chain-integrity-gate-checkpoint.json",
        "source_sha256": "fe711c887239036f7d9d67c5cf9ab8a405a0be8f86e98ae7a9db6730bb7c0c4b",
        "output_sha256": "0cb44297a08d238210fb19a851426d7248c56e1c8cc4132e6038898827807f19",
        "previous": 100,
    },
    102: {
        "source": ROOT / "src/aacp-phase102-terminal-seal-lineage-verification-gate.py",
        "output": OUTDIR / "phase102-terminal-seal-lineage-verification-gate.json",
        "checkpoint": OUTDIR / "phase102-terminal-seal-lineage-verification-gate-checkpoint.json",
        "source_sha256": "c65b37cd80a5db0e044666cfe88038dfbe353e5477f67ad1fb588f39abc8bb28",
        "output_sha256": "982511f968a4599be5df89bd22b8e6c76a59190db68b3fe594ec093e06f510fe",
        "previous": 101,
    },
    103: {
        "source": ROOT / "src/aacp-phase103-terminal-seal-lineage-continuity-audit.py",
        "test": ROOT / "tests/aacp-phase103-terminal-seal-lineage-continuity-audit-regression.py",
        "output": OUTDIR / "phase103-terminal-seal-lineage-continuity-audit.json",
        "checkpoint": OUTDIR / "phase103-terminal-seal-lineage-continuity-audit-checkpoint.json",
        "source_sha256": "18414fe1b4ed59cb20b756f1f4a48f61f37319144dfb56d3429eb255ff77e980",
        "test_sha256": "09091e9002d32babde85019e952ee6bcb1c820ef7fe420ffeb4776bc6769c7dd",
        "previous": 102,
    },
}

PHASE102_TEST = ROOT / "tests/aacp-phase102-terminal-seal-lineage-verification-regression.py"
EXPECTED_P102_TEST = "b035f6c744283e45bc264856547e5720aa25f4ebea2dd2eb7fb951a7b2538f96"

OUTPUT = OUTDIR / "phase104-terminal-seal-cross-artifact-consistency-audit.json"
CHECKPOINT = OUTDIR / "phase104-terminal-seal-cross-artifact-consistency-audit-checkpoint.json"

SAFETY_FIELDS = (
    "executionAuthorized", "networkAccess", "walletPresent",
    "signingEnabled", "broadcastEnabled", "submissionEnabled",
)


class GateError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def read(path):
    require(path.is_file(), f"Missing required file: {path}")
    return path.read_bytes()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse(data, label):
    try:
        value = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GateError(f"Invalid JSON in {label}: {exc}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def verify_metadata(item, label, phase, previous):
    if phase >= 102:
        require(item.get("phase") == phase, f"{label} phase mismatch")
    require(item.get("previous_phase") == previous,
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
        hashes = {}
        records = {}

        for phase, spec in PHASES.items():
            for kind in ("source", "output", "checkpoint"):
                data = read(spec[kind])
                hashes[f"phase{phase}_{kind}"] = sha(data)
                if kind in ("output", "checkpoint"):
                    records[(phase, kind)] = data

            require(records[(phase, "output")] == records[(phase, "checkpoint")],
                    f"Phase{phase} output/checkpoint mismatch")

            require(hashes[f"phase{phase}_source"] == spec["source_sha256"],
                    f"Phase{phase} source SHA-256 anchor mismatch")

            if phase <= 102:
                require(hashes[f"phase{phase}_output"] == spec["output_sha256"],
                        f"Phase{phase} output SHA-256 anchor mismatch")

        p102_test_hash = sha(read(PHASE102_TEST))
        require(p102_test_hash == EXPECTED_P102_TEST,
                "Phase102 regression SHA-256 anchor mismatch")
        hashes["phase102_regression"] = p102_test_hash

        p103_test_hash = sha(read(PHASES[103]["test"]))
        require(p103_test_hash == PHASES[103]["test_sha256"],
                "Phase103 regression SHA-256 anchor mismatch")
        hashes["phase103_regression"] = p103_test_hash

        items = {}
        for phase in range(100, 104):
            items[phase] = parse(records[(phase, "output")], f"Phase{phase}")
            verify_metadata(
                items[phase], f"Phase{phase}", phase,
                PHASES[phase]["previous"],
            )

        p101 = items[101]
        p102 = items[102]
        p103 = items[103]

        require(p101.get("phase100_source_sha256") == hashes["phase100_source"],
                "Phase101 Phase100 source lineage mismatch")
        require(p101.get("phase100_output_sha256") == hashes["phase100_output"],
                "Phase101 Phase100 output lineage mismatch")
        require(p101.get("phase100_checkpoint_sha256") == hashes["phase100_checkpoint"],
                "Phase101 Phase100 checkpoint lineage mismatch")
        require(p101.get("phase100_output_checkpoint_identical") is True,
                "Phase101 identity attestation missing")

        require(p102.get("phase100_source_sha256") == hashes["phase100_source"],
                "Phase102 Phase100 source lineage mismatch")
        require(p102.get("phase100_output_sha256") == hashes["phase100_output"],
                "Phase102 Phase100 output lineage mismatch")
        require(p102.get("phase101_source_sha256") == hashes["phase101_source"],
                "Phase102 Phase101 source lineage mismatch")
        require(p102.get("phase101_output_sha256") == hashes["phase101_output"],
                "Phase102 Phase101 output lineage mismatch")
        require(p102.get("lineage_100_to_101_verified") is True,
                "Phase102 lineage attestation missing")

        for phase in (100, 101, 102):
            prefix = f"phase{phase}"
            require(p103.get(f"{prefix}_source_sha256") == hashes[f"{prefix}_source"],
                    f"Phase103 {prefix} source lineage mismatch")
            require(p103.get(f"{prefix}_output_sha256") == hashes[f"{prefix}_output"],
                    f"Phase103 {prefix} output lineage mismatch")
            require(p103.get(f"{prefix}_checkpoint_sha256") == hashes[f"{prefix}_checkpoint"],
                    f"Phase103 {prefix} checkpoint lineage mismatch")
            require(p103.get(f"{prefix}_output_checkpoint_identical") is True,
                    f"Phase103 {prefix} identity attestation missing")

        require(p103.get("phase102_regression_sha256") == hashes["phase102_regression"],
                "Phase103 Phase102 regression lineage mismatch")
        require(p103.get("lineage_100_to_102_verified") is True,
                "Phase103 complete lineage attestation missing")

        result = {
            "state": "VERIFIED_READ_ONLY",
            "phase": 104,
            "gate": "Terminal Seal Cross-Artifact Consistency Audit",
            "previous_phase": 103,
            "ready": True,
            "valid": True,
            "checkpoint": "VERIFIED",
            "error_count": 0,
            "phase100_to_103_cross_artifact_consistency_verified": True,
            "phase100_to_103_output_checkpoint_identity_verified": True,
            "phase100_to_103_lineage_verified": True,
            "phase102_regression_sha256": hashes["phase102_regression"],
            "phase103_regression_sha256": hashes["phase103_regression"],
            "phase103_source_sha256": hashes["phase103_source"],
            "phase103_output_sha256": hashes["phase103_output"],
            "phase103_checkpoint_sha256": hashes["phase103_checkpoint"],
            "phase103_output_checkpoint_identical": True,
            "executionAuthorized": False,
            "networkAccess": False,
            "walletPresent": False,
            "signingEnabled": False,
            "broadcastEnabled": False,
            "submissionEnabled": False,
        }

        for phase in range(100, 104):
            for kind in ("source", "output", "checkpoint"):
                result[f"phase{phase}_{kind}_sha256"] = hashes[f"phase{phase}_{kind}"]

        encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
        OUTDIR.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(encoded)
        CHECKPOINT.write_bytes(encoded)

        print("STATE: VERIFIED_READ_ONLY")
        print("PHASE: 104")
        print("PREVIOUS PHASE: 103")
        print("READY: True")
        print("VALID: True")
        print("CHECKPOINT: VERIFIED")
        print("CROSS-ARTIFACT CONSISTENCY: VERIFIED")
        print("LINEAGE 100 -> 103: VERIFIED")
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
