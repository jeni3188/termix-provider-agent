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

PHASES = {
    100: ("aacp-phase100-terminal-seal-continuity-gate.py",
          "phase100-terminal-seal-continuity-gate",
          "9d09c9a83f19168e99c755666321850151f95e93df0b939fad4bf4ba8dbdc068",
          "6ceaa5dac2ad1e39270a13dd7d387a7af6dc0e1e2e7588761413056f1f035c71", 99),
    101: ("aacp-phase101-terminal-seal-chain-integrity-gate.py",
          "phase101-terminal-seal-chain-integrity-gate",
          "fe711c887239036f7d9d67c5cf9ab8a405a0be8f86e98ae7a9db6730bb7c0c4b",
          "0cb44297a08d238210fb19a851426d7248c56e1c8cc4132e6038898827807f19", 100),
    102: ("aacp-phase102-terminal-seal-lineage-verification-gate.py",
          "phase102-terminal-seal-lineage-verification-gate",
          "c65b37cd80a5db0e044666cfe88038dfbe353e5477f67ad1fb588f39abc8bb28",
          "982511f968a4599be5df89bd22b8e6c76a59190db68b3fe594ec093e06f510fe", 101),
    103: ("aacp-phase103-terminal-seal-lineage-continuity-audit.py",
          "phase103-terminal-seal-lineage-continuity-audit",
          "18414fe1b4ed59cb20b756f1f4a48f61f37319144dfb56d3429eb255ff77e980",
          "c19ff7358a0c2e41f02658d256b1d88fb8b65d52e3e0786af1e2c777bba14b93", 102),
    104: ("aacp-phase104-terminal-seal-cross-artifact-consistency-audit.py",
          "phase104-terminal-seal-cross-artifact-consistency-audit",
          "c6d3c2a422f93436f16e400c43f9ae26e1eea1a2ad63111c35b2fab0b5181fac",
          "3864d9c9a9693d5c041b0c193c960127904ad71a0d7aeec38fb75e5e4e191552", 103),
    105: ("aacp-phase105-terminal-seal-phase104-lineage-audit.py",
          "phase105-terminal-seal-phase104-lineage-audit",
          "a8166f593a714ba4f1b0cac2fdeea59d3e95eebe7eae40e514c8bbccb0b53a83",
          "b74c9a724cb5cc456f2d22a681e56ccf65d2f033499d79f97a0ca54def1eb6a0", 104),
    106: ("aacp-phase106-terminal-seal-phase105-lineage-audit.py",
          "phase106-terminal-seal-phase105-lineage-audit",
          "96500c0f51c501630c99b0852a90b3e529f0a93adea75afe1a5801e9690b090d",
          "93c16edcb519262e78c34ca4632b85adb933c072fbca42aa6205d44d7f16fff5", 105),
    107: ("aacp-phase107-terminal-seal-phase106-lineage-audit.py",
          "phase107-terminal-seal-phase106-lineage-audit",
          "5700c4f58e4a7e418bd49e1efec7aa2e96393547aa3217a6a53bde0234f72e7c",
          "f45ee1c21502be65bc3d3ab3c856b1973fda11d483e031c4b6de94415b6199eb", 106),
    108: ("aacp-phase108-terminal-seal-phase107-lineage-audit.py",
          "phase108-terminal-seal-phase107-lineage-audit",
          "eb8ad42c19e1e3bc46a6ecf6ce66804fcf9f3c969bcd81efcdae707c768336f2",
          "41bc90f07d2e60f3de6e837f275ca7d050ea9fb01add782205951d6bc2fe3836", 107),
}

TESTS = {
    103: ("aacp-phase103-terminal-seal-lineage-continuity-audit-regression.py",
          "09091e9002d32babde85019e952ee6bcb1c820ef7fe420ffeb4776bc6769c7dd"),
    104: ("aacp-phase104-terminal-seal-cross-artifact-consistency-audit-regression.py",
          "2ed992557dfaaa061c6eddfa8107ec2f136ec2e06c1014f6b888e1bf828e9d78"),
    105: ("aacp-phase105-terminal-seal-phase104-lineage-audit-regression.py",
          "d6af8f66674c97221c391fa857e7dfd1d1ed179badf88ba6fa6b20cf432804cb"),
    106: ("aacp-phase106-terminal-seal-phase105-lineage-audit-regression.py",
          "31fc0a3252269cbb4505bd5399fa1cd4ac72d88b58ada165f9f0bedcd58912e9"),    107: ("aacp-phase107-terminal-seal-phase106-lineage-audit-regression.py",
          "c8323292b1894f103a05ea6cc04378a98cc8b0e6a2d6384a329a7d65e37b2f82"),
    108: ("aacp-phase108-terminal-seal-phase107-lineage-audit-regression.py",
          "a3addebebba22954172390ca1e29c20a9b3196a8b16b622291fc2023b62633c1"),
}

