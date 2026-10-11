#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "provider-output" / "aacp-observer"

PHASE104_SOURCE_SHA256 = (
    "c6d3c2a422f93436f16e400c43f9ae26e1eea1a2ad63111c35b2fab0b5181fac"
)
PHASE104_TEST_SHA256 = (
    "2ed992557dfaaa061c6eddfa8107ec2f136ec2e06c1014f6b888e1bf828e9d78"
)
PHASE104_OUTPUT_SHA256 = (
    "3864d9c9a9693d5c041b0c193c960127904ad71a0d7aeec38fb75e5e4e191552"
)

PHASES = {
    100: {
        "source": "aacp-phase100-terminal-seal-continuity-gate.py",
        "name": "phase100-terminal-seal-continuity-gate",
        "source_sha256": "9d09c9a83f19168e99c755666321850151f95e93df0b939fad4bf4ba8dbdc068",
        "output_sha256": "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71",
        "previous": 99,
    },
    101: {
        "source": "aacp-phase101-terminal-seal-chain-integrity-gate.py",
        "name": "phase101-terminal-seal-chain-integrity-gate",
        "source_sha256": "fe711c887239036f7d9d67c5cf9ab8a405a0be8f86e98ae7a9db6730bb7c0c4b",
        "output_sha256": "0cb44297a08d238210fb19a851426d7248c56e1c8cc4132e6038898827807f19",
        "previous": 100,
    },
    102: {
        "source": "aacp-phase102-terminal-seal-lineage-verification-gate.py",
        "name": "phase102-terminal-seal-lineage-verification-gate",
        "source_sha256": "c65b37cd80a5db0e044666cfe88038dfbe353e5477f67ad1fb588f39abc8bb28",
        "output_sha256": "982511f968a4599be5df89bd22b8e6c76a59190db68b3fe594ec093e06f510fe",
        "previous": 101,
    },
    103: {
        "source": "aacp-phase103-terminal-seal-lineage-continuity-audit.py",
        "name": "phase103-terminal-seal-lineage-continuity-audit",
        "source_sha256": "18414fe1b4ed59cb20b756f1f4a48f61f37319144dfb56d3429eb255ff77e980",
        "previous": 102,
    },
    104: {
        "source": "aacp-phase104-terminal-seal-cross-artifact-consistency-audit.py",
        "name": "phase104-terminal-seal-cross-artifact-consistency-audit",
        "source_sha256": PHASE104_SOURCE_SHA256,
        "output_sha256": PHASE104_OUTPUT_SHA256,
        "previous": 103,
    },
}

PHASE103_TEST = ROOT / "tests/aacp-phase103-terminal-seal-lineage-continuity-audit-regression.py"
PHASE102_TEST = ROOT / "tests/aacp-phase102-terminal-seal-lineage-verification-regression.py"
PHASE104_TEST = ROOT / "tests/aacp-phase104-terminal-seal-cross-artifact-consistency-audit-regression.py"

EXPECTED_P102_TEST = (
    "b035f6c744283e45bc264856547e5720aa25f4ebea2dd2eb7fb951a7b2538f96"
)
EXPECTED_P103_TEST = (
    "09091e9002d32babde85019e952ee6bcb1c820ef7fe420ffeb4776bc6769c7dd"
)

OUTPUT = OUTDIR / "phase105-terminal-seal-phase104-lineage-audit.json"
CHECKPOINT = OUTDIR / "phase105-terminal-seal-phase104-lineage-audit-checkpoint.json"

