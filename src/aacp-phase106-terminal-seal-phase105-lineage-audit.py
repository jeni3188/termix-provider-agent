#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "provider-output" / "aacp-observer"

SAFETY_FIELDS = (
    "executionAuthorized",
    "networkAccess",
    "walletPresent",
    "signingEnabled",
    "broadcastEnabled",
    "submissionEnabled",
)

P105_SOURCE_SHA256 = (
    "a8166f593a714ba4f1b0cac2fdeea59d3e95eebe7eae40e514c8bbccb0b53a83"
)
P105_TEST_SHA256 = (
    "d6af8f66674c97221c391fa857e7dfd1d1ed179badf88ba6fa6b20cf432804cb"
)
P105_OUTPUT_SHA256 = (
    "b74c9a724cb5cc456f2d22a681e56ccf65d2f033499d79f97a0ca54def1eb6a0"
)
P104_TEST_SHA256 = (
    "2ed992557dfaaa061c6eddfa8107ec2f136ec2e06c1014f6b888e1bf828e9d78"
)
P103_TEST_SHA256 = (
    "09091e9002d32babde85019e952ee6bcb1c820ef7fe420ffeb4776bc6769c7dd"
)
P102_TEST_SHA256 = (
    "b035f6c744283e45bc264856547e5720aa25f4ebea2dd2eb7fb951a7b2538f96"
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
        "source_sha256": "c6d3c2a422f93436f16e400c43f9ae26e1eea1a2ad63111c35b2fab0b5181fac",
        "output_sha256": "3864d9c9a9693d5c041b0c193c960127904ad71a0d7aeec38fb75e5e4e191552",
        "previous": 103,
    },
    105: {
        "source": "aacp-phase105-terminal-seal-phase104-lineage-audit.py",
        "name": "phase105-terminal-seal-phase104-lineage-audit",
        "source_sha256": P105_SOURCE_SHA256,
        "output_sha256": P105_OUTPUT_SHA256,
        "previous": 104,
    },
}

TESTS = {
    102: (
        ROOT / "tests/aacp-phase102-terminal-seal-lineage-verification-regression.py",
        P102_TEST_SHA256,
    ),
    103: (
        ROOT / "tests/aacp-phase103-terminal-seal-lineage-continuity-audit-regression.py",
        P103_TEST_SHA256,
    ),
    104: (
        ROOT / "tests/aacp-phase104-terminal-seal-cross-artifact-consistency-audit-regression.py",
        P104_TEST_SHA256,
    ),
    105: (
        ROOT / "tests/aacp-phase105-terminal-seal-phase104-lineage-audit-regression.py",
        P105_TEST_SHA256,
    ),
}