OUTPUT = OUTDIR / "phase109-terminal-seal-phase108-lineage-audit.json"
CHECKPOINT = OUTDIR / "phase109-terminal-seal-phase108-lineage-audit-checkpoint.json"


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
    if phase in (100, 101):
        require("phase" not in item,
                f"{label} unexpected phase field")
    else:
        require(item.get("phase") == phase,
                f"{label} phase mismatch")
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
        lineage = {}
        for phase, (source_name, base, source_anchor,
                    output_anchor, previous) in PHASES.items():
            source = ROOT / "src" / source_name
            output = OUTDIR / f"{base}.json"
            checkpoint = OUTDIR / f"{base}-checkpoint.json"

            source_hash = sha(read(source))
            require(source_hash == source_anchor,
                    f"Phase{phase} source hash anchor mismatch")

            output_bytes = read(output)
            checkpoint_bytes = read(checkpoint)
            require(output_bytes == checkpoint_bytes,
                    f"Phase{phase} output/checkpoint mismatch")
            output_hash = sha(output_bytes)
            require(output_hash == output_anchor,
                    f"Phase{phase} output hash anchor mismatch")

            item = parse(output_bytes, f"Phase{phase} output")
            verify_metadata(item, f"Phase{phase}", phase, previous)

            lineage[phase] = {
                "source_sha256": source_hash,
                "output_sha256": output_hash,
                "checkpoint_sha256": sha(checkpoint_bytes),
            }

        for phase, (test_name, test_anchor) in TESTS.items():
            test_path = ROOT / "tests" / test_name
            require(sha(read(test_path)) == test_anchor,
                    f"Phase{phase} regression hash anchor mismatch")

        for phase in range(102, 109):
            item = parse(
                read(OUTDIR / f"{PHASES[phase][1]}.json"),
                f"Phase{phase} output",
            )

            if phase == 102:
                require(item.get("lineage_100_to_101_verified") is True,
                        "Phase102 lineage attestation missing")
            elif phase == 103:
                require(item.get("lineage_100_to_102_verified") is True,
                        "Phase103 lineage attestation missing")
            else:
                previous = phase - 1
                prefix = f"phase100_to_{previous}_"
                require(item.get(prefix + "lineage_verified") is True,
                        f"Phase{phase} lineage attestation missing")
                require(
                    item.get(prefix + "cross_artifact_consistency_verified")
                    is True,
                    f"Phase{phase} consistency attestation missing",
                )
                require(
                    item.get(prefix + "output_checkpoint_identity_verified")
                    is True,
                    f"Phase{phase} identity attestation missing",
                )

        result = {
            "phase": 109,
            "previous_phase": 108,
            "gate": "Terminal Seal Phase108 Lineage Audit",
            "state": "VERIFIED_READ_ONLY",
            "ready": True,
            "valid": True,
            "checkpoint": "VERIFIED",
            "error_count": 0,
            **{field: False for field in SAFETY_FIELDS},
            "phase100_to_108_lineage_verified": True,
            "phase100_to_108_cross_artifact_consistency_verified": True,
            "phase100_to_108_output_checkpoint_identity_verified": True,
        }

        for phase, hashes in lineage.items():
            for kind, value in hashes.items():
                result[f"phase{phase}_{kind}"] = value
        for phase, (_, test_hash) in TESTS.items():
            result[f"phase{phase}_regression_sha256"] = test_hash

        encoded = (
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        ).encode()
        OUTDIR.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(encoded)
        CHECKPOINT.write_bytes(encoded)

        print("PHASE109_GATE=PASS")
        print("phase=109")
        print("previous_phase=108")
        print("state=VERIFIED_READ_ONLY")
        print("checkpoint=VERIFIED")
        print("error_count=0")
        print("lineage=100-108")
        print("output_checkpoint_identical=True")
        print("executionAuthorized=False")
        print("networkAccess=False")
        print("walletPresent=False")
        print("signingEnabled=False")
        print("broadcastEnabled=False")
        print("submissionEnabled=False")
        return 0
    except (GateError, OSError) as exc:
        print(f"PHASE109_GATE=FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