SAFETY_FIELDS = (
    "executionAuthorized",
    "networkAccess",
    "walletPresent",
    "signingEnabled",
    "broadcastEnabled",
    "submissionEnabled",
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
        items = {}

        for phase, spec in PHASES.items():
            source = ROOT / "src" / spec["source"]
            output = OUTDIR / f'{spec["name"]}.json'
            checkpoint = OUTDIR / f'{spec["name"]}-checkpoint.json'

            source_data = read(source)
            output_data = read(output)
            checkpoint_data = read(checkpoint)

            hashes[f"phase{phase}_source"] = sha(source_data)
            hashes[f"phase{phase}_output"] = sha(output_data)
            hashes[f"phase{phase}_checkpoint"] = sha(checkpoint_data)

            require(
                hashes[f"phase{phase}_source"] == spec["source_sha256"],
                f"Phase{phase} source SHA-256 anchor mismatch",
            )
            require(
                output_data == checkpoint_data,
                f"Phase{phase} output/checkpoint mismatch",
            )

            if "output_sha256" in spec:
                require(
                    hashes[f"phase{phase}_output"] == spec["output_sha256"],
                    f"Phase{phase} output SHA-256 anchor mismatch",
                )

            records[phase] = output_data
            items[phase] = parse(output_data, f"Phase{phase}")
            verify_metadata(
                items[phase], f"Phase{phase}", phase, spec["previous"]
            )

        for test_path, expected, label in (
            (PHASE102_TEST, EXPECTED_P102_TEST, "Phase102"),
            (PHASE103_TEST, EXPECTED_P103_TEST, "Phase103"),
            (PHASE104_TEST, PHASE104_TEST_SHA256, "Phase104"),
        ):
            actual = sha(read(test_path))
            require(actual == expected, f"{label} regression SHA-256 anchor mismatch")
            hashes[f"phase{label[5:]}_regression"] = actual

        p101, p102, p103, p104 = (
            items[101], items[102], items[103], items[104]
        )

        require(
            p101.get("phase100_source_sha256") == hashes["phase100_source"],
            "Phase101 Phase100 source lineage mismatch",
        )
        require(
            p101.get("phase100_output_sha256") == hashes["phase100_output"],
            "Phase101 Phase100 output lineage mismatch",
        )
        require(
            p101.get("phase100_checkpoint_sha256") == hashes["phase100_checkpoint"],
            "Phase101 Phase100 checkpoint lineage mismatch",
        )
        require(
            p101.get("phase100_output_checkpoint_identical") is True,
            "Phase101 identity attestation missing",
        )

        require(
            p102.get("phase100_source_sha256") == hashes["phase100_source"],
            "Phase102 Phase100 source lineage mismatch",
        )
        require(
            p102.get("phase100_output_sha256") == hashes["phase100_output"],
            "Phase102 Phase100 output lineage mismatch",
        )
        require(
            p102.get("phase101_source_sha256") == hashes["phase101_source"],
            "Phase102 Phase101 source lineage mismatch",
        )
        require(
            p102.get("phase101_output_sha256") == hashes["phase101_output"],
            "Phase102 Phase101 output lineage mismatch",
        )
        require(
            p102.get("lineage_100_to_101_verified") is True,
            "Phase102 lineage attestation missing",
        )

        for phase in (100, 101, 102):
            prefix = f"phase{phase}"
            for kind in ("source", "output", "checkpoint"):
                require(
                    p103.get(f"{prefix}_{kind}_sha256") == hashes[f"{prefix}_{kind}"],
                    f"Phase103 {prefix} {kind} lineage mismatch",
                )
            require(
                p103.get(f"{prefix}_output_checkpoint_identical") is True,
                f"Phase103 {prefix} identity attestation missing",
            )
        require(
            p103.get("phase102_regression_sha256") == hashes["phase102_regression"],
            "Phase103 Phase102 regression lineage mismatch",
        )
        require(
            p103.get("lineage_100_to_102_verified") is True,
            "Phase103 lineage attestation missing",
        )

        require(
            p104.get("phase100_to_103_cross_artifact_consistency_verified") is True,
            "Phase104 cross-artifact attestation missing",
        )
        require(
            p104.get("phase100_to_103_output_checkpoint_identity_verified") is True,
            "Phase104 output/checkpoint attestation missing",
        )
        require(
            p104.get("phase100_to_103_lineage_verified") is True,
            "Phase104 lineage attestation missing",
        )
        require(
            p104.get("phase102_regression_sha256") == hashes["phase102_regression"],
            "Phase104 Phase102 regression lineage mismatch",
        )
        require(
            p104.get("phase103_regression_sha256") == hashes["phase103_regression"],
            "Phase104 Phase103 regression lineage mismatch",
        )

        for phase in range(100, 104):
            prefix = f"phase{phase}"
            for kind in ("source", "output", "checkpoint"):
                require(
                    p104.get(f"{prefix}_{kind}_sha256") == hashes[f"{prefix}_{kind}"],
                    f"Phase104 {prefix} {kind} lineage mismatch",
                )

        result = {
            "state": "VERIFIED_READ_ONLY",
            "phase": 105,
            "gate": "Terminal Seal Phase104 Lineage Audit",
            "previous_phase": 104,
            "ready": True,
            "valid": True,
            "checkpoint": "VERIFIED",
            "error_count": 0,
            "phase100_to_104_lineage_verified": True,
            "phase100_to_104_cross_artifact_consistency_verified": True,
            "phase100_to_104_output_checkpoint_identity_verified": True,
            "phase104_source_sha256": hashes["phase104_source"],
            "phase104_output_sha256": hashes["phase104_output"],
            "phase104_checkpoint_sha256": hashes["phase104_checkpoint"],
            "phase104_regression_sha256": hashes["phase104_regression"],
            "phase104_output_checkpoint_identical": True,
            "executionAuthorized": False,
            "networkAccess": False,
            "walletPresent": False,
            "signingEnabled": False,
            "broadcastEnabled": False,
            "submissionEnabled": False,
        }

        for phase in range(100, 105):
            for kind in ("source", "output", "checkpoint"):
                result[f"phase{phase}_{kind}_sha256"] = hashes[f"phase{phase}_{kind}"]

        encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
        OUTDIR.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(encoded)
        CHECKPOINT.write_bytes(encoded)

        print("STATE: VERIFIED_READ_ONLY")
        print("PHASE: 105")
        print("PREVIOUS PHASE: 104")
        print("READY: True")
        print("VALID: True")
        print("CHECKPOINT: VERIFIED")
        print("LINEAGE 100 -> 104: VERIFIED")
        print("CROSS-ARTIFACT CONSISTENCY: VERIFIED")
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