OUTPUT = OUTDIR / "phase106-terminal-seal-phase105-lineage-audit.json"
CHECKPOINT = OUTDIR / "phase106-terminal-seal-phase105-lineage-audit-checkpoint.json"


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

            items[phase] = parse(output_data, f"Phase{phase}")
            verify_metadata(
                items[phase], f"Phase{phase}", phase, spec["previous"]
            )

        for phase, (path, expected) in TESTS.items():
            actual = sha(read(path))
            require(actual == expected,
                    f"Phase{phase} regression SHA-256 anchor mismatch")
            hashes[f"phase{phase}_regression"] = actual

        p101, p102, p103, p104, p105 = (
            items[101], items[102], items[103], items[104], items[105]
        )

        for kind in ("source", "output", "checkpoint"):
            require(
                p101.get(f"phase100_{kind}_sha256")
                == hashes[f"phase100_{kind}"],
                f"Phase101 Phase100 {kind} lineage mismatch",
            )
        require(
            p101.get("phase100_output_checkpoint_identical") is True,
            "Phase101 Phase100 identity attestation missing",
        )

        for phase in (100, 101):
            for kind in ("source", "output"):
                require(
                    p102.get(f"phase{phase}_{kind}_sha256")
                    == hashes[f"phase{phase}_{kind}"],
                    f"Phase102 Phase{phase} {kind} lineage mismatch",
                )
        require(
            p102.get("lineage_100_to_101_verified") is True,
            "Phase102 lineage attestation missing",
        )

        for phase in (100, 101, 102):
            for kind in ("source", "output", "checkpoint"):
                require(
                    p103.get(f"phase{phase}_{kind}_sha256")
                    == hashes[f"phase{phase}_{kind}"],
                    f"Phase103 Phase{phase} {kind} lineage mismatch",
                )
            require(
                p103.get(f"phase{phase}_output_checkpoint_identical") is True,
                f"Phase103 Phase{phase} identity attestation missing",
            )
        require(
            p103.get("phase102_regression_sha256")
            == hashes["phase102_regression"],
            "Phase103 Phase102 regression lineage mismatch",
        )
        require(
            p103.get("lineage_100_to_102_verified") is True,
            "Phase103 lineage attestation missing",
        )

        for field in (
            "phase100_to_103_cross_artifact_consistency_verified",
            "phase100_to_103_output_checkpoint_identity_verified",
            "phase100_to_103_lineage_verified",
        ):
            require(p104.get(field) is True,
                    f"Phase104 attestation missing: {field}")
        for phase in range(100, 104):
            for kind in ("source", "output", "checkpoint"):
                require(
                    p104.get(f"phase{phase}_{kind}_sha256")
                    == hashes[f"phase{phase}_{kind}"],
                    f"Phase104 Phase{phase} {kind} lineage mismatch",
                )
        for phase in (102, 103):
            require(
                p104.get(f"phase{phase}_regression_sha256")
                == hashes[f"phase{phase}_regression"],
                f"Phase104 Phase{phase} regression lineage mismatch",
            )

        for field in (
            "phase100_to_104_lineage_verified",
            "phase100_to_104_cross_artifact_consistency_verified",
            "phase100_to_104_output_checkpoint_identity_verified",
        ):
            require(p105.get(field) is True,
                    f"Phase105 attestation missing: {field}")

        for phase in range(100, 105):
            for kind in ("source", "output", "checkpoint"):
                require(
                    p105.get(f"phase{phase}_{kind}_sha256")
                    == hashes[f"phase{phase}_{kind}"],
                    f"Phase105 Phase{phase} {kind} lineage mismatch",
                )
        require(
            p105.get("phase104_regression_sha256")
            == hashes["phase104_regression"],
            "Phase105 Phase104 regression lineage mismatch",
        )
        require(
            p105.get("phase104_output_checkpoint_identical") is True,
            "Phase105 Phase104 identity attestation missing",
        )

        result = {
            "state": "VERIFIED_READ_ONLY",
            "phase": 106,
            "gate": "Terminal Seal Phase105 Lineage Audit",
            "previous_phase": 105,
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
            "phase100_to_105_lineage_verified": True,
            "phase100_to_105_cross_artifact_consistency_verified": True,
            "phase100_to_105_output_checkpoint_identity_verified": True,
            "phase105_source_sha256": hashes["phase105_source"],
            "phase105_output_sha256": hashes["phase105_output"],
            "phase105_checkpoint_sha256": hashes["phase105_checkpoint"],
            "phase105_regression_sha256": hashes["phase105_regression"],
            "phase105_output_checkpoint_identical": True,
        }

        for phase in range(100, 106):
            for kind in ("source", "output", "checkpoint"):
                result[f"phase{phase}_{kind}_sha256"] = hashes[
                    f"phase{phase}_{kind}"
                ]
        for phase in TESTS:
            result[f"phase{phase}_regression_sha256"] = hashes[
                f"phase{phase}_regression"
            ]

        encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
        OUTDIR.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(encoded)
        CHECKPOINT.write_bytes(encoded)

        print("STATE: VERIFIED_READ_ONLY")
        print("PHASE: 106")
        print("PREVIOUS PHASE: 105")
        print("READY: True")
        print("VALID: True")
        print("CHECKPOINT: VERIFIED")
        print("LINEAGE 100 -> 105: VERIFIED")
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
