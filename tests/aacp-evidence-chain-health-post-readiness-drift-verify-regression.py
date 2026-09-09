#!/usr/bin/env python3

import importlib.util
import json
import tempfile
from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "aacp-evidence-chain-health-post-readiness-drift-verify.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase37",
        SOURCE,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f)
        f.write("\n")


def prepare(module, root):
    output = root / "provider-output" / "aacp-observer"
    output.mkdir(parents=True, exist_ok=True)

    module.BASE_DIR = output
    module.BASELINE_FILE = (
        output
        / "aacp-evidence-chain-health-post-readiness-drift-baseline.json"
    )
    module.OUTPUT_FILE = (
        output
        / "latest-aacp-evidence-chain-health-post-readiness-drift-verify.json"
    )

    names = {
        "phase31": (
            "aacp-evidence-chain-health-audit-history-audit-history.json",
            "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY",
        ),
        "phase32": (
            "aacp-evidence-chain-health-audit-history-audit-history-verify.json",
            "AACP_EVIDENCE_CHAIN_HEALTH_AUDIT_HISTORY_AUDIT_HISTORY_VERIFY",
        ),
        "phase33": (
            "aacp-evidence-chain-health-cross-layer-integrity-verify.json",
            "AACP_EVIDENCE_CHAIN_HEALTH_CROSS_LAYER_INTEGRITY_VERIFY",
        ),
        "phase34": (
            "aacp-evidence-chain-health-integrity-attestation.json",
            "AACP_EVIDENCE_CHAIN_HEALTH_INTEGRITY_ATTESTATION",
        ),
        "phase35": (
            "aacp-evidence-chain-health-attestation-consistency-verify.json",
            "AACP_EVIDENCE_CHAIN_HEALTH_ATTESTATION_CONSISTENCY_VERIFY",
        ),
    }

    module.LAYERS = {}

    for name, (filename, artifact_type) in names.items():
        path = output / filename

        payload = {
            "version": "1.0.0",
            "type": artifact_type,
            "state": "VERIFIED_READ_ONLY",
            "sourceState": "VERIFIED_READ_ONLY",
            "executionAuthorized": False,
            "errorCount": 0,
        }

        write_json(path, payload)

        module.LAYERS[name] = {
            "file": str(path),
            "type": artifact_type,
        }

    phase36 = output / "latest-aacp-evidence-chain-health-final-readiness.json"

    write_json(
        phase36,
        {
            "version": "1.0.0",
            "type": "AACP_EVIDENCE_CHAIN_HEALTH_FINAL_READINESS",
            "mode": "READ_ONLY",
            "state": "VERIFIED_READ_ONLY",
            "sourceState": "VERIFIED_READ_ONLY",
            "executionAuthorized": False,
            "readiness": {
                "ready": True,
                "reason": "ALL_REQUIRED_LAYERS_VERIFIED",
            },
            "verification": {
                "valid": True,
                "requiredLayers": 5,
                "verifiedLayers": 5,
            },
            "errorCount": 0,
        },
    )

    module.PHASE36_FILE = phase36


def run_case(name, fn):
    try:
        fn()
        print(f"PASS: {name}")
        return True
    except AssertionError as exc:
        print(f"FAIL: {name}: {exc}")
        return False


def main():
    passed = 0
    total = 0

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        module = load_module()
        prepare(module, root)

        total += 1
        report = module.build_report()
        passed += run_case(
            "first run establishes baseline",
            lambda: (
                assert_true(report["state"] == "BASELINE_ESTABLISHED"),
                assert_true(report["readiness"]["ready"] is False),
                assert_true(report["verification"]["valid"] is True),
                assert_true(report["verification"]["verifiedLayers"] == 0),
                assert_true(report["errorCount"] == 0),
            ),
        )

        total += 1
        report = module.build_report()
        passed += run_case(
            "unchanged baseline verifies",
            lambda: (
                assert_true(report["state"] == "VERIFIED_READ_ONLY"),
                assert_true(report["readiness"]["ready"] is True),
                assert_true(report["verification"]["valid"] is True),
                assert_true(report["verification"]["verifiedLayers"] == 5),
                assert_true(report["errorCount"] == 0),
            ),
        )

        for name in module.LAYERS:
            total += 1

            def drift_case(name=name):
                path = Path(module.LAYERS[name]["file"])
                with open(path, "a", encoding="utf-8") as f:
                    f.write("DRIFT\n")

                report = module.build_report()

                assert_true(report["state"] == "BLOCKED")
                assert_true(report["readiness"]["ready"] is False)
                assert_true(report["verification"]["valid"] is False)
                assert_true(report["errorCount"] > 0)

            passed += run_case(
                f"{name} drift is blocked",
                drift_case,
            )

            # Restore the artifact and baseline for the next isolated drift case.
            prepare(module, root)
            module.build_report()

        total += 1

        def missing_case():
            path = Path(module.LAYERS["phase35"]["file"])
            path.unlink()

            report = module.build_report()

            assert_true(report["state"] == "BLOCKED")
            assert_true(report["verification"]["valid"] is False)
            assert_true(report["readiness"]["ready"] is False)

        passed += run_case(
            "missing artifact is blocked",
            missing_case,
        )

        prepare(module, root)
        module.build_report()

        total += 1

        def phase36_not_ready():
            payload = json.load(open(module.PHASE36_FILE))
            payload["readiness"]["ready"] = False
            write_json(module.PHASE36_FILE, payload)

            report = module.build_report()

            assert_true(report["state"] == "BLOCKED")
            assert_true(report["verification"]["valid"] is False)

        passed += run_case(
            "Phase 36 not ready is blocked",
            phase36_not_ready,
        )

        total += 1

        def execution_forbidden():
            payload = json.load(open(module.PHASE36_FILE))
            payload["readiness"]["ready"] = True
            payload["executionAuthorized"] = True
            write_json(module.PHASE36_FILE, payload)

            report = module.build_report()

            assert_true(report["state"] == "BLOCKED")
            assert_true(report["verification"]["valid"] is False)

        passed += run_case(
            "execution authorization violation is blocked",
            execution_forbidden,
        )

    print(f"\nRESULT: {passed}/{total} PASSED")

    return 0 if passed == total else 1


def assert_true(value):
    assert value


if __name__ == "__main__":
    raise SystemExit(main())
